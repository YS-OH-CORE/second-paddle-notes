"""Run identical integration tests on two pinned, unmodified public source trees."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = 'b2f009d4f289597a5eace6b9c7a169901c3a5af8'
HEAD = 'c9122c0cc9544653611d1e2c5151f77bb41a743d'
ORIGINALS = ('tests/gateway/test_reaped_eviction_interrupts_run.py',
             'tests/gateway/test_reaped_session_recovery.py')
MODULES = ('gateway/run.py', 'gateway/run_inbound.py', 'gateway/run_agent_cache.py',
           'gateway/run_turn.py', 'gateway/turn_lease.py', 'gateway/session.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def counts(path):
    cases = list(ET.parse(path).getroot().iter('testcase'))
    failed = [c for c in cases if c.find('failure') is not None]
    errors = [c for c in cases if c.find('error') is not None]
    skipped = [c for c in cases if c.find('skipped') is not None]
    return dict(tests=len(cases), failures=len(failed), errors=len(errors), skipped=len(skipped),
                passed=len(cases)-len(failed)-len(errors)-len(skipped),
                failure_names=[c.attrib['name'] for c in failed])


def verify(base, head, out):
    base, head, out = base.resolve(), head.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    test = Path(__file__).with_name('test_salvage_inbound_integration.py')
    identities = {}
    for label, root, commit in [('base', base, BASE), ('head', head, HEAD)]:
        if git(root, 'rev-parse', 'HEAD') != commit or git(root, 'status', '--porcelain', '--untracked-files=no'):
            raise ValueError('Source checkout is not the pinned unmodified commit')
        identities[label] = {p: digest(root/p) for p in (*MODULES, *ORIGINALS)}
        destination = root/'tests/gateway/test_zero_salvage_inbound_integration.py'
        with destination.open('xb') as handle:
            handle.write(test.read_bytes())
    results = {}
    for label, root, tests in [('base', base, ['tests/gateway/test_zero_salvage_inbound_integration.py']),
                              ('head', head, ['tests/gateway/test_zero_salvage_inbound_integration.py']),
                              ('head_original', head, list(ORIGINALS))]:
        home = out/(label+'-home'); home.mkdir()
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TERM', 'TMPDIR')}
        env.update(HOME=str(home), HERMES_HOME=str(home/'hermes'), PYTHONPATH=str(root),
                   PYTHONIOENCODING='utf-8', ZERO_OBSERVATIONS=str(out/(label+'.jsonl')))
        xml = out/(label+'.xml')
        cmd = [sys.executable, '-m', 'pytest', '-q', '-o', 'addopts=', '--tb=short',
               '--basetemp', str(out/(label+'-temp')), '--junitxml', str(xml), *tests]
        result = subprocess.run(cmd, cwd=root, env=env, text=True, capture_output=True, timeout=90)
        (out/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        results[label] = dict(returncode=result.returncode, **counts(xml))
    summary = dict(status='observed_not_yet_accepted', source_commits={'base': BASE, 'head': HEAD},
                   test_sha256=digest(test), source_hashes=identities, results=results,
                   scope='Selected real outer-inbound+session-database+lease integration, controlled agent/admission/delivery/capacity fixtures; not a live gateway.')
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    for label, root in [('base', base), ('head', head)]:
        if git(root, 'status', '--porcelain', '--untracked-files=no'):
            raise AssertionError('Tracked upstream content changed during tests')
        if identities[label] != {p: digest(root/p) for p in (*MODULES, *ORIGINALS)}:
            raise AssertionError('Source/original test identity changed')
    b, h, original = (results[k] for k in ('base','head','head_original'))
    if not (b['tests']==8 and b['failures']>0 and b['errors']==b['skipped']==0):
        raise AssertionError('Baseline did not demonstrate clean behavioral failures; inspect raw reports')
    if not (h['tests']==h['passed']==8 and h['returncode']==0):
        raise AssertionError('Consolidated head did not pass all eight integration cases')
    if not (original['passed']==original['tests']==12 and original['returncode']==0):
        raise AssertionError('Original adjacent tests did not all pass')
    summary.update(status='verified', tracked_upstream_unchanged=True)
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',required=True,type=Path)
    parser.add_argument('--head',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(); verify(args.base,args.head,args.out)
