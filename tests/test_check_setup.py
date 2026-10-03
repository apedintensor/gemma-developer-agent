"""Exercise portable setup and credential boundaries without real credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
BACKENDS = {
    'ai_studio': ('prototype', 'profile', 'gemini'),
    'openrouter': ('openrouter_prototype', 'openrouter_profile', 'openrouter'),
}


class SetupChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        (self.root / 'configs').mkdir()
        shutil.copyfile(SOURCE / 'tools/check_setup.py', self.root / 'tools/check_setup.py')
        self.settings = json.loads((SOURCE / 'configs/project.json').read_text(encoding='utf-8'))
        self.save_settings()
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ('AI_REGISTRY_ROOT', 'AI_REGISTRY_PROFILE', 'PYTHONPATH')}
        self.env['PYTHONUTF8'] = '1'

    def save_settings(self):
        (self.root / 'configs/project.json').write_text(json.dumps(self.settings), encoding='utf-8')

    def run_check(self, *args):
        return subprocess.run([sys.executable, '-I', str(self.root / 'tools/check_setup.py'), *args],
                              cwd=self.root, env=self.env, text=True, encoding='utf-8',
                              capture_output=True, timeout=15)

    def fake_registry(self, source, endpoint=None, service=None, backend='openrouter'):
        settings_key, _, expected_service = BACKENDS[backend]
        registry = self.root / 'fake-registry'
        (registry / 'registry').mkdir(parents=True, exist_ok=True)
        (registry / 'api_registry.py').write_text(source, encoding='utf-8')
        metadata = {'profiles': {'test-profile': {
            'service': service or expected_service,
            'base_url': endpoint or self.settings[settings_key]['base_url']}}}
        (registry / 'registry/api-profiles.json').write_text(json.dumps(metadata), encoding='utf-8')
        self.env.update(AI_REGISTRY_ROOT=str(registry), AI_REGISTRY_PROFILE='test-profile')

    def test_fresh_clone_needs_no_local_registry(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                result = self.run_check('--backend', backend)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Local registry not required', result.stdout)
                self.assertIn('Prototype backend: ' + backend, result.stdout)

    def test_default_backend_comes_from_project_configuration(self):
        self.assertEqual(self.settings['default_backend'], 'openrouter')
        self.assertIn('Prototype backend: openrouter', self.run_check().stdout)
        self.settings['default_backend'] = 'ai_studio'
        self.save_settings()
        self.assertIn('Prototype backend: ai_studio', self.run_check().stdout)
        self.settings['default_backend'] = 'unexpected'
        self.save_settings()
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_default_check_does_not_import_registry(self):
        self.fake_registry("raise AssertionError('must not import in portable mode')")
        self.assertEqual(self.run_check().returncode, 0)

    def test_changed_model_or_endpoint_is_rejected(self):
        original = json.loads(json.dumps(self.settings))
        for backend, (settings_key, _, _) in BACKENDS.items():
            for field in ('model', 'base_url', 'protocol', 'service'):
                with self.subTest(backend=backend, field=field):
                    self.settings = json.loads(json.dumps(original))
                    self.settings[settings_key][field] = 'unexpected'
                    self.save_settings()
                    self.assertNotEqual(self.run_check('--backend', backend).returncode, 0)
        self.settings = original
        self.settings['competition_model'] = 'unexpected'
        self.save_settings()
        self.assertNotEqual(self.run_check().returncode, 0)

    def test_profile_must_be_explicit(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                self.fake_registry('def load_api(*args, **kwargs): raise AssertionError()', backend=backend)
                self.env.pop('AI_REGISTRY_PROFILE')
                self.assertNotEqual(self.run_check('--backend', backend, '--check-credentials').returncode, 0)

    def test_metadata_mismatch_fails_before_loader_import(self):
        for backend in BACKENDS:
            for mismatch in ({'endpoint': 'https://example.invalid'}, {'service': 'unexpected'}):
                with self.subTest(backend=backend, mismatch=mismatch):
                    self.fake_registry("raise AssertionError('should not import')", backend=backend, **mismatch)
                    result = self.run_check('--backend', backend, '--check-credentials')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('RuntimeError', result.stderr)
                    self.assertNotIn('AssertionError', result.stderr)

    def test_metadata_check_does_not_load_credentials(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                self.fake_registry('def load_api(*args, **kwargs): raise AssertionError()', backend=backend)
                result = self.run_check('--backend', backend, '--check-registry')
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_fake_credentials_are_selected_and_not_printed(self):
        for backend, (settings_key, _, service) in BACKENDS.items():
            with self.subTest(backend=backend):
                self.fake_registry(f'''from types import SimpleNamespace
def load_api(service, profile):
    assert service == {service!r} and profile == 'test-profile'
    return SimpleNamespace(api_key='FAKE_SECRET_SENTINEL', base_url={self.settings[settings_key]['base_url']!r})
''', backend=backend)
                result = self.run_check('--backend', backend, '--check-credentials')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('FAKE_SECRET_SENTINEL', result.stdout + result.stderr)

    def test_backend_uses_its_own_local_profile_key(self):
        for backend, (_, profile_key, _) in BACKENDS.items():
            with self.subTest(backend=backend):
                self.fake_registry('def load_api(*args, **kwargs): raise AssertionError()', backend=backend)
                self.env.pop('AI_REGISTRY_PROFILE')
                local = {'profile': 'wrong-ai-studio-profile', 'openrouter_profile': 'wrong-openrouter-profile'}
                local[profile_key] = 'test-profile'
                (self.root / 'configs/local.json').write_text(json.dumps(local), encoding='utf-8')
                result = self.run_check('--backend', backend, '--check-registry')
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_profile_environment_override_has_precedence(self):
        self.fake_registry('def load_api(*args, **kwargs): raise AssertionError()')
        (self.root / 'configs/local.json').write_text(
            json.dumps({'openrouter_profile': 'different-profile'}), encoding='utf-8')
        result = self.run_check('--check-registry')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_loader_exception_does_not_disclose_secret(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                self.fake_registry("def load_api(*args, **kwargs): raise ValueError('FAKE_SECRET_SENTINEL')", backend=backend)
                result = self.run_check('--backend', backend, '--check-credentials')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ValueError', result.stderr)
                self.assertNotIn('FAKE_SECRET_SENTINEL', result.stdout + result.stderr)

    def test_runtime_endpoint_mismatch_is_rejected(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                self.fake_registry('''from types import SimpleNamespace
def load_api(*args, **kwargs):
    return SimpleNamespace(api_key='FAKE_SECRET_SENTINEL', base_url='https://example.invalid')
''', backend=backend)
                result = self.run_check('--backend', backend, '--check-credentials')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('FAKE_SECRET_SENTINEL', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
