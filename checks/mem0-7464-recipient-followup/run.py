# SPDX-License-Identifier: Apache-2.0
"""Rerun Souptik96's unchanged regressions after their response to review.

Youngseok Oh x Zero. No new runtime fix, real memories, or model calls.
The current fork branch and the closed PR's older head are distinct snapshots.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

CURRENT = '127bb79725aeb09d70e58620fd1d88476abf9aca'
OLDER = 'cec74a8ebf5a9d6724104d4867868da118b58205'
SOURCE = 'mem0/vector_stores/langchain.py'
IDENTITIES = {
    SOURCE: '09e2ee4f9a5471878c6166b3fdab752389354a9c',
    'tests/memory/test_main.py': 'df10946acb1821e1a94dedf7cc1854b8f2ebbce8',
    'tests/vector_stores/test_langchain_vector_store.py': '9e55ace7ac0f73ffa66f3496099ffcd81f79682b',
}
VECTOR = 'tests/vector_stores/test_langchain_vector_store.py::'
MEMORY = 'tests/memory/test_main.py::'
NODES = [
    VECTOR + 'test_list_with_exception',
    VECTOR + 'test_list_non_chroma_client_raises_not_implemented',
    VECTOR + 'test_list_chroma_empty_result_returns_nested_empty_list',
    MEMORY + 'test_get_all_with_non_chroma_langchain_store_raises',
    MEMORY + 'test_delete_all_with_non_chroma_langchain_store_raises_without_deleting',
    MEMORY + 'test_async_get_all_and_delete_all_with_non_chroma_langchain_store_raise',
    MEMORY + 'test_delete_all_with_populated_faiss_langchain_store_keeps_records_and_raises',
]
EXPECTED_OLD_FAILURES = {n.split('::')[-1] for n in NODES if 'empty_result' not in n}


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    repo, out, home = root/'repo', root/'output', root/'home'
    for path in (repo, out, home):
        path.mkdir()
    env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'LANG': 'C.UTF-8',
           'GIT_LFS_SKIP_SMUDGE': '1', 'GIT_TERMINAL_PROMPT': '0',
           'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    report = {'completed': False, 'candidate_commit': CURRENT, 'older_source_commit': OLDER,
              'selection': NODES, 'runs': {}, 'model_calls': 0,
              'workflow_commit': os.environ.get('GITHUB_SHA'), 'run_id': os.environ.get('GITHUB_RUN_ID')}
    original = None

    def call(args, label, *, custom_env=None, timeout=90, check=True):
        r = subprocess.run(list(map(str, args)), cwd=repo, env=custom_env or env,
                           capture_output=True, text=True, timeout=timeout)
        (out/(label+'.log')).write_text('COMMAND '+repr(args)+'\n'+r.stdout+'\nSTDERR\n'+r.stderr, encoding='utf-8')
        print(label, r.returncode, r.stdout[-3000:], r.stderr[-1000:], flush=True)
        if check:
            r.check_returncode()
        return r

    try:
        shutil.copy2(Path(__file__), out/'run.py')
        call(['git', 'init', '-q'], 'git_init')
        call(['git', 'fetch', '--depth=1', 'https://github.com/Souptik96/mem0.git', CURRENT], 'git_fetch', timeout=120)
        call(['git', 'checkout', '--detach', 'FETCH_HEAD'], 'git_checkout')
        assert call(['git', 'rev-parse', 'HEAD'], 'git_identity').stdout.strip() == CURRENT
        for path, expected in IDENTITIES.items():
            raw = (repo/path).read_bytes()
            assert blob(raw) == expected, (path, blob(raw))
            target = out/'sources'/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        original = (repo/SOURCE).read_bytes()
        shutil.copy2(repo/'LICENSE', out/'LICENSE.upstream')
        url = 'https://raw.githubusercontent.com/Souptik96/mem0/'+OLDER+'/'+SOURCE
        with urllib.request.urlopen(url, timeout=25) as response:
            old_source = response.read(100001)
        assert len(old_source) <= 100000
        assert blob(old_source) == 'c3f5f60ebc9418730235493eba2a73f9cb3f8a34'
        (out/'older_langchain.py').write_bytes(old_source)
        report['source_blobs'] = {'candidate': blob(original), 'older': blob(old_source), **IDENTITIES}
        call([sys.executable, '-m', 'venv', root/'venv'], 'venv', timeout=30)
        py = root/'venv/bin/python'
        # Install only the dependencies needed by the existing selected tests.
        # Bounds come from the pinned project's optional groups. Save resolution.
        call([py, '-m', 'pip', 'install', '-e', str(repo)+'[test]',
              'langchain>=0.3.30,<1.0.0', 'langchain-community>=0.3.27,<1.0.0',
              'langchain-core>=0.3.85,<1.0.0', 'faiss-cpu>=1.7.4'], 'install', timeout=240)
        frozen = call([py, '-m', 'pip', 'freeze', '--all'], 'freeze')
        (out/'environment.txt').write_text(frozen.stdout, encoding='utf-8')
        for label, content in (('candidate', original), ('older_fallback', old_source)):
            (repo/SOURCE).write_bytes(content)
            fresh = root/(label+'-home')
            fresh.mkdir()
            child_env = {**env, 'HOME': str(fresh), 'XDG_CONFIG_HOME': str(fresh/'config'),
                         'PYTHONPATH': str(repo), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                         'MEM0_TELEMETRY': 'false', 'LANGSMITH_TRACING': 'false',
                         'LANGCHAIN_TRACING_V2': 'false', 'HF_HUB_OFFLINE': '1'}
            xml = out/(label+'.xml')
            args = ['-q', '--noconftest', '-p', 'pytest_mock', '-p', 'pytest_asyncio.plugin',
                    '-p', 'no:cacheprovider', '-o', 'addopts=', '--junitxml='+str(xml), *NODES]
            code = (
                'import socket,inspect,pathlib\n'
                'def deny(*a,**k): raise RuntimeError("Network is outside this synthetic regression check")\n'
                'socket.socket.connect=socket.socket.connect_ex=socket.getaddrinfo=deny\n'
                'import faiss,langchain_community\n'
                'import mem0.vector_stores.langchain as tested\n'
                'assert pathlib.Path(inspect.getfile(tested)).resolve()==pathlib.Path('+repr(str(repo/SOURCE))+')\n'
                'import pytest\n'
                'raise SystemExit(pytest.main('+repr(args)+'))\n'
            )
            (out/(label+'_entry.py')).write_text(code, encoding='utf-8')
            r = call([py, '-B', out/(label+'_entry.py')], label, custom_env=child_env, timeout=100, check=False)
            tree = ET.parse(xml)
            cases = tree.findall('.//testcase')
            failures = [n.attrib['name'] for n in cases if n.find('failure') is not None]
            errors = [n.attrib['name'] for n in cases if n.find('error') is not None]
            skipped = [n.attrib['name'] for n in cases if n.find('skipped') is not None]
            row = {'tests': len(cases), 'failed': failures, 'errors': errors, 'skipped': skipped,
                   'exit': r.returncode, 'source_blob': blob(content)}
            report['runs'][label] = row
            assert len(cases) == 7 and not errors and not skipped, row
            expected = set() if label == 'candidate' else EXPECTED_OLD_FAILURES
            assert set(failures) == expected, row
            assert r.returncode == (0 if label == 'candidate' else 1), row
            for path, expected_blob in IDENTITIES.items():
                if path != SOURCE:
                    assert blob((repo/path).read_bytes()) == expected_blob, 'Test source changed'
        report['completed'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        if original is not None:
            (repo/SOURCE).write_bytes(original)
            report['candidate_source_restored'] = (repo/SOURCE).read_bytes() == original
        save(out/'SUMMARY.json', report)
        print('SUMMARY '+json.dumps(report), flush=True)
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
