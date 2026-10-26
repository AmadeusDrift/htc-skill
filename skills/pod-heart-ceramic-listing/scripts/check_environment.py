"""Initialize isolated dependencies and verify Photoshop without changing system settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {'PyYAML': '6.0.3', 'Pillow': '13.0.0'}


def run_command(command, timeout=180):
    try:
        result = subprocess.run([str(x) for x in command], capture_output=True,
                                encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'Command timed out after {timeout}s: {command[0]}') from exc
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or f'Exit {result.returncode}')[-4000:].strip())
    return result.stdout.strip()


def venv_python(folder):
    return Path(folder) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def package_versions(python):
    # Imports test runtime usability, rather than merely finding installed metadata.
    code = """import importlib, importlib.metadata, json
result = {}
for name, module in [('PyYAML', 'yaml'), ('Pillow', 'PIL')]:
    try:
        importlib.import_module(module)
        result[name] = importlib.metadata.version(name)
    except (ImportError, OSError, importlib.metadata.PackageNotFoundError):
        pass
print(json.dumps(result))
"""
    return json.loads(run_command([python, '-X', 'utf8', '-c', code], timeout=30))


def ensure_dependencies(folder, repair=True):
    python = venv_python(folder)
    actions = []
    try:
        if not python.is_file():
            if not repair:
                return {'status': 'ACTION_REQUIRED', 'detail': 'Isolated Python environment is missing', 'python': str(python)}
            run_command([sys.executable, '-m', 'venv', folder])
            actions.append('created isolated Python environment')
        versions = package_versions(python)
        missing = [name for name in PACKAGES if name not in versions]
        if missing and not repair:
            return {'status': 'ACTION_REQUIRED', 'missing': missing, 'python': str(python)}
        if missing:
            run_command([python, '-m', 'pip', '--disable-pip-version-check', 'install',
                         '--index-url', 'https://pypi.org/simple', '--only-binary=:all:',
                         *[f'{name}=={PACKAGES[name]}' for name in missing]], timeout=300)
            actions.extend(f'installed {name}' for name in missing)
            versions = package_versions(python)
            if any(name not in versions for name in PACKAGES):
                raise RuntimeError('Dependencies remain unusable after installation; inspect the isolated environment')
        return {'status': 'READY', 'python': str(python), 'versions': versions, 'actions': actions}
    except (RuntimeError, OSError, ValueError) as exc:
        return {'status': 'ERROR', 'python': str(python), 'actions': actions, 'detail': str(exc)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def can_reuse_smoke(previous, fingerprint):
    artifacts = previous.get('artifacts', [])
    if previous.get('status') != 'PASS' or previous.get('fingerprint') != fingerprint or not artifacts:
        return False
    try:
        return all(Path(p).is_file() and (p not in previous.get('artifact_hashes', {}) or
                   sha256(p) == previous['artifact_hashes'][p]) for p in artifacts)
    except OSError:
        return False


def read_report(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def check_writable(folder):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder) as handle:
            handle.write(b'POD environment check')
        return {'status': 'READY', 'path': str(folder)}
    except OSError as exc:
        return {'status': 'ERROR', 'path': str(folder), 'detail': str(exc)}


def powershell_probe():
    if os.name != 'nt':
        return {'status': 'ACTION_REQUIRED', 'detail': 'Photoshop COM requires Windows; text/image planning may continue'}
    failures = []
    for name in ('pwsh', 'powershell'):
        shell = shutil.which(name)
        if not shell:
            continue
        try:
            version = run_command([shell, '-NoProfile', '-NonInteractive', '-Command',
                                   '$PSVersionTable.PSVersion.ToString()'], timeout=30)
            probe = json.loads(run_command([shell, '-NoProfile', '-NonInteractive', '-File',
                                           ROOT / 'scripts/photoshop.ps1', '-Mode', 'Probe']))
            if not probe.get('version'):
                raise RuntimeError('Photoshop probe did not return its version')
            return {'status': 'READY', 'shell': shell, 'shell_version': version, 'photoshop': probe}
        except (RuntimeError, OSError, ValueError) as exc:
            failures.append({'shell': shell, 'detail': str(exc)})
    return {'status': 'ACTION_REQUIRED', 'detail': 'No working PowerShell/Photoshop connection. Install missing software or finish licensing manually; no security settings were changed.', 'attempts': failures}


def initialize(env_dir, output_dir, check_only=False, full=False):
    report_path = env_dir.parent / 'environment-report.json'
    previous = read_report(report_path)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'python': {'status': 'READY', 'version': sys.version.split()[0], 'path': sys.executable},
              'directories': [check_writable(env_dir.parent), check_writable(output_dir)]}
    if any(item['status'] != 'READY' for item in report['directories']):
        report['status'] = 'ERROR'
        report['detail'] = 'Cannot write environment or output directory'
        return report, report_path
    deps = report['dependencies'] = ensure_dependencies(env_dir, repair=not check_only)
    ps = report['photoshop_connection'] = powershell_probe()
    smoke = {'status': 'NOT_TESTED'}
    if deps['status'] == ps['status'] == 'READY':
        fingerprint = hashlib.sha256(json.dumps({
            'host': os.environ.get('COMPUTERNAME', ''), 'python': deps['python'],
            'packages': deps['versions'], 'shell': ps['shell'], 'shell_version': ps['shell_version'],
            'photoshop': ps['photoshop']['version'],
            'photoshop_script': sha256(ROOT / 'scripts/photoshop.ps1'),
            'smoke_script': sha256(ROOT / 'scripts/psd_smoke.py')}, sort_keys=True).encode()).hexdigest()
        cached = previous.get('psd_smoke', {})
        if not full and can_reuse_smoke(cached, fingerprint):
            smoke = {**cached, 'cached': True}
        elif not check_only:
            try:
                smoke = json.loads(run_command([deps['python'], '-X', 'utf8', ROOT / 'scripts/psd_smoke.py',
                                               '--shell', ps['shell'], '--output-dir', output_dir], timeout=300))
                smoke.update(fingerprint=fingerprint, cached=False)
            except (RuntimeError, OSError, ValueError) as exc:
                smoke = {'status': 'ERROR', 'detail': str(exc), 'fingerprint': fingerprint}
    report['psd_smoke'] = smoke
    report['status'] = ('READY' if deps['status'] == ps['status'] == 'READY' and smoke['status'] == 'PASS'
                        else 'ERROR' if deps['status'] == 'ERROR' or smoke['status'] == 'ERROR' else 'ACTION_REQUIRED')
    report['planning_can_continue'] = True
    return report, report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-dir', type=Path, default=ROOT / 'local/validation-env')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'runs/environment-smoke')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-only', action='store_true', help='Do not install packages or run a new PSD smoke test')
    mode.add_argument('--full', action='store_true', help='Repeat PSD smoke even if a matching successful result is cached')
    args = parser.parse_args()
    report, path = initialize(args.env_dir.resolve(), args.output_dir.resolve(), args.check_only, args.full)
    try:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        report.update(status='ERROR', report_write_error=str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
