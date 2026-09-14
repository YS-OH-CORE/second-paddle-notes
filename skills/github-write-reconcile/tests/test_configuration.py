"""Configuration regression tests; never inspect or print a real token."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from test_reconcile import r


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.intent = {'version': 1, 'repository': 'owner/repo', 'ref': 'main',
                       'path': 'note.json', 'expected_sha256': '0' * 64}

    def test_token_is_opaque_not_a_guessed_prefix_format(self):
        token = 'opaque.header.signature+/=-'
        self.assertEqual(r.GitHubReadOnly(token).token, token)
        for bad in ('x y', 'x\ty', 'x\x00y', 'x' * 8193):
            with self.subTest(bad_length=len(bad)), self.assertRaises(r.CheckError):
                r.GitHubReadOnly(bad)

    def test_missing_token_flag_has_fixed_diagnostic(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'intent.json'
            path.write_text(json.dumps(self.intent))
            out = io.StringIO()
            with patch.dict(r.os.environ, {}, clear=True), patch('sys.stdout', out):
                code = r.main(['--intent', str(path), '--use-github-token'])
            self.assertEqual(code, 4)
            self.assertEqual(json.loads(out.getvalue())['reason'], 'TOKEN_NOT_SET')

    def test_public_default_ignores_environment_token(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'intent.json'
            path.write_text(json.dumps(self.intent))
            out = io.StringIO()
            with patch.dict(r.os.environ, {'GITHUB_TOKEN': 'do not use this value'}), patch('sys.stdout', out):
                with patch.object(r, 'GitHubReadOnly') as factory:
                    factory.return_value.return_value = (403, None)
                    factory.return_value.calls = 1
                    code = r.main(['--intent', str(path)])
                    factory.assert_called_once_with('')
            self.assertEqual(code, 4)
            self.assertNotIn('do not use', out.getvalue())


if __name__ == '__main__':
    unittest.main()
