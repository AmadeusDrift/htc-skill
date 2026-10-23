"""Inspect, preview and package existing gallery images; never generate or replace artwork."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

from PIL import Image, ImageDraw, ImageFont


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def project_path(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Path escapes project: {value}')
    return path


def _ids(items, label):
    ids = [item.get('id') for item in items]
    if (len(set(ids)) != len(ids) or
            any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in ids)):
        raise ValueError(f'{label} ids must be unique safe identifiers')
    return ids


def load_manifest(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    project_root = data.get('project_root', '.')
    if project_root not in ('.', '..'):
        raise ValueError('project_root must be . or .. (manifest folder or its product parent)')
    root = (path.parent / project_root).resolve()
    slots = _ids(data.get('slots', []), 'slot')
    expected = data.get('images_per_set', 7)
    if not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0 or len(slots) != expected:
        raise ValueError('slots must match images_per_set (default 7)')
    variants = data.get('variants', [])
    if not variants:
        raise ValueError('At least one variant is required')
    _ids(variants, 'variant')
    canvas = data.get('canvas')
    if (not isinstance(canvas, list) or len(canvas) != 2 or
            any(not isinstance(n, int) or isinstance(n, bool) or n <= 0 for n in canvas)):
        raise ValueError('canvas requires two positive integer pixel dimensions')
    for variant in variants:
        images = {**data.get('shared_images', {}), **variant.get('images', {})}
        if set(images) - set(slots):
            raise ValueError(f"{variant['id']}: unknown image slots")
        variant['_paths'] = {slot: project_path(root, images[slot]) for slot in slots if slot in images}
    return root, data


def _image(path, canvas):
    if not path.is_file():
        raise ValueError(f'Missing image: {path}')
    with Image.open(path) as source:
        if source.size != tuple(canvas):
            raise ValueError(f'Image canvas mismatch: {path}')
        source.load()
        if source.mode in {'RGBA', 'LA'} or 'transparency' in source.info:
            rgba = source.convert('RGBA')
            background = Image.new('RGBA', rgba.size, 'white')
            background.alpha_composite(rgba)
            return background.convert('RGB')
        return source.convert('RGB')


def _variants(data, variant_id=None):
    variants = [v for v in data['variants'] if variant_id is None or v['id'] == variant_id]
    if not variants:
        raise ValueError(f'Unknown variant: {variant_id}')
    return variants


def _complete(variant, data):
    missing = {s['id'] for s in data['slots']} - set(variant['_paths'])
    if missing:
        raise ValueError(f"Missing image mappings for {variant['id']}: {', '.join(sorted(missing))}")


def inspect(manifest, variant_id=None):
    root, data = load_manifest(manifest)
    variants = _variants(data, variant_id)
    for variant in variants:
        _complete(variant, data)
        for path in variant['_paths'].values():
            _image(path, data['canvas'])
    for template in data.get('templates', []):
        path = project_path(root, template['path'])
        expected = template.get('sha256', '')
        if not re.fullmatch(r'[a-fA-F0-9]{64}', expected):
            raise ValueError(f'Missing frozen template hash: {path}')
        if not path.is_file() or sha256(path) != expected.lower():
            raise ValueError(f'Frozen template hash mismatch: {path}')
    return {'status': 'FILES_VERIFIED_VISUAL_REVIEW_REQUIRED',
            'variant_count': len(variants), 'images_per_set': len(data['slots']),
            'delivered_image_count': len(variants) * len(data['slots']),
            'template_count': len(data.get('templates', []))}


def _protected(manifest, root, data):
    return {Path(manifest).resolve(),
            *(path for v in data['variants'] for path in v['_paths'].values()),
            *(project_path(root, t['path']) for t in data.get('templates', []))}


def _preview(output, inputs, params, render, protected, cache_dir=None):
    output = Path(output).resolve()
    cache = (Path(cache_dir) / (hashlib.sha256(str(output).encode('utf-8')).hexdigest() + '.json')
             if cache_dir is not None else output.with_name(output.name + '.inputs.json'))
    if output in protected or cache in protected:
        raise ValueError('Preview output or sidecar conflicts with a project source')
    record = {'inputs': [{'path': str(path), 'sha256': sha256(path)} for path in inputs], 'params': params}
    if output.exists():
        try:
            previous = json.loads(cache.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            previous = {}
        if (previous.get('inputs') == record['inputs'] and previous.get('params') == params
                and previous.get('output_sha256') == sha256(output)):
            return {'path': str(output), 'reused': True}
        raise ValueError(f'Refusing to overwrite preview with different inputs: {output}')
    if cache.exists():
        raise ValueError(f'Refusing to overwrite existing preview sidecar: {cache}')
    if output.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
        raise ValueError('Preview output must be PNG or JPEG')
    output.parent.mkdir(parents=True, exist_ok=True)
    image = render()
    if output.suffix.lower() == '.png':
        image.save(output)
    else:
        image.save(output, quality=94, subsampling=0)
    record['output_sha256'] = sha256(output)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'path': str(output), 'reused': False}


def make_grid(manifest, slot, output):
    root, data = load_manifest(manifest)
    if slot not in {s['id'] for s in data['slots']}:
        raise ValueError(f'Unknown slot: {slot}')
    if any(slot not in v['_paths'] for v in data['variants']):
        raise ValueError(f'Missing image mapping for requested slot: {slot}')
    inputs = [v['_paths'][slot] for v in data['variants']]
    images = [_image(p, data['canvas']) for p in inputs]
    cols = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / cols)
    width, height = data['canvas']
    def render():
        result = Image.new('RGB', (cols * width, rows * height), 'white')
        for n, image in enumerate(images):
            result.paste(image, ((n % cols) * width, (n // cols) * height))
        return result
    return _preview(output, inputs, {'kind': 'grid', 'slot': slot, 'cols': cols,
                                    'variants': [v['id'] for v in data['variants']]},
                    render, _protected(manifest, root, data),
                    project_path(root, data['preview_cache_dir']) if data.get('preview_cache_dir') else None)


def make_overview(manifest, variant_id, output, thumb=500):
    root, data = load_manifest(manifest)
    variant = next((v for v in data['variants'] if v['id'] == variant_id), None)
    if variant is None:
        raise ValueError(f'Unknown variant: {variant_id}')
    _complete(variant, data)
    inputs = list(variant['_paths'].values())
    images = [_image(p, data['canvas']) for p in inputs]
    def render():
        cols = min(4, len(images)); rows = math.ceil(len(images) / cols)
        gap, footer = 18, 36
        result = Image.new('RGB', (cols * (thumb + gap) + gap, rows * (thumb + footer + gap) + gap), '#f2eee7')
        draw = ImageDraw.Draw(result)
        try:
            font = ImageFont.truetype('arial.ttf', 20)
        except OSError:
            font = ImageFont.load_default(size=20)
        for n, (image, slot) in enumerate(zip(images, data['slots'])):
            image.thumbnail((thumb, thumb), Image.Resampling.LANCZOS)
            x = gap + n % cols * (thumb + gap); y = gap + n // cols * (thumb + footer + gap)
            result.paste(image, (x + (thumb - image.width) // 2, y + (thumb - image.height) // 2))
            draw.text((x, y + thumb + 7), f"{variant_id} / {slot['id']}", fill='#51483c', font=font)
        return result
    return _preview(output, inputs, {'kind': 'overview', 'variant': variant_id, 'thumb': thumb,
                                    'slots': [s['id'] for s in data['slots']]},
                    render, _protected(manifest, root, data),
                    project_path(root, data['preview_cache_dir']) if data.get('preview_cache_dir') else None)


def pack(manifest, output, variant_id=None):
    inspect(manifest, variant_id)
    _, data = load_manifest(manifest)
    variants = _variants(data, variant_id)
    items = {f"{v['id']}/{slot}.png": path for v in variants for slot, path in v['_paths'].items()}
    # Images retain their original encoded bytes and extension; packaging is not image conversion.
    items = {name.rsplit('.', 1)[0] + path.suffix.lower(): path for name, path in items.items()}
    output = Path(output).resolve()
    if output.suffix.lower() != '.zip':
        raise ValueError('Package output must be .zip')
    existed = output.exists()
    if not existed:
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for name, path in sorted(items.items()):
                archive.write(path, name)
    try:
        with zipfile.ZipFile(output) as archive:
            if set(archive.namelist()) != set(items) or archive.testzip() is not None:
                raise ValueError('Archive entries or CRC differ')
            for name, path in items.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != sha256(path):
                    raise ValueError(f'Archive content differs: {name}')
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        raise ValueError(f'Refusing to overwrite package; choose a new versioned path: {exc}') from exc
    return {'path': str(output), 'reused': existed, 'images': len(items), 'integrity': 'PASS'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['inspect', 'overview', 'grid', 'pack'])
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--variant')
    parser.add_argument('--slot')
    args = parser.parse_args()
    try:
        if args.mode == 'inspect': result = inspect(args.manifest, args.variant)
        elif args.out is None: raise ValueError('--out is required')
        elif args.mode == 'overview': result = make_overview(args.manifest, args.variant, args.out)
        elif args.mode == 'grid': result = make_grid(args.manifest, args.slot, args.out)
        else: result = pack(args.manifest, args.out, args.variant)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'ERROR', 'detail': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
