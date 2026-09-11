"""Verify a request-owned confirmation patch in a disposable exact-PR checkout."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from build_binding_patch import BLOBS, patch_sources

REV = 'addb69bc409dae7d1c0ae9f2dc571fd4a39d8fc8'
BASE = 'tests/gateway/test_model_multiline_payload.py'
ADDED = [
    'tests/gateway/test_model_confirmation_replacement.py',
    'tests/gateway/test_model_confirmation_binding.py',
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(root: Path, out: Path):
    root = root.resolve()
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() != REV:
        raise ValueError('Wrong source revision')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root):
        raise ValueError('Use a clean disposable checkout')
    for path, blob in BLOBS.items():
        data = (root/path).read_bytes()
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != blob:
            raise ValueError('Wrong original source blob')
    base_bytes = (root/BASE).read_bytes()
    here = Path(__file__).resolve().parent
    if any((root/path).exists() for path in ADDED):
        raise ValueError('Regression file already exists')
    out.mkdir(parents=True, exist_ok=False)
    out = out.resolve()
    (out/'home').mkdir()
    env = {k: os.environ[k] for k in ('PATH','SYSTEMROOT','TMPDIR','TEMP','TMP') if k in os.environ}
    env.update(HOME=str(out/'home'), HERMES_HOME=str(out/'home/hermes'), PYTHONPATH=str(root),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
        TZ='UTC', LANG='C.UTF-8')

    def tests(label, paths):
        xml = out/(label+'.xml')
        local_env = dict(env, MODEL_BINDING_OBSERVATIONS=str(out/(label+'-binding.jsonl')),
                        MODEL_CONFIRM_OBSERVATIONS=str(out/(label+'-replacement.jsonl')))
        command = [sys.executable, '-m', 'pytest', '-p', 'pytest_asyncio.plugin',
                   '-o', 'addopts=', '-q', *paths, '--junitxml='+str(xml)]
        result = subprocess.run(command, cwd=root, env=local_env, capture_output=True, text=True, timeout=75)
        (out/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
        if not xml.exists():
            raise RuntimeError(label+': XML missing')
        nodes = ET.parse(xml).getroot().findall('.//testcase')
        rec = dict(exit_code=result.returncode, tests=len(nodes),
            failures=sum(n.find('failure') is not None for n in nodes),
            errors=sum(n.find('error') is not None for n in nodes),
            skipped=sum(n.find('skipped') is not None for n in nodes),
            failed_cases=[n.attrib['name'] for n in nodes if n.find('failure') is not None])
        (out/(label+'.json')).write_text(json.dumps(rec, indent=2)+'\n', encoding='utf-8')
        print(label, json.dumps(rec), flush=True)
        return rec

    def passed(result, count=None):
        return not any(result[k] for k in ('exit_code','failures','errors','skipped')) and (
            result['tests'] == count if count is not None else result['tests'] > 0)

    baseline = tests('baseline_existing', [BASE])
    if not passed(baseline, 9):
        raise RuntimeError('The unchanged PR baseline is not green')
    for path in ADDED:
        shutil.copyfile(here/Path(path).name, root/path)
    before = tests('before', ADDED)
    if before['exit_code'] != 1 or before['tests'] != 12 or before['errors'] or before['skipped'] or before['failures'] < 2:
        raise RuntimeError('Baseline did not reach the expected assertion boundary')
    patch = patch_sources(root)
    (out/'production_binding.patch').write_text(patch, encoding='utf-8')
    after = tests('after', ADDED)
    existing = tests('after_existing', [BASE])
    registry = tests('after_registry', ['tests/tools/test_slash_confirm.py'])
    if not passed(after,12) or not passed(existing,9) or not passed(registry):
        raise RuntimeError('The request-bound implementation failed a regression')
    if (root/BASE).read_bytes() != base_bytes:
        raise RuntimeError('Original tests were modified')
    changed = subprocess.check_output(['git','diff','--name-only'],cwd=root,text=True).splitlines()
    if sorted(changed) != sorted(BLOBS):
        raise RuntimeError('Unexpected production changes')
    combined = patch
    for path in ADDED:
        text = (root/path).read_text(encoding='utf-8')
        combined += ''.join(difflib.unified_diff([],text.splitlines(True),fromfile='/dev/null',tofile='b/'+path))
    patch_path = out/'confirmation_binding.patch'
    patch_path.write_text(combined, encoding='utf-8')
    subprocess.run(['git','apply','--check','--reverse',str(patch_path)],cwd=root,check=True)
    observations = {}
    for label in ('before','after'):
        observations[label] = {}
        for family in ('binding','replacement'):
            file = out/(label+'-'+family+'.jsonl')
            rows = [json.loads(line) for line in file.read_text(encoding='utf-8').splitlines()]
            expected_count = 10 if family == 'binding' else 2
            if len(rows) != expected_count:
                raise RuntimeError('Missing per-case observations: '+str(file))
            observations[label][family] = rows
    info = subprocess.check_output([sys.executable,'-c',
        'import json,gateway.run_inbound as i,gateway.slash_commands_model as m,tools.slash_confirm as c; '
        'print(json.dumps({"inbound":i.__file__,"model":m.__file__,"registry":c.__file__}))'],
        cwd=root,env=env,text=True,timeout=25)
    imports = json.loads(info)
    for key, path in (('inbound','gateway/run_inbound.py'),('model','gateway/slash_commands_model.py'),('registry','tools/slash_confirm.py')):
        if Path(imports[key]).resolve() != root/path:
            raise RuntimeError('Wrong imported module')
    summary = dict(status='request_bound_patch_verified', source_revision=REV, source_blobs=BLOBS,
        baseline_existing=baseline, before=before, after=after, after_existing=existing, after_registry=registry,
        original_test_file_unchanged=True, original_tests_sha256=digest(base_bytes),
        patch_sha256=digest(patch_path.read_bytes()), production_patch_sha256=digest(patch.encode()),
        tests={path:digest((root/path).read_bytes()) for path in ADDED},
        modules={path:digest((root/path).read_bytes()) for path in BLOBS},
        imports=imports, observations=observations, models_called=0, platform_messages_sent=0,
        scope='Actual PR model handlers, gateway dispatch and slash-confirm registry. Existing fixture doubles for provider/model resolution, warning policy, delivery, storage facade and final agent. Controlled asyncio presentation schedules and clock; retained-callback cases explicitly call the callback to isolate ownership.',
        limits='Not a full gateway deployment, arbitrary cross-thread schedule, process-restart approval persistence, native-button automatic routing, model compliance, maintainer acceptance or independent review. Expired registry entries cannot resolve; a last inert token can remain until replacement or conversation cleanup.')
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    verify(args.upstream,args.out)
