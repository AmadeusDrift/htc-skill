import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('environment', ROOT / 'scripts' / 'check_environment.py')
environment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class EnvironmentTests(unittest.TestCase):
    def test_check_only_missing_environment_does_not_install(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(environment, 'run_command') as run:
            result = environment.ensure_dependencies(Path(directory) / 'env', repair=False)
            self.assertEqual(result['status'], 'ACTION_REQUIRED')
            run.assert_not_called()

    def test_existing_dependencies_are_not_reinstalled(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            exe = environment.venv_python(folder)
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.touch()
            with patch.object(environment, 'package_versions', return_value={'PyYAML': '6.0.3', 'Pillow': '13.0.0'}), patch.object(environment, 'run_command') as run:
                result = environment.ensure_dependencies(folder, repair=True)
                self.assertEqual(result['status'], 'READY')
                run.assert_not_called()

    def test_only_missing_package_is_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            exe = environment.venv_python(folder)
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.touch()
            with patch.object(environment, 'package_versions', side_effect=[{'Pillow': '13.0.0'}, {'PyYAML': '6.0.3', 'Pillow': '13.0.0'}]), patch.object(environment, 'run_command', return_value='') as run:
                result = environment.ensure_dependencies(folder, repair=True)
                self.assertEqual(result['status'], 'READY')
                self.assertIn('PyYAML==6.0.3', run.call_args.args[0])
                self.assertNotIn('Pillow==13.0.0', run.call_args.args[0])

    def test_install_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            exe = environment.venv_python(folder)
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.touch()
            with patch.object(environment, 'package_versions', return_value={}), patch.object(environment, 'run_command', side_effect=RuntimeError('network unavailable')):
                result = environment.ensure_dependencies(folder, repair=True)
                self.assertEqual(result['status'], 'ERROR')
                self.assertIn('network unavailable', result['detail'])

    def test_failed_smoke_is_not_reused(self):
        self.assertFalse(environment.can_reuse_smoke({'fingerprint': 'same', 'status': 'ERROR'}, 'same'))

    def test_environment_change_invalidates_smoke_cache(self):
        self.assertFalse(environment.can_reuse_smoke({'fingerprint': 'old', 'status': 'PASS'}, 'new'))

    def test_cache_requires_artifacts_that_still_exist(self):
        self.assertFalse(environment.can_reuse_smoke({'fingerprint': 'same', 'status': 'PASS', 'artifacts': ['missing.psd']}, 'same'))

    def test_successful_smoke_can_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'template.psd'
            artifact.write_bytes(b'8BPS')
            self.assertTrue(environment.can_reuse_smoke({'fingerprint': 'same', 'status': 'PASS', 'artifacts': [str(artifact)]}, 'same'))

    def test_changed_artifact_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'template.psd'
            artifact.write_bytes(b'8BPS')
            cached = {'fingerprint': 'same', 'status': 'PASS', 'artifacts': [str(artifact)],
                      'artifact_hashes': {str(artifact): environment.sha256(artifact)}}
            artifact.write_bytes(b'changed template')
            self.assertFalse(environment.can_reuse_smoke(cached, 'same'))

    def test_missing_photoshop_reports_partial_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch.object(environment, 'ensure_dependencies', return_value={'status': 'READY'}), patch.object(environment, 'powershell_probe', return_value={'status': 'ACTION_REQUIRED', 'detail': 'Photoshop missing'}):
                report, path = environment.initialize(folder / 'env', folder / 'output')
            self.assertEqual(report['status'], 'ACTION_REQUIRED')
            self.assertTrue(report['planning_can_continue'])
            self.assertEqual(report['psd_smoke']['status'], 'NOT_TESTED')


if __name__ == '__main__':
    unittest.main()
