"""Read-only mechanical checks. A pass always requires semantic/human review."""
import argparse
import json
import re
from pathlib import Path


def validate(data):
    errors, warnings = [], []
    product = data.get('product', {})
    rules = data.get('rules', {})
    listing = data.get('listing', {})
    gallery = data.get('gallery', [])
    stage = data.get('validation_stage', 'gallery')
    schema = data.get('schema_version')
    if schema not in {None, '0.4'}:
        errors.append('schema_version must be 0.4 or omitted for legacy data')
    elif schema is None:
        warnings.append('Legacy schema: explicit gallery strategy is optional; not proof of a designed gallery')
    if stage not in {'product-info', 'gallery'}:
        errors.append('validation_stage must be product-info or gallery')
    if stage == 'product-info':
        gallery = []
        warnings.append('Product-info review only: print placement and gallery have not been checked')
    for key in ('id', 'type', 'marketplace', 'language'):
        if not product.get(key):
            errors.append(f'product.{key} is required')
    region = product.get('print_region', {})
    placement = region.get('placement_review', {})
    delegated_placement = (isinstance(placement, dict) and placement.get('status') == 'delegated'
                           and bool(placement.get('evidence')))
    if stage != 'product-info' and (not region.get('description') or
                                    (region.get('confirmed') is not True and not delegated_placement)):
        errors.append('product.print_region requires a description and confirmation or explicit placement delegation')
    facts = product.get('facts', [])
    confirmed = {f.get('id') for f in facts if isinstance(f, dict) and f.get('confirmed') is True and f.get('text')}
    if not confirmed:
        errors.append('confirmed product facts are required')
    fact_ids = [f.get('id') for f in facts if isinstance(f, dict)]
    if len(set(fact_ids)) != len(fact_ids) or any(not x for x in fact_ids):
        errors.append('product.facts ids must be unique and nonempty')
    title = listing.get('title', '')
    bullets = listing.get('bullets', [])
    description = listing.get('description', '')
    if not isinstance(bullets, list) or len(bullets) != 5:
        errors.append('listing.bullets must contain exactly five entries (project requirement)')
        bullets = bullets if isinstance(bullets, list) else []
    text_fields = [('title', title)] + [(f'bullets[{i}]', b) for i, b in enumerate(bullets)]
    if 'description' in listing:
        text_fields.append(('description', description))
    for field, value in text_fields:
        if not isinstance(value, str) or not value.strip():
            errors.append(f'listing.{field} must be nonempty text')
            continue
        if re.search(r'<[^>]+>', value):
            errors.append(f'listing.{field}: HTML/code is not allowed in this plain-text workflow')
        if re.search(r'https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}', value, re.I):
            errors.append(f'listing.{field}: external link or contact information')
        if re.search(r'free shipping|money.back guarantee|full refund|best seller|\bTBD\b|copy pending', value, re.I):
            errors.append(f'listing.{field}: promotional/placeholder wording')
    for key, values, target in (
        ('title_max', [title], None),
        ('bullet_max', bullets, rules.get('bullet_target', 250)),
        ('description_max', [description], rules.get('description_target', 1000)),
    ):
        limit = rules.get(key)
        if limit is None:
            if key == 'title_max':
                errors.append('rules.title_max requires a marketplace/category limit')
            else:
                warnings.append(f'{key} unknown: verify category limit; editorial target is not an Amazon limit')
        elif not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            errors.append(f'rules.{key} must be a positive integer or null')
        else:
            for i, value in enumerate(values):
                if isinstance(value, str) and len(value) > limit:
                    errors.append(f'{key}[{i}]: {len(value)} characters exceeds {limit}')
        if isinstance(target, int) and target > 0:
            for i, value in enumerate(values):
                if isinstance(value, str) and len(value) > target:
                    warnings.append(f'{key}[{i}] exceeds editorial target {target}')
    if not rules.get('title_source'):
        errors.append('rules.title_source is required')
    if isinstance(title, str):
        if re.search(r'[!$?_{}^¬¦]', title):
            errors.append('listing.title contains prohibited title characters')
        words = re.findall(r"\b[\w]+\b", title.casefold())
        repeated = {w for w in words if w not in {'a', 'an', 'the', 'and', 'or', 'for', 'of', 'in', 'on', 'to', 'with'} and words.count(w) > 2}
        if repeated:
            warnings.append('Review repeated title words: ' + ', '.join(sorted(repeated)))
    if len(set(b for b in bullets if isinstance(b, str))) < len(bullets):
        errors.append('listing.bullets contains exact duplicates')
    for i, bullet in enumerate(bullets):
        if not isinstance(bullet, str):
            continue
        if bullet.isupper():
            errors.append(f'bullets[{i}]: all caps')
        if re.search(r'[.!?。！？]$', bullet.strip()):
            warnings.append(f'bullets[{i}]: remove ending punctuation per bullet guidelines')
        if re.search(r'[\U0001F300-\U0001FAFF\u2600-\u27BF™®©€£¥]', bullet):
            errors.append(f'bullets[{i}]: emoji or restricted symbol')
    image_count = data.get('images_per_set', 7)
    if not isinstance(image_count, int) or isinstance(image_count, bool) or image_count <= 0:
        errors.append('images_per_set must be a positive integer')
        image_count = 7
    if image_count != 7 and not data.get('images_per_set_source'):
        errors.append('images_per_set_source must record the user-requested change from seven')
    if stage != 'product-info' and (not isinstance(gallery, list) or len(gallery) != image_count):
        errors.append(f'gallery must contain exactly {image_count} images (seven by default)')
        gallery = gallery if isinstance(gallery, list) else []
    ids = [g.get('id') for g in gallery if isinstance(g, dict)]
    if len(ids) != len(gallery) or len(ids) != len(set(ids)) or any(not x for x in ids):
        errors.append('gallery ids must be unique and nonempty')
    if gallery and isinstance(gallery[0], dict):
        if gallery[0].get('role') != 'scene' or gallery[0].get('overlay_text') != []:
            errors.append('gallery[0] must be scene with overlay_text=[]')
    sources = [('listing', listing)] + [(f'gallery[{i}]', g) for i, g in enumerate(gallery) if isinstance(g, dict)]
    for label, item in sources:
        refs = item.get('fact_ids')
        if not isinstance(refs, list) or not refs:
            errors.append(f'{label}.fact_ids must reference confirmed facts')
        else:
            for ref in refs:
                if ref not in confirmed:
                    errors.append(f'{label}: fact {ref} is missing or unconfirmed')
    for i, item in enumerate(gallery):
        if not isinstance(item, dict):
            continue
        overlay = item.get('overlay_text')
        if not isinstance(overlay, list) or any(not isinstance(t, str) or not t.strip() for t in overlay):
            errors.append(f'gallery[{i}].overlay_text must be a list of nonempty strings')
        if i and item.get('role') not in {'benefit', 'structure-size', 'tips', 'function', 'detail', 'size', 'scene', 'use', 'comparison'}:
            errors.append(f'gallery[{i}]: unsupported role')
    strategy = data.get('gallery_strategy')
    if schema == '0.4' and stage != 'product-info' and strategy is None:
        errors.append('gallery_strategy is required by schema_version 0.4')
    if strategy is not None and stage != 'product-info':
        if not isinstance(strategy, dict):
            errors.append('gallery_strategy must be an object')
        else:
            for key in ('buyer_profile', 'core_buying_reason', 'visual_direction'):
                if not isinstance(strategy.get(key), str) or not strategy[key].strip():
                    errors.append(f'gallery_strategy.{key} is required')
        for i, item in enumerate(gallery):
            if not isinstance(item, dict):
                continue
            for key in ('buyer_question', 'composition', 'reuse_scope'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(f'gallery[{i}].{key} is required for a designed gallery')
            zh = item.get('overlay_text_zh')
            if not isinstance(zh, list) or len(zh) != len(item.get('overlay_text', [])):
                errors.append(f'gallery[{i}].overlay_text_zh must match the English text')
    workflow = data.get('workflow', {})
    if not isinstance(workflow, dict):
        errors.append('workflow must be an object')
    else:
        if workflow.get('template_state', 'draft') not in {'draft', 'frozen'}:
            errors.append('workflow.template_state must be draft or frozen')
        if workflow.get('stage') not in {None, 'design_draft', 'first_set_ready', 'frozen', 'variants_exported', 'verified_for_declared_templates'}:
            errors.append('workflow.stage is unknown')
        if workflow.get('stage') in {'frozen', 'variants_exported', 'verified_for_declared_templates'} and workflow.get('template_state') != 'frozen':
            errors.append('workflow.stage requires frozen template_state')
    if isinstance(workflow, dict) and workflow.get('template_state') == 'frozen':
        review = workflow.get('first_set_review', {})
        if not isinstance(review, dict) or review.get('status') not in {'approved', 'delegated'} or not review.get('evidence'):
            errors.append('workflow.first_set_review requires approval or explicit delegation evidence')
        elif review.get('status') == 'delegated' and review.get('ai_visual_review') is not True:
            errors.append('workflow.first_set_review.ai_visual_review is required under delegation')
        hashes = workflow.get('template_hashes')
        if not isinstance(hashes, dict) or not hashes or any(not isinstance(v, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', v) for v in hashes.values()):
            errors.append('workflow.template_hashes must record frozen SHA256 values')
        if workflow.get('variant_method') != 'smart-object-only':
            errors.append('workflow.variant_method must be smart-object-only after freezing')
    image_status = rules.get('image_policy_status')
    if image_status == 'verified_for_category':
        if not rules.get('image_policy_source'):
            errors.append('verified image policy requires image_policy_source')
    else:
        warnings.append('Scene main image is user requested; applicability to Haul/category is not independently verified')
    warnings.append('Fact mappings do not prove semantic accuracy; compare every claim and image against source facts')
    if data.get('example_only'):
        warnings.append('Fictional technical example only; not a real product or upload-ready listing')
    return {
        'status': 'ERROR' if errors else 'MECHANICAL_PASS_REVIEW_REQUIRED',
        'errors': errors, 'warnings': warnings,
        'counts': {'title': len(title) if isinstance(title, str) else None,
                   'bullets': [len(b) if isinstance(b, str) else None for b in bullets],
                   'description': len(description) if isinstance(description, str) else None,
                   'gallery': len(gallery)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.input.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        result = {'status': 'ERROR', 'errors': [str(exc)], 'warnings': []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
