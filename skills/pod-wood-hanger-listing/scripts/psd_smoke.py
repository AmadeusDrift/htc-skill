"""Code-only rectangular PSD integration test using disposable, generated fixtures."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ps_job(shell, mode, spec=None, document=None):
    command = [shell, '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'scripts/photoshop.ps1'), '-Mode', mode]
    if spec:
        command += ['-SpecPath', str(spec)]
    if document:
        command += ['-DocumentPath', str(document)]
    return subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace', timeout=90)


def require_success(result, expected):
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    value = json.loads(result.stdout)
    if value.get('status') != expected:
        raise RuntimeError(f'Unexpected Photoshop result: {value}')
    return value


def run_smoke(shell, output):
    folder = output / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    base = Image.new('RGB', (1024, 1024), '#dde7ec')
    draw = ImageDraw.Draw(base)
    draw.rectangle((220, 220, 804, 804), fill='white', outline='#34424a', width=10)
    draw.text((40, 40), 'PSD SMART OBJECT TECHNICAL TEST', fill='black')
    base.save(folder / 'base.png')
    shapes = [('original', '#db3344', (56, 56, 456, 456)),
              ('wide', '#176fc1', (24, 184, 488, 328)),
              ('tall', '#259b61', (184, 24, 328, 488)),
              ('square', '#8d3abb', (86, 86, 426, 426))]
    for name, color, box in shapes:
        art = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        pen = ImageDraw.Draw(art)
        pen.rectangle((0, 0, 511, 511), outline=color, width=6)
        if name == 'original':
            pen.ellipse(box, fill=color)
        else:
            pen.rectangle(box, fill=color)
        art.save(folder / f'{name}.png')
    Image.new('RGBA', (256, 512), 'orange').save(folder / 'wrong-size.png')
    template = folder / 'template.psd'
    spec = {'base_path': str(folder / 'base.png'), 'artwork_path': str(folder / 'original.png'),
            'output_path': str(template), 'region': {'x': 256, 'y': 256, 'width': 512, 'height': 512}}
    build_path = folder / 'build.json'
    build_path.write_text(json.dumps(spec), encoding='utf-8')
    build = require_success(ps_job(shell, 'Build', spec=build_path), 'PSD_CREATED')
    inspected = require_success(ps_job(shell, 'Inspect', document=template), 'PSD_INSPECTED')
    if not build.get('smartObject') or not inspected.get('smartObject') or inspected.get('bounds') != [256, 256, 768, 768]:
        raise RuntimeError('PSD smart object or placement check failed')
    if template.read_bytes()[:4] != b'8BPS':
        raise RuntimeError('Missing native PSD signature')
    original_hash = digest(template)
    checks, previews = [], []
    for name in [item[0] for item in shapes] + ['wrong-size']:
        preview = folder / f'{name}-preview.png'
        trial_path = folder / f'{name}-trial.json'
        trial_path.write_text(json.dumps({'template_path': str(template),
                             'artwork_path': str(folder / f'{name}.png'),
                             'preview_path': str(preview)}), encoding='utf-8')
        result = ps_job(shell, 'TrialReplace', spec=trial_path)
        if name == 'wrong-size':
            if result.returncode == 0 or 'Normalize replacement artwork' not in result.stderr or preview.exists():
                raise RuntimeError('Mismatched artwork source dimensions were not safely rejected')
            continue
        trial = require_success(result, 'TRIAL_PREVIEW_EXPORTED')
        if trial['before'] != trial['after'] or trial['after'] != [256, 256, 768, 768]:
            raise RuntimeError(f'{name}: smart object moved')
        actual = Image.open(preview).convert('RGB')
        expected = base.copy()
        art = Image.open(folder / f'{name}.png').convert('RGBA')
        expected.paste(art, (256, 256), art)
        if actual.size != expected.size:
            raise RuntimeError(f'{name}: output dimensions changed')
        diff = ImageChops.difference(actual, expected)
        error = max(pair[1] for pair in diff.getextrema())
        outside = ImageChops.difference(actual, base)
        ImageDraw.Draw(outside).rectangle((256, 256, 767, 767), fill='black')
        if error > 2 or outside.getbbox() is not None:
            raise RuntimeError(f'{name}: pixels or background differ, max channel error={error}')
        checks.append({'artwork': name, 'max_channel_error': error, 'outside_unchanged': True})
        previews.append(preview)
    rejected = ps_job(shell, 'Build', spec=build_path)
    if rejected.returncode == 0 or 'Refusing to overwrite' not in rejected.stderr:
        raise RuntimeError('Existing PSD overwrite was not rejected')
    if digest(template) != original_hash:
        raise RuntimeError('Template changed during replacement/negative tests')
    comparison = Image.new('RGB', (1024, 300), 'white')
    for index, preview in enumerate(previews):
        ImageDraw.Draw(comparison).text((index * 256 + 12, 12), shapes[index][0].upper(), fill='black')
        comparison.paste(Image.open(preview).convert('RGB').resize((256, 256)), (index * 256, 36))
    comparison.save(folder / 'comparison.png')
    artifacts = [str(template), *[str(p) for p in previews], str(folder / 'comparison.png')]
    report = {'status': 'PASS', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'Generated rectangular technical fixture; real product/curved surfaces not certified',
              'build': build, 'inspect': inspected, 'pixel_checks': checks,
              'template_unchanged': True, 'mismatched_canvas_rejected': True,
              'overwrite_rejected': True, 'artifacts': artifacts,
              'artifact_hashes': {p: digest(Path(p)) for p in artifacts}}
    (folder / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shell', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run_smoke(args.shell, args.output_dir.resolve())
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        report = {'status': 'ERROR', 'detail': str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
