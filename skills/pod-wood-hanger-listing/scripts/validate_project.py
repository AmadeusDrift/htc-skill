"""Validate a POD product plan/files against the adjacent skill's confirmed profile."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def positive_dimension(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 and math.isfinite(value)
    except OverflowError:
        return False


def validate_data(data, profile, stage='plan', root=None):
    errors = []
    root = Path(root).resolve() if root else None
    if not isinstance(data, dict):
        return ['Project must be a JSON object']
    if data.get('schema_version') != '1.0':
        errors.append('schema_version must be 1.0')
    if data.get('product_type') != profile['product_type']:
        errors.append('product_type differs from this skill')
    expected = profile['sets']
    count = profile['images_per_set']
    fixed_name = profile['fixed_product_name']
    override = data.get('scope_override')
    if override is not None:
        if not isinstance(override, dict) or not isinstance(override.get('evidence'), str) or not override['evidence'].strip():
            errors.append('scope_override requires explicit user evidence')
        else:
            expected = override.get('sets', expected)
            count = override.get('images_per_set', count)
            fixed_name = override.get('fixed_product_name', fixed_name)
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        errors.append('images_per_set override must be a positive integer'); count = profile['images_per_set']
    if not isinstance(fixed_name, str) or not fixed_name.strip():
        errors.append('fixed_product_name override must be nonempty'); fixed_name = profile['fixed_product_name']
    if not isinstance(expected, list) or not all(isinstance(x, dict) and isinstance(x.get('id'), str) and isinstance(x.get('sizes_cm'), list) and x['sizes_cm'] for x in expected):
        return errors + ['Scope sets require id and sizes_cm']
    expected_ids = [s['id'] for s in expected]
    if len(expected_ids) != len(set(expected_ids)):
        errors.append('Scope set ids must be unique')
    for spec in expected:
        for dims in spec['sizes_cm']:
            if not isinstance(dims, list) or len(dims) not in (2, 3) or not all(positive_dimension(n) for n in dims):
                errors.append('Scope dimensions must contain two or three finite positive numbers')
    sets = data.get('sets')
    if not isinstance(sets, list) or not all(isinstance(s, dict) for s in sets):
        return errors + ['sets must be a list of objects']
    ids = [s.get('id') for s in sets]
    if len(ids) != len(expected_ids) or any(not isinstance(v, str) for v in ids) or sorted(ids) != sorted(expected_ids):
        errors.append('Sets must match the confirmed scope exactly')
    expected_slots = [f'{n:02}' for n in range(1, count + 1)]
    if stage == 'files' and root is None:
        errors.append('files stage requires an explicit product root')

    def relative(value, label, psd=False):
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{label}: path required'); return None
        path = Path(value)
        if path.is_absolute() or path.drive or '..' in path.parts or (psd and (len(path.parts) != 1 or path.suffix.lower() != '.psd')):
            errors.append(f'{label}: path must stay inside product; PSD must be a root .psd'); return None
        target = (root / path).resolve() if root else None
        if root and not target.is_relative_to(root):
            errors.append(f'{label}: resolved path escapes product'); return None
        return target

    def file_exists(value, label, psd=False):
        target = relative(value, label, psd)
        if stage == 'files' and target is not None and not target.is_file():
            errors.append(f'Missing {label}: {value}'); return None
        return target

    def image_file(value, label, expected_canvas=None, png=False):
        target = file_exists(value, label)
        if stage != 'files' or target is None or not target.is_file():
            return
        try:
            from PIL import Image
            with Image.open(target) as im:
                if png and im.format != 'PNG':
                    errors.append(f'{label}: artwork must be a real PNG')
                if expected_canvas is not None and list(im.size) != expected_canvas:
                    errors.append(f'{label}: image canvas differs')
                im.verify()
        except (ImportError, OSError, ValueError) as exc:
            errors.append(f'{label}: cannot validate image ({exc})')

    previous_variants = None
    all_psds = set()
    for group in sets:
        gid = group.get('id', '?'); label = f'set {gid}'
        spec = next((s for s in expected if s['id'] == gid), None)
        if spec and group.get('sizes_cm') != spec['sizes_cm']:
            errors.append(f'{label}: sizes_cm differs from confirmed dimensions')
        gallery = group.get('gallery', [])
        if not isinstance(gallery, list) or not all(isinstance(g, dict) for g in gallery):
            errors.append(f'{label}: gallery must be objects'); continue
        if [g.get('id') for g in gallery] != expected_slots:
            errors.append(f'{label}: gallery must contain ordered slots {expected_slots}')
        psds = set()
        for g in gallery:
            glabel = f'{label}/{g.get("id", "?")}'
            contains = g.get('contains_sku_artwork')
            instances = g.get('print_instances', [])
            if not isinstance(contains, bool) or not isinstance(instances, list):
                errors.append(f'{glabel}: requires explicit artwork boolean and instance list'); continue
            if contains and not instances:
                errors.append(f'{glabel}: visible artwork requires print_instances')
            if not contains and instances:
                errors.append(f'{glabel}: artwork flag contradicts print_instances')
            names = [i.get('layer_name') if isinstance(i, dict) else None for i in instances]
            if any(not isinstance(n, str) or not n.strip() for n in names) or len(set(n for n in names if isinstance(n, str))) != len(names):
                errors.append(f'{glabel}: print layer names must be nonempty and unique')
            if any(not isinstance(i, dict) or not i.get('region_description') for i in instances):
                errors.append(f'{glabel}: every print instance requires region_description')
            if contains or g.get('psd_path'):
                value = g.get('psd_path'); file_exists(value, glabel + ' PSD', psd=True)
                if isinstance(value, str):
                    canonical = str(Path(value)).replace('\\', '/').casefold()
                    if canonical in all_psds:
                        errors.append(f'{glabel}: separate gallery templates must use unique PSD paths')
                    psds.add(value); all_psds.add(canonical)
        listing = group.get('listing', {})
        if not isinstance(listing, dict):
            errors.append(f'{label}: listing must be an object'); listing = {}
        template = listing.get('title_template', {})
        if not isinstance(template, dict):
            template = {}
        phrase, fixed = template.get('print_phrase'), template.get('fixed_product_name')
        if not all(isinstance(x, str) and x.strip() for x in (phrase, fixed)) or listing.get('title') != f'{str(phrase).strip()} {str(fixed).strip()}':
            errors.append(f'{label}: title must equal print phrase plus fixed product name')
        if fixed != fixed_name:
            errors.append(f'{label}: fixed product name differs from confirmed product profile')
        bullets = listing.get('bullets', [])
        if not isinstance(bullets, list) or len(bullets) != 5 or any(not isinstance(b, str) or not b.strip() for b in bullets):
            errors.append(f'{label}: exactly five nonempty bullets required'); bullets = []
        if not isinstance(listing.get('description'), str) or not listing.get('description', '').strip():
            errors.append(f'{label}: nonempty product description required')
        rules = listing.get('rules', {})
        if not isinstance(rules, dict):
            rules = {}
        if rules.get('limit_unit') != 'characters':
            errors.append(f'{label}: this checker requires character limits; bytes require separate validation')
        for field, values in [('title', [listing.get('title', '')]), ('bullet', bullets), ('description', [listing.get('description', '')])]:
            limit = rules.get(field + '_max')
            if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0 or not rules.get(field + '_source'):
                errors.append(f'{label}: {field} requires a positive limit and its source')
            elif any(isinstance(v, str) and len(v) > limit for v in values):
                errors.append(f'{label}: {field} exceeds declared character limit')
        variants = group.get('variants', [])
        if not isinstance(variants, list) or not variants or not all(isinstance(v, dict) for v in variants):
            errors.append(f'{label}: variants must be nonempty objects'); variants = []
        vids = [v.get('id') for v in variants]
        if any(not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in vids) or len(set(v for v in vids if isinstance(v, str))) != len(vids):
            errors.append(f'{label}: variant ids must be unique safe identifiers')
        if previous_variants is not None and vids != previous_variants:
            errors.append(f'{label}: artwork SKU ids/order must agree across size sets')
        previous_variants = vids
        for variant in variants:
            vlabel = f'{label}/{variant.get("id", "?")}'
            variant_title = listing.get('title', '')
            variant_listing = variant.get('listing')
            if variant_listing is not None:
                if not isinstance(variant_listing, dict) or set(variant_listing) != {'print_phrase', 'title'}:
                    errors.append(f'{vlabel}: variant listing may override print_phrase and title only')
                else:
                    vphrase = variant_listing.get('print_phrase')
                    variant_title = variant_listing.get('title')
                    if not isinstance(vphrase, str) or not vphrase.strip() or variant_title != f'{vphrase.strip()} {fixed}':
                        errors.append(f'{vlabel}: variant title must use its print phrase and fixed product name')
                    limit = rules.get('title_max')
                    if isinstance(limit, int) and isinstance(variant_title, str) and len(variant_title) > limit:
                        errors.append(f'{vlabel}: variant title exceeds declared character limit')
            images = variant.get('images', {})
            if not isinstance(images, dict) or sorted(images) != expected_slots:
                errors.append(f'{vlabel}: images must map every slot exactly'); images = {}
            if len(set(p for p in images.values() if isinstance(p, str))) != len(images):
                errors.append(f'{vlabel}: every slot needs its own image file')
            for value in [*images.values(), variant.get('artwork_path'), variant.get('copy_path'), variant.get('overview_path')]:
                if isinstance(value, str) and value:
                    top = Path(value).parts[0]
                    vid = variant.get('id')
                    if not isinstance(vid, str) or not (top == vid or top.startswith(vid + '-')):
                        errors.append(f'{vlabel}: files must belong to this artwork SKU directory')
            for sid, value in images.items():
                image_file(value, vlabel + '/' + sid, group.get('canvas', data.get('canvas')))
            image_file(variant.get('artwork_path'), vlabel + ' artwork', png=True)
            text = file_exists(variant.get('copy_path'), vlabel + ' copy')
            if stage == 'files' and text and text.is_file():
                try:
                    content = text.read_text(encoding='utf-8-sig')
                    if any(not isinstance(v, str) or v not in content for v in [variant_title, *bullets, listing.get('description', '')]):
                        errors.append(f'{vlabel}: copy file must contain full title, five bullets and description')
                except (OSError, UnicodeError):
                    errors.append(f'{vlabel}: copy must be readable UTF-8')
            image_file(variant.get('overview_path'), vlabel + ' overview')
        if stage == 'files':
            flow = group.get('workflow', {})
            if not isinstance(flow, dict):
                flow = {}
            review = flow.get('first_set_review', {})
            if not isinstance(review, dict):
                review = {}
            if flow.get('template_state') != 'frozen' or flow.get('variant_method') != 'smart-object-only':
                errors.append(f'{label}: files stage requires frozen smart-object-only workflow')
            if review.get('status') not in ('approved', 'delegated') or not review.get('evidence') or review.get('ai_visual_review') is not True:
                errors.append(f'{label}: actual first-set review evidence required')
            hashes = flow.get('template_hashes', {})
            if not isinstance(hashes, dict) or set(hashes) != psds:
                errors.append(f'{label}: frozen hashes must cover exactly this set PSDs'); hashes = {}
            for value, expected_hash in hashes.items():
                target = file_exists(value, label + ' frozen PSD', psd=True)
                if not isinstance(expected_hash, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected_hash):
                    errors.append(f'{label}: frozen hash must be SHA256'); continue
                if target and target.is_file():
                    try:
                        with target.open('rb') as handle:
                            if handle.read(4) != b'8BPS':
                                errors.append(f'{label}: invalid PSD file header: {value}')
                        actual = hashlib.sha256(target.read_bytes()).hexdigest()
                        if actual != expected_hash.lower():
                            errors.append(f'{label}: frozen PSD hash mismatch: {value}')
                    except OSError as exc:
                        errors.append(f'{label}: cannot read PSD ({exc})')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--stage', choices=['plan', 'files'], default='plan')
    parser.add_argument('--root', type=Path, help='Product root; defaults to parent of 工作资料, otherwise manifest folder')
    args = parser.parse_args()
    try:
        profile = read_json(Path(__file__).resolve().parents[1] / 'assets/product-profile.json')
        data = read_json(args.project)
        root = args.root or (args.project.resolve().parent.parent if args.project.parent.name == '工作资料' else args.project.resolve().parent)
        errors = validate_data(data, profile, args.stage, root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors = [str(exc)]
    print(json.dumps({'status': 'ERROR' if errors else 'MECHANICAL_PASS_REVIEW_REQUIRED', 'stage': args.stage,
        'errors': errors, 'scope': 'Declared structure/files only; visual quality and actual smart-object replacement require separate evidence'}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
