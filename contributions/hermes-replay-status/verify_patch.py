#!/usr/bin/env python3
"""Check a narrow patch against real imports from the pinned Hermes source.

Only run against a disposable checkout. No model, gateway or account is started.
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
import xml.etree.ElementTree as ET

REV = '6c3d4a4af70d76b7365bf19e9420ffdcbb9830ad'
BLOB = '7af23b143e3f3c8bbc01d09c98b7be535f910961'
TEST = 'tests/agent/test_replay_cleanup_structured_results.py'
MODULE = 'agent/replay_cleanup.py'
DB_TEST = 'tests/agent/test_replay_cleanup_sessiondb_roundtrip.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(upstream, out):
    upstream = upstream.resolve()
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve()
    patch = Path(__file__).with_name('replay_cleanup.patch').resolve()
    rev = subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True).strip()
    if rev != REV:
        raise ValueError('Checkout is not the inspected upstream revision')
    original = (upstream/MODULE).read_bytes()
    actual_blob = hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest()
    if actual_blob != BLOB or (upstream/TEST).exists() or (upstream/DB_TEST).exists():
        raise ValueError('Source changed or proposed regression file already exists')
    if subprocess.check_output(['git','status','--porcelain'],cwd=upstream):
        raise ValueError('Use a clean disposable checkout')
    (out/'home').mkdir()
    env = {key:os.environ[key] for key in ('PATH','SYSTEMROOT','TMPDIR','TEMP','TMP') if key in os.environ}
    env.update(HOME=str(out/'home'), HERMES_HOME=str(out/'home/hermes'),
               PYTHONPATH=str(upstream), PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1',
               PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TZ='UTC', LANG='C.UTF-8')

    def tests(label, file):
        report = out/(label+'.xml')
        command = [sys.executable,'-m','pytest','-o','addopts=', '-q',file,'--junitxml='+str(report)]
        test_env = dict(env, REPLAY_ROUNDTRIP_EVIDENCE=str(out/(label+'-roundtrip.jsonl')))
        result = subprocess.run(command,cwd=upstream,env=test_env,capture_output=True,text=True,timeout=120)
        (out/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if not report.exists():
            raise RuntimeError(label+': no actual pytest report was returned')
        root = ET.parse(report).getroot()
        cases = root.findall('.//testcase')
        data = dict(exit_code=result.returncode, tests=len(cases),
                    failures=sum(c.find('failure') is not None for c in cases),
                    errors=sum(c.find('error') is not None for c in cases),
                    skipped=sum(c.find('skipped') is not None for c in cases),
                    failed_cases=[c.attrib['name'] for c in cases if c.find('failure') is not None])
        print(label, json.dumps(data), flush=True)
        return data

    subprocess.run(['git','apply','--check',str(patch)],cwd=upstream,check=True)
    subprocess.run(['git','apply','--include='+TEST,str(patch)],cwd=upstream,check=True)
    before = tests('before',TEST)
    if before['exit_code'] != 1 or before['errors'] or before['skipped'] or before['tests'] != 27 or before['failures'] < 1:
        raise RuntimeError('Baseline did not demonstrate the expected assertion failures; inspect before.txt')
    shutil.copyfile(Path(__file__).with_name(Path(DB_TEST).name), upstream/DB_TEST)
    db_before = tests('db-before',DB_TEST)
    if db_before['exit_code'] != 1 or db_before['errors'] or db_before['skipped'] or db_before['tests'] != 8 or db_before['failures'] < 1:
        raise RuntimeError('DB baseline did not demonstrate assertion failures')
    subprocess.run(['git','apply','--include='+MODULE,str(patch)],cwd=upstream,check=True)
    after = tests('after',TEST)
    if after['exit_code'] or after['failures'] or after['errors'] or after['skipped'] or after['tests'] != 27:
        raise RuntimeError('Patched regression cases did not all pass')
    db_after = tests('db-after',DB_TEST)
    if db_after['exit_code'] or db_after['failures'] or db_after['errors'] or db_after['skipped'] or db_after['tests'] != 8:
        raise RuntimeError('Patched DB restart tests did not pass')
    existing = tests('existing','tests/agent/test_replay_cleanup.py')
    if existing['exit_code'] or existing['failures'] or existing['errors'] or existing['skipped'] or not existing['tests']:
        raise RuntimeError('Existing replay cleanup tests did not pass')
    changed = subprocess.check_output(['git','diff','--name-only'],cwd=upstream,text=True).splitlines()
    if changed != [MODULE]:
        raise RuntimeError('Unexpected tracked source changes')
    identity = subprocess.check_output([sys.executable,'-c',
        'import json,agent.replay_cleanup as r,agent.tool_dispatch_helpers as h; '
        'print(json.dumps({"replay_module":r.__file__,"message_builder_module":h.__file__}))'],
        cwd=upstream,env=env,text=True,timeout=25)
    loaded = json.loads(identity)
    if Path(loaded['replay_module']).resolve() != upstream/MODULE:
        raise RuntimeError('Imported a different replay module')
    if Path(loaded['message_builder_module']).resolve() != upstream/'agent/tool_dispatch_helpers.py':
        raise RuntimeError('Imported a different message builder')
    summary = dict(status='verified', source_revision=REV, source_blob=BLOB,
        patch_sha256=sha(patch.read_bytes()), patched_module_sha256=sha((upstream/MODULE).read_bytes()),
        before=before, after=after, db_before=db_before, db_after=db_after, existing=existing, real_imports=loaded,
        source_functions_stubbed=False, model_calls=0, gateway_started=False,
        scope='Synthetic in-memory tests and real SessionDB persistence with separate writer/reader processes, then actual replay cleanup. No gateway restart, provider request or model evaluation.',
        residual='Legacy unstructured or wrapped text still uses the old heuristic. This patch does not authenticate interruption provenance.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    verify(args.upstream,args.out)
