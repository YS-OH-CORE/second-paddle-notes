"""Verify the already requested test patch; no model/package tests are executed.

Youngseok Oh and Zero, AI collaboration partners. This only creates a new
local evidence directory and fetches immutable public repository files.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import email.utils
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

PATCH_COMMIT = 'c0127dc37547ff8b6454be16684fe3b5331d2834'
PATCH_BLOB = '1ea87d51267bfef91186ad94bbe702582b98de60'
REFS = {
    'original_tested_base': '89b6b17574892ec0770551537a3fe69d6886703e',
    'closed_pr_snapshot': 'e435677fb9981b3f2bfc7abeaabcb394e47c29e2',
    'current_main_at_check': '6e4bcc5db795e369f900a00da304bfdeaeee5ac5',
}
TEST_PATH = 'tests/generation/test_logits_process.py'
METHOD = 'test_bias_dist_processor_zero_token_roundtrip_full_prefix'


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def download(url: str, path: Path) -> bytes:
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Zero-requested-regression-portability'})
            with urllib.request.urlopen(request, timeout=25) as response:
                data = response.read(1_000_001)
            if len(data) > 1_000_000:
                raise ValueError('Unexpectedly large text source')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            time.sleep(2)
            return data
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            delay = 20 * (attempt + 1)
            retry = exc.headers.get('Retry-After')
            if retry:
                try:
                    delay = max(delay, float(retry))
                except ValueError:
                    delay = max(delay, (email.utils.parsedate_to_datetime(retry) - dt.datetime.now(dt.timezone.utc)).total_seconds())
            if delay > 60:
                raise RuntimeError('Requested rate-limit delay exceeds the bounded check') from exc
            time.sleep(delay)
    raise AssertionError('unreachable')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(exist_ok=False, parents=True)
    patch = root / 'roundtrip.patch'
    report = {'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'python': sys.version, 'kind': 'patch_application_and_AST_only',
              'new_pytest_runs': 0, 'new_model_calls': 0, 'rows': [], 'completed': False}
    try:
        patch_data = download(
            'https://raw.githubusercontent.com/YS-OH-CORE/second-paddle-notes/' + PATCH_COMMIT +
            '/checks/transformers-49093/pr49099/roundtrip.patch', patch)
        assert git_blob(patch_data) == PATCH_BLOB
        report['patch_blob'] = PATCH_BLOB
        report['patch_sha256'] = hashlib.sha256(patch_data).hexdigest()
        for name, commit in REFS.items():
            folder = root / name
            target = folder / TEST_PATH
            original = download('https://raw.githubusercontent.com/huggingface/transformers/' + commit + '/' + TEST_PATH, target)
            (folder / 'test_original.py').write_bytes(original)
            row = {'snapshot': name, 'commit': commit, 'original_blob': git_blob(original)}
            report['rows'].append(row)
            results = []
            for options in (['--check'], []):
                completed = subprocess.run(['git', 'apply', *options, str(patch)], cwd=folder,
                                           text=True, capture_output=True, timeout=15)
                results.append({'options': options, 'returncode': completed.returncode,
                                'stdout': completed.stdout, 'stderr': completed.stderr})
                if completed.returncode:
                    break
            (folder / 'git_apply.json').write_text(json.dumps(results, indent=2) + '\n')
            row['patch_applies'] = len(results) == 2 and all(r['returncode'] == 0 for r in results)
            if not row['patch_applies']:
                continue
            before, after = ast.parse(original), ast.parse(target.read_bytes())
            before_class = next(n for n in before.body if isinstance(n, ast.ClassDef) and n.name == 'LogitsProcessorTest')
            after_class = next(n for n in after.body if isinstance(n, ast.ClassDef) and n.name == 'LogitsProcessorTest')
            assert not any(getattr(n, 'name', None) == METHOD for n in before_class.body)
            added = [n for n in after_class.body if getattr(n, 'name', None) == METHOD]
            assert len(added) == 1
            row['added_method_ast_sha256'] = hashlib.sha256(ast.dump(added[0]).encode()).hexdigest()
            # Undo only the intended AST additions, then compare all remaining code.
            after_class.body.remove(added[0])
            after.body = [n for n in after.body if not (
                isinstance(n, ast.Import) and len(n.names) == 1 and n.names[0].name == 'tempfile')]
            for node in after.body:
                if isinstance(node, ast.ImportFrom) and node.module == 'transformers':
                    node.names = [n for n in node.names if n.name != 'GenerationConfig']
            row['only_requested_method_and_imports_added'] = ast.dump(before) == ast.dump(after)
            row['patched_blob'] = git_blob(target.read_bytes())
            row['patched_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        report['completed'] = len(report['rows']) == len(REFS)
        report['all_patch_checks_pass'] = all(r.get('patch_applies') and r.get('only_requested_method_and_imports_added') for r in report['rows'])
        report['same_test_method_all_snapshots'] = len({r.get('added_method_ast_sha256') for r in report['rows']}) == 1 and report['all_patch_checks_pass']
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    (root / 'PORTABILITY.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['completed'] and report.get('all_patch_checks_pass') else 1


if __name__ == '__main__':
    raise SystemExit(main())
