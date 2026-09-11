#!/usr/bin/env python3
"""Bounded review of PR22982 in a clean disposable checkout, without a model."""
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

REV = 'addb69bc409dae7d1c0ae9f2dc571fd4a39d8fc8'
SOURCE = 'gateway/run_inbound.py'
SOURCE_BLOB = '4a7e166c980264f38edbf836efa0d36a1961b93b'
TEST = 'tests/gateway/test_model_confirmation_replacement.py'
EXISTING = 'tests/gateway/test_model_multiline_payload.py'
ANCHOR = '''        _model_event, _inline_payload = self._split_inline_command_payload(event)
        _response = await self._handle_model_command(_model_event)
'''
REPLACEMENT = '''        _model_event, _inline_payload = self._split_inline_command_payload(event)
        # Every new /model request supersedes any older inline request, even
        # when this request has no payload and needs another confirmation.
        self._model_inline_payload_stash().pop(_quick_key, None)
        _response = await self._handle_model_command(_model_event)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(upstream: Path, out: Path):
    upstream = upstream.resolve()
    rev = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=upstream, text=True).strip()
    if rev != REV or subprocess.check_output(['git', 'status', '--porcelain'], cwd=upstream):
        raise ValueError('A clean checkout of the exact inspected PR head is required')
    raw = (upstream / SOURCE).read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob != SOURCE_BLOB or raw.decode().count(ANCHOR) != 1 or (upstream / TEST).exists():
        raise ValueError('Inspected source or regression target changed')
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve()
    (out / 'home').mkdir()
    shutil.copyfile(Path(__file__).with_name(Path(TEST).name), upstream / TEST)
    env = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT', 'TMPDIR', 'TEMP', 'TMP') if k in os.environ}
    env.update(HOME=str(out/'home'), HERMES_HOME=str(out/'home/hermes'),
               PYTHONPATH=str(upstream), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', TZ='UTC', LANG='C.UTF-8')
    def tests(label, file):
        xml = out/(label+'.xml')
        this_env = dict(env, MODEL_CONFIRM_OBSERVATIONS=str(out/(label+'.jsonl')))
        result = subprocess.run([sys.executable,'-m','pytest','-p','pytest_asyncio.plugin',
            '-o','addopts=','-q',file,'--junitxml='+str(xml)], cwd=upstream, env=this_env,
            capture_output=True, text=True, timeout=90)
        (out/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        if not xml.exists():
            raise RuntimeError(label+': no XML report; inspect saved output')
        cases = ET.parse(xml).getroot().findall('.//testcase')
        data = dict(exit_code=result.returncode, tests=len(cases),
            failures=sum(c.find('failure') is not None for c in cases),
            errors=sum(c.find('error') is not None for c in cases),
            skipped=sum(c.find('skipped') is not None for c in cases))
        (out/(label+'.json')).write_text(json.dumps(data, indent=2)+'\n')
        print(label, json.dumps(data), flush=True)
        return data
    before = tests('before', TEST)
    if before != dict(exit_code=1, tests=2, failures=2, errors=0, skipped=0):
        raise RuntimeError('Expected two routing assertions, not setup failures; inspect before.txt')
    modified = raw.decode().replace(ANCHOR, REPLACEMENT)
    compile(modified, SOURCE, 'exec')
    (upstream/SOURCE).write_text(modified, encoding='utf-8')
    patch = subprocess.check_output(['git','diff','--',SOURCE], cwd=upstream)
    (out/'candidate.patch').write_bytes(patch)
    after = tests('after', TEST)
    existing = tests('existing', EXISTING)
    if after != dict(exit_code=0, tests=2, failures=0, errors=0, skipped=0):
        raise RuntimeError('Candidate failed the new regressions')
    if existing['exit_code'] or existing['errors'] or existing['failures'] or existing['skipped'] or existing['tests'] != 9:
        raise RuntimeError('The nine existing PR cases did not all pass')
    observations = {}
    for label in ('before','after'):
        rows = [json.loads(line) for line in (out/(label+'.jsonl')).read_text().splitlines()]
        if len(rows) != 2:
            raise RuntimeError('Missing observations')
        for row in rows:
            if Path(row['imports']['inbound']).resolve() != upstream/SOURCE:
                raise RuntimeError('A different module was loaded')
        observations[label] = rows
    summary = dict(status='reproduced_and_candidate_checked', pr=22982, pr_head=REV,
        source_blob=SOURCE_BLOB, before=before, after=after, existing=existing,
        patch_sha256=sha(patch), test_sha256=sha((upstream/TEST).read_bytes()),
        changed_source=SOURCE, observations=observations,
        scope='Real PR gateway dispatch and slash-confirm routing with upstream fixture doubles for model resolution, warning policy, adapters, storage facade and agent boundary. Controlled clock. No real model, message delivery or user deployment.',
        limits='Sequential pending-confirm replacement only; no concurrent callback proof, restart persistence, full gateway deployment or upstream acceptance.')
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    verify(args.upstream, args.out)
