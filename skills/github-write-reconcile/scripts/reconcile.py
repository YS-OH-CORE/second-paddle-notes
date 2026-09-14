"""Read-only GitHub file reconciliation. Never submits or retries a write."""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Callable
import urllib.error
import urllib.parse
import urllib.request

API = 'https://api.github.com'
MAX_BODY = 2_000_000
MAX_FILE = 65_536
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
EXIT = {'content_match': 0, 'content_conflict': 2, 'absent_at_snapshot': 3, 'unknown': 4}
Get = Callable[[str], tuple[int, object]]


class CheckError(ValueError):
    """Fixed diagnostic codes, never remote response bodies or credentials."""


def need(ok: bool, code: str) -> None:
    if not ok:
        raise CheckError(code)


def strict_json(raw: bytes | str) -> object:
    def pairs(items):
        result = {}
        for k, v in items:
            need(k not in result, 'DUPLICATE_JSON_KEY')
            result[k] = v
        return result
    def constant(_):
        raise CheckError('NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def validate_intent(intent: object) -> dict:
    need(isinstance(intent, dict), 'INTENT_NOT_OBJECT')
    need(set(intent) == {'version', 'repository', 'ref', 'path', 'expected_sha256'}, 'INTENT_FIELDS')
    need(type(intent['version']) is int and intent['version'] == 1, 'INTENT_VERSION')
    for k in ('repository', 'ref', 'path', 'expected_sha256'):
        need(type(intent[k]) is str, 'INTENT_VALUE_TYPE')
    repo, ref, path = intent['repository'], intent['ref'], intent['path']
    need(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', repo)), 'REPOSITORY_FORMAT')
    need(1 <= len(ref) <= 256 and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]*', ref)), 'REF_FORMAT')
    need('..' not in ref and '//' not in ref and not ref.endswith(('/', '.', '.lock')), 'REF_FORMAT')
    need(all(not part.startswith('.') for part in ref.split('/')), 'REF_FORMAT')
    p = PurePosixPath(path)
    need(1 <= len(path.encode('utf-8')) <= 1024 and bool(p.parts) and not p.is_absolute()
         and str(p) == path and '..' not in p.parts and '\\' not in path
         and all(ord(c) >= 32 and ord(c) != 127 for c in path), 'PATH_FORMAT')
    need(bool(HEX64.fullmatch(intent['expected_sha256'])), 'EXPECTED_DIGEST_FORMAT')
    return intent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubReadOnly:
    """GET only, fixed host, bounded response, redirects refused."""
    def __init__(self, token: str = ''):
        need(len(token) <= 8192 and all(33 <= ord(c) <= 126 for c in token), 'TOKEN_FORMAT')
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)
        self.calls = 0

    def __call__(self, path: str) -> tuple[int, object]:
        need(path.startswith('/repos/') and '://' not in path and '#' not in path, 'API_PATH')
        self.calls += 1
        need(self.calls <= 4, 'READ_BUDGET')
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                   'User-Agent': 'second-paddle-readonly-reconcile/1'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        req = urllib.request.Request(API + path, method='GET', headers=headers)
        try:
            with self.opener.open(req, timeout=10) as response:
                raw = response.read(MAX_BODY + 1)
                need(len(raw) <= MAX_BODY, 'HTTP_BODY_TOO_LARGE')
                return response.status, strict_json(raw)
        except urllib.error.HTTPError as exc:
            # A 404/403/429 is not proof that an earlier operation never ran.
            code = exc.code
            exc.close()
            return code, None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise CheckError('TRANSPORT_UNAVAILABLE') from None


def github_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def decode_blob(body: object, expected_blob: str, expected_size: int) -> bytes:
    need(isinstance(body, dict), 'BLOB_SHAPE')
    need(body.get('encoding') == 'base64' and body.get('sha') == expected_blob, 'BLOB_IDENTITY')
    need(type(body.get('size')) is int and body['size'] == expected_size, 'BLOB_SIZE')
    text = body.get('content')
    need(type(text) is str and len(text) <= 2 * MAX_FILE + 1024, 'BASE64_SIZE')
    compact = text.translate(str.maketrans('', '', '\r\n\t '))
    try:
        raw = base64.b64decode(compact, validate=True)
    except (ValueError, binascii.Error):
        raise CheckError('BASE64_INVALID') from None
    need(base64.b64encode(raw).decode('ascii') == compact, 'BASE64_NONCANONICAL')
    need(len(raw) == expected_size and github_blob(raw) == expected_blob, 'BLOB_BYTES_DIFFER')
    return raw


def reconcile(intent: object, get: Get) -> dict:
    """Resolve a branch once; inspect immutable commit/tree/blob records only."""
    result = {'version': 1, 'status': 'unknown', 'retry_authorized': False,
              'scope': 'File content at one Git snapshot, not original HTTP outcome or exactly-once'}
    try:
        i = validate_intent(intent)
        result.update(repository=i['repository'], requested_ref=i['ref'], path=i['path'],
                      expected_sha256=i['expected_sha256'])
        prefix = '/repos/' + i['repository']
        def read(path):
            status, body = get(prefix + path)
            need(status == 200, 'PROVIDER_HTTP_' + str(status))
            need(isinstance(body, dict), 'PROVIDER_SHAPE')
            return body
        commit = i['ref']
        if not HEX40.fullmatch(commit):
            obj = read('/git/ref/heads/' + urllib.parse.quote(commit, safe='/'))
            need(obj.get('ref') == 'refs/heads/' + commit, 'REF_IDENTITY')
            need(obj.get('object', {}).get('type') == 'commit', 'REF_NOT_COMMIT')
            commit = obj['object']['sha']
        need(type(commit) is str and bool(HEX40.fullmatch(commit)), 'COMMIT_IDENTITY')
        result['snapshot_commit'] = commit
        obj = read('/git/commits/' + commit)
        need(obj.get('sha') == commit, 'COMMIT_IDENTITY')
        tree = obj['tree']['sha']
        need(type(tree) is str and bool(HEX40.fullmatch(tree)), 'TREE_IDENTITY')
        obj = read('/git/trees/' + tree + '?recursive=1')
        need(obj.get('sha') == tree and obj.get('truncated') is False, 'TREE_INCOMPLETE')
        entries = obj.get('tree')
        need(type(entries) is list and len(entries) <= 5000, 'TREE_LIMIT')
        need(all(isinstance(x, dict) and type(x.get('path')) is str for x in entries), 'TREE_ENTRY_SHAPE')
        names = [x['path'] for x in entries]
        need(len(names) == len(set(names)), 'TREE_DUPLICATE_PATH')
        matches = [x for x in entries if x['path'] == i['path']]
        if not matches:
            result.update(status='absent_at_snapshot', reason='PATH_NOT_IN_COMPLETE_TREE')
            return result
        entry = matches[0]
        need(entry.get('type') == 'blob' and entry.get('mode') in ('100644', '100755'), 'NOT_REGULAR_FILE')
        blob, size = entry.get('sha'), entry.get('size')
        need(type(blob) is str and bool(HEX40.fullmatch(blob)), 'BLOB_IDENTITY')
        need(type(size) is int and 0 <= size <= MAX_FILE, 'FILE_SIZE_LIMIT')
        raw = decode_blob(read('/git/blobs/' + blob), blob, size)
        digest = hashlib.sha256(raw).hexdigest()
        result.update(status='content_match' if digest == i['expected_sha256'] else 'content_conflict',
                      observed_sha256=digest, blob_sha1=blob, bytes=len(raw))
    except CheckError as exc:
        result.update(status='unknown', reason=str(exc))
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        result.update(status='unknown', reason='MALFORMED_INPUT_OR_PROVIDER_RECORD')
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--intent', type=Path, required=True, help='Local expected identity JSON. No content is uploaded.')
    p.add_argument('--use-github-token', action='store_true', help='Explicitly use GITHUB_TOKEN for GETs to api.github.com only.')
    args = p.parse_args(argv)
    try:
        with args.intent.open('rb') as f:
            raw = f.read(8193)
        need(len(raw) <= 8192, 'INTENT_TOO_LARGE')
        intent = strict_json(raw)
        token = os.environ.get('GITHUB_TOKEN', '') if args.use_github_token else ''
        need(not args.use_github_token or bool(token), 'TOKEN_NOT_SET')
        get = GitHubReadOnly(token)
        result = reconcile(intent, get)
        result['get_requests'] = get.calls
    except CheckError as exc:
        result = {'version': 1, 'status': 'unknown', 'reason': str(exc), 'retry_authorized': False}
    except (OSError, ValueError, RecursionError):
        result = {'version': 1, 'status': 'unknown', 'reason': 'LOCAL_INPUT_OR_CONFIGURATION', 'retry_authorized': False}
    result['reader_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
