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
    for key in ('id', 'type', 'marketplace', 'language'):
        if not product.get(key):
            errors.append(f'product.{key} is required')
    region = product.get('print_region', {})
    if region.get('confirmed') is not True or not region.get('description'):
        errors.append('product.print_region must be supplied and confirmed by a person')
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
    text_fields = [('title', title), ('description', description)] + [(f'bullets[{i}]', b) for i, b in enumerate(bullets)]
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
    if not isinstance(gallery, list) or len(gallery) not in (3, 4):
        errors.append('gallery must contain three or four images')
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
        if i and item.get('role') not in {'benefit', 'structure-size', 'tips'}:
            errors.append(f'gallery[{i}]: unsupported role')
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
