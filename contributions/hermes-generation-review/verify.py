"""Compare exact parent/head trees with the same supplemental lifecycle checks."""
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

PARENT = '2b1c0ae586e7bf4c51cc0cbe61eff4ec0190be03'
HEAD = 'b2f009d4f289597a5eace6b9c7a169901c3a5af8'
TEST = 'tests/gateway/test_displaced_generation_review.py'
EXISTING = 'tests/gateway/test_reaped_eviction_interrupts_run.py'


def main(parent: Path, head: Path, out: Path):
    trees = {'parent': parent.resolve(), 'head': head.resolve()}
    raw = Path(__file__).with_name(Path(TEST).name).read_bytes()
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve()
    manifests = {}
    for label, expected in (('parent', PARENT), ('head', HEAD)):
        tree = trees[label]
        rev = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip()
        dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=tree)
        if rev != expected or dirty or (tree/TEST).exists():
            raise ValueError(label + ': need clean exact checkout and a new test path')
        manifests[label] = {'revision': rev, 'files': {}}
        for name in ('gateway/run_agent_cache.py', 'gateway/run_inbound.py', 'gateway/session_state.py', 'gateway/turn_lease.py', EXISTING):
            data = (tree/name).read_bytes()
            manifests[label]['files'][name] = {
                'git_blob': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
                'sha256': hashlib.sha256(data).hexdigest()}
        (tree/TEST).write_bytes(raw)
    results = {}
    for label, tree, files in (
        ('parent_supplemental', trees['parent'], [TEST]),
        ('head_supplemental', trees['head'], [TEST]),
        ('head_author_tests', trees['head'], [EXISTING]),
    ):
        home = out/(label+'_home'); home.mkdir()
        env = {k: os.environ[k] for k in ('PATH','SYSTEMROOT','TMPDIR','TMP','TEMP') if k in os.environ}
        env.update(HOME=str(home), HERMES_HOME=str(home/'hermes'), PYTHONPATH=str(tree),
                   PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                   PYTHONHASHSEED='0', TZ='UTC', LANG='C.UTF-8',
                   LIFECYCLE_REVIEW_OBSERVATIONS=str(out/(label+'.jsonl')))
        xml = out/(label+'.xml')
        completed = subprocess.run([sys.executable, '-m', 'pytest', '-p', 'pytest_asyncio.plugin',
            '-o','addopts=', '-q', *files, '--junitxml='+str(xml)], cwd=tree, env=env,
            capture_output=True, text=True, timeout=90)
        (out/(label+'.txt')).write_text(completed.stdout+'\n'+completed.stderr, encoding='utf-8')
        if not xml.exists():
            raise RuntimeError(label+': no assertion report; see saved output')
        cases = ET.parse(xml).getroot().findall('.//testcase')
        results[label] = dict(exit_code=completed.returncode, tests=len(cases),
            failures=sum(c.find('failure') is not None for c in cases),
            errors=sum(c.find('error') is not None for c in cases),
            skipped=sum(c.find('skipped') is not None for c in cases))
        print(label, results[label], flush=True)
    report = {'schema':'displaced-generation-review-v1', 'source':manifests,
              'test_sha256':hashlib.sha256(raw).hexdigest(), 'results':results,
              'scope':'Real imported gateway state/restore/lease helpers, controlled in-memory state and real asyncio locks. Cache eviction and active-state persistence use recording functions. No actual agent, provider, gateway server, platform send, user DB or operating-system process cancellation.',
              'new_implementation_by_reviewer':False,
              'credit':'Production repair is the PR authors work. This is an additional AI-assisted check with Zero (ChatGPT).',
              'full_outer_finalizer_executed':False}
    (out/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Final constraints describe the expected behavior comparison, not merely green CI.
    assert results['parent_supplemental'] == dict(exit_code=1, tests=4, failures=4, errors=0, skipped=0), results
    assert results['head_supplemental'] == dict(exit_code=0, tests=4, failures=0, errors=0, skipped=0), results
    assert results['head_author_tests'] == dict(exit_code=0, tests=10, failures=0, errors=0, skipped=0), results
    for label in ('parent_supplemental','head_supplemental'):
        rows = [json.loads(line) for line in (out/(label+'.jsonl')).read_text().splitlines()]
        assert len(rows) == 4, rows
        tree = trees[label.split('_')[0]]
        for row in rows:
            assert Path(row['source_modules']['cache']).resolve() == tree/'gateway/run_agent_cache.py'
    # No upstream implementation or original test is changed by this verifier.
    for label, tree in trees.items():
        assert subprocess.check_output(['git','diff','--name-only'],cwd=tree) == b''
    report['verified'] = True
    (out/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent', type=Path, required=True)
    p.add_argument('--head', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a=p.parse_args(); main(a.parent,a.head,a.out)
