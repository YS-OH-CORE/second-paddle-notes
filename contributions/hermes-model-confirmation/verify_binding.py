"""Compare the real PR modules before/after a confirmation-owned payload patch."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from build_binding_patch import apply

REV = 'addb69bc409dae7d1c0ae9f2dc571fd4a39d8fc8'
TEST = 'tests/gateway/test_model_confirmation_binding.py'
EXISTING = 'tests/gateway/test_model_multiline_payload.py'
SOURCES = {'gateway/run_inbound.py':'4a7e166c980264f38edbf836efa0d36a1961b93b',
    'gateway/slash_commands_model.py':'87e0668849bddada5c5c601bed23bf9387f77a21',
    'tools/slash_confirm.py':'f3f3e78e1775bafb55bc8128667530190cd09b9a'}

def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root, out):
    root = root.resolve()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip() != REV:
        raise ValueError('Wrong PR revision')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root):
        raise ValueError('Disposable checkout must be clean')
    for name, expected in SOURCES.items():
        raw = (root/name).read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != expected:
            raise ValueError('Unexpected source: '+name)
    out.mkdir(parents=True,exist_ok=False); out = out.resolve()
    (out/'home').mkdir()
    origin = Path(__file__).parent
    test_data = (origin/Path(TEST).name).read_bytes()
    if (root/TEST).exists(): raise ValueError('Test path already exists')
    (root/TEST).write_bytes(test_data)
    env = {k:os.environ[k] for k in ('PATH','SYSTEMROOT','TMPDIR','TEMP','TMP') if k in os.environ}
    env.update(HOME=str(out/'home'),HERMES_HOME=str(out/'home/hermes'),PYTHONPATH=str(root),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',TZ='UTC',LANG='C.UTF-8')
    def run(label, path):
        report=out/(label+'.xml')
        e=dict(env,MODEL_BINDING_OBSERVATIONS=str(out/(label+'.jsonl')))
        result=subprocess.run([sys.executable,'-m','pytest','-p','pytest_asyncio.plugin',
            '-o','addopts=','-q',path,'--junitxml='+str(report)],cwd=root,env=e,capture_output=True,text=True,timeout=90)
        (out/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if not report.exists():raise RuntimeError('Missing report: '+label)
        cases=ET.parse(report).getroot().findall('.//testcase')
        data=dict(exit_code=result.returncode,tests=len(cases),
            failures=sum(c.find('failure') is not None for c in cases),
            errors=sum(c.find('error') is not None for c in cases),
            skipped=sum(c.find('skipped') is not None for c in cases),
            failed_cases=[c.get('name') for c in cases if c.find('failure') is not None])
        (out/(label+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        print(label,json.dumps(data),flush=True)
        return data
    def passed(result, count=None):
        return result['exit_code']==0 and result['failures']==result['errors']==result['skipped']==0 and (count is None or result['tests']==count)
    existing_before=run('existing_before',EXISTING)
    if not passed(existing_before,9):raise RuntimeError('Original existing tests failed')
    before=run('before',TEST)
    if before['exit_code']!=1 or before['tests']!=14 or before['failures']<2 or before['errors'] or before['skipped']:
        raise RuntimeError('Baseline must fail real assertions, not collection/setup')
    # Only this newly copied scratch test is removed, so the builder can reserve it.
    (root/TEST).unlink()
    patch=apply(root,origin/Path(TEST).name)
    (out/'confirmation_binding.patch').write_bytes(patch)
    after=run('after',TEST)
    existing_after=run('existing_after',EXISTING)
    primitive=run('confirmation_primitive','tests/tools/test_slash_confirm.py')
    if not passed(after,14) or not passed(existing_after,9) or not passed(primitive):
        raise RuntimeError('Patched regression gate failed; inspect exact reports')
    # Conditional removal must not consume a newer registered approval.
    probe='''import asyncio,json
from tools import slash_confirm as s
async def callback(choice): return "NEW"
s.register("binding-probe","new","model",callback)
s.clear("binding-probe",confirm_id="old")
assert s.get_pending("binding-probe")["confirm_id"] == "new"
assert asyncio.run(s.resolve("binding-probe","new","once")) == "NEW"
print(json.dumps({"conditional_clear_preserved_new":True}))
'''
    result=subprocess.run([sys.executable,'-c',probe],cwd=root,env=env,capture_output=True,text=True,timeout=20,check=True)
    (out/'conditional_clear.json').write_text(result.stdout,encoding='utf-8')
    observations={}
    for label in ('before','after'):
        rows=[json.loads(line) for line in (out/(label+'.jsonl')).read_text(encoding='utf-8').splitlines()]
        if len(rows)!=14:raise RuntimeError('Missing actual observations: '+label)
        for row in rows:
            if Path(row['imports']['inbound']).resolve()!=root/'gateway/run_inbound.py':raise RuntimeError('Wrong import')
        observations[label]=rows
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=root,text=True).splitlines()
    expected=sorted(['gateway/run.py','gateway/run_inbound.py','gateway/slash_commands_model.py',
        'tools/slash_confirm.py',EXISTING])
    if sorted(changed)!=expected:raise RuntimeError('Unexpected tracked changes')
    summary=dict(status='binding_patch_verified',pr=22982,pr_head=REV,source_blobs=SOURCES,
        before=before,after=after,existing_before=existing_before,existing_after=existing_after,
        confirmation_primitive=primitive,patch_sha256=digest(patch),test_sha256=digest(test_data),
        patched_files={name:digest((root/name).read_bytes()) for name in changed},observations=observations,
        scope='Real PR routing and registry with the original PR fixture doubles for model resolution, guards, transport, storage facade and final agent. Controlled same-loop coroutine interleaving. No provider call, live platform, user installation, gateway server or persistent approval store.',
        limits='No claim of revoking already resolved/in-flight work, all cross-thread schedules, full product compatibility or upstream acceptance. Existing nine cases retain behavior assertions; shadow-stash assertions were replaced and reset checks now exercise the actual registry.')
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();verify(a.upstream,a.out)
