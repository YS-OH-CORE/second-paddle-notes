"""Offline tests for the reader, not provider writes or loss injections."""
import base64
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reconcile.py'
spec = importlib.util.spec_from_file_location('reader', SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
COMMIT, TREE = 'a' * 40, 'b' * 40
RAW = b'{"ok":true}\n'
BLOB = r.github_blob(RAW)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.intent = {'version': 1, 'repository': 'owner/repo', 'ref': 'topic/recovery',
                       'path': 'notes/result.json', 'expected_sha256': hashlib.sha256(RAW).hexdigest()}
        self.records = [
            {'ref': 'refs/heads/topic/recovery', 'object': {'type': 'commit', 'sha': COMMIT}},
            {'sha': COMMIT, 'tree': {'sha': TREE}},
            {'sha': TREE, 'truncated': False, 'tree': [{'path': self.intent['path'], 'type': 'blob', 'mode': '100644', 'sha': BLOB, 'size': len(RAW)}]},
            {'sha': BLOB, 'size': len(RAW), 'encoding': 'base64', 'content': base64.encodebytes(RAW).decode()},
        ]
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        return 200, self.records[len(self.paths) - 1]

    def run_case(self):
        result = r.reconcile(self.intent, self.get)
        self.assertFalse(result['retry_authorized'])
        return result

    def test_match_pins_branch_once_and_ignores_later_head(self):
        result = self.run_case()
        self.assertEqual(result['status'], 'content_match')
        self.assertEqual(result['snapshot_commit'], COMMIT)
        self.assertEqual(self.paths, [
            '/repos/owner/repo/git/ref/heads/topic/recovery',
            '/repos/owner/repo/git/commits/' + COMMIT,
            '/repos/owner/repo/git/trees/' + TREE + '?recursive=1',
            '/repos/owner/repo/git/blobs/' + BLOB])
        self.assertNotIn('content', result)

    def test_fixed_commit_uses_three_gets(self):
        self.intent['ref'] = COMMIT
        self.records.pop(0)
        self.assertEqual(self.run_case()['status'], 'content_match')
        self.assertEqual(len(self.paths), 3)

    def test_conflicting_digest_is_not_success(self):
        self.intent['expected_sha256'] = '0' * 64
        self.assertEqual(self.run_case()['status'], 'content_conflict')

    def test_absent_complete_tree_does_not_authorize_retry(self):
        self.records[2]['tree'] = []
        self.assertEqual(self.run_case()['status'], 'absent_at_snapshot')
        self.assertEqual(len(self.paths), 3)

    def test_truncated_tree_never_means_absent(self):
        self.records[2].update(tree=[], truncated=True)
        result = self.run_case()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['reason'], 'TREE_INCOMPLETE')

    def test_http_errors_never_mean_absent(self):
        for status in (301, 401, 403, 404, 409, 429, 500, 503):
            with self.subTest(status=status):
                result = r.reconcile(self.intent, lambda _: (status, {'secret': 'do not echo'}))
                self.assertEqual(result['status'], 'unknown')
                self.assertFalse(result['retry_authorized'])
                self.assertNotIn('secret', json.dumps(result))

    def test_unknown_transport(self):
        def fail(_):
            raise r.CheckError('TRANSPORT_UNAVAILABLE')
        self.assertEqual(r.reconcile(self.intent, fail)['status'], 'unknown')

    def test_branch_mismatch_rejected(self):
        self.records[0]['ref'] = 'refs/heads/other'
        self.assertEqual(self.run_case()['reason'], 'REF_IDENTITY')

    def test_commit_mismatch_rejected(self):
        self.records[1]['sha'] = 'c' * 40
        self.assertEqual(self.run_case()['reason'], 'COMMIT_IDENTITY')

    def test_symlink_directory_and_submodule_rejected(self):
        for kind, mode in (('blob', '120000'), ('commit', '160000'), ('tree', '040000')):
            with self.subTest(kind=kind):
                self.paths = []
                self.records[2]['tree'][0].update(type=kind, mode=mode)
                self.assertEqual(self.run_case()['reason'], 'NOT_REGULAR_FILE')
                self.assertEqual(len(self.paths), 3)

    def test_duplicate_path_rejected(self):
        self.records[2]['tree'].append(deepcopy(self.records[2]['tree'][0]))
        self.assertEqual(self.run_case()['reason'], 'TREE_DUPLICATE_PATH')

    def test_large_and_boolean_file_sizes_rejected(self):
        for size in (True, -1, 65537):
            with self.subTest(size=size):
                self.paths = []
                self.records[2]['tree'][0]['size'] = size
                self.assertEqual(self.run_case()['reason'], 'FILE_SIZE_LIMIT')

    def test_returned_blob_bytes_must_match_tree(self):
        self.records[3]['content'] = base64.b64encode(b'{"ok":null}\n').decode()
        self.assertEqual(self.run_case()['reason'], 'BLOB_BYTES_DIFFER')

    def test_representation_wraps_accepted_but_alphabet_is_strict(self):
        good = deepcopy(self.records[3])
        good['content'] = '\r\n\t ' + good['content']
        self.assertEqual(r.decode_blob(good, BLOB, len(RAW)), RAW)
        for suffix in ('!', '\v', '\u200b'):
            with self.subTest(suffix=suffix), self.assertRaises(r.CheckError):
                r.decode_blob(dict(good, content=good['content'] + suffix), BLOB, len(RAW))

    def test_noncanonical_padding_bits_rejected(self):
        raw = b'f'
        body = {'sha': r.github_blob(raw), 'size': 1, 'encoding': 'base64', 'content': 'Zh=='}
        with self.assertRaisesRegex(r.CheckError, 'BASE64_NONCANONICAL'):
            r.decode_blob(body, r.github_blob(raw), 1)

    def test_malformed_provider_is_fixed_error(self):
        self.records[1]['tree'] = None
        self.assertEqual(self.run_case()['reason'], 'MALFORMED_INPUT_OR_PROVIDER_RECORD')

    def test_unsafe_intents_do_not_make_requests(self):
        mutations = [('ref', '../main'), ('ref', 'x?ref=main'), ('repository', 'owner/repo/extra'),
                     ('path', '../secret'), ('path', '/absolute'), ('path', 'a//b'),
                     ('path', 'a\\b'), ('version', True), ('expected_sha256', 'short')]
        for k, v in mutations:
            with self.subTest(k=k, v=v):
                self.paths = []
                intent = dict(self.intent, **{k: v})
                result = r.reconcile(intent, self.get)
                self.assertEqual(result['status'], 'unknown')
                self.assertEqual(self.paths, [])

    def test_json_duplicate_nonfinite_rejected(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(r.CheckError):
                r.strict_json(raw)

    def test_get_transport_has_no_body_and_optional_token(self):
        for token in ('', 'github_pat_dummy'):
            with self.subTest(token=bool(token)):
                client = r.GitHubReadOnly(token)
                response = io.BytesIO(b'{}')
                response.status = 200
                with patch.object(client.opener, 'open', return_value=response) as opened:
                    self.assertEqual(client('/repos/owner/repo/git/commits/' + COMMIT), (200, {}))
                req = opened.call_args.args[0]
                self.assertEqual(req.get_method(), 'GET')
                self.assertIsNone(req.data)
                self.assertTrue(req.full_url.startswith('https://api.github.com/repos/'))
                self.assertEqual(req.has_header('Authorization'), bool(token))

    def test_redirects_refused(self):
        self.assertIsNone(r.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid/'))

    def test_transport_does_not_read_http_error_body(self):
        client = r.GitHubReadOnly('github_pat_dummy')
        exc = urllib.error.HTTPError('https://api.github.com', 404, 'private details', {}, io.BytesIO(b'sensitive'))
        with patch.object(client.opener, 'open', side_effect=exc):
            self.assertEqual(client('/repos/owner/repo/git/commits/' + COMMIT), (404, None))

    def test_transport_body_and_call_limits(self):
        client = r.GitHubReadOnly()
        response = io.BytesIO(b'x' * (r.MAX_BODY + 1))
        response.status = 200
        with patch.object(client.opener, 'open', return_value=response), self.assertRaisesRegex(r.CheckError, 'HTTP_BODY_TOO_LARGE'):
            client('/repos/owner/repo/git/commits/' + COMMIT)
        client.calls = 4
        with self.assertRaisesRegex(r.CheckError, 'READ_BUDGET'):
            client('/repos/owner/repo/git/commits/' + COMMIT)

    def test_token_injection_rejected(self):
        with self.assertRaisesRegex(r.CheckError, 'TOKEN_FORMAT'):
            r.GitHubReadOnly('x\nAuthorization: y')


if __name__ == '__main__':
    unittest.main()
