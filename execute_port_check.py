"""Build the narrowly resolved candidate and run fixed-source fixture tests.

Run only inside a disposable environment. Downloads public code and uses its
canonical test runner. No accounts, actual model calls or upstream writes.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

from prepare_port import MAIN, HEAD, FILES, prepare


def emit(kind, **fields):
    print('BINDING_PORT_CHECK '+json.dumps(dict(kind=kind, **fields),ensure_ascii=True),flush=True)


def run(args,cwd,timeout=180):
    completed=subprocess.run(args,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    emit('command',argv=args,exit_code=completed.returncode,stdout=completed.stdout[-18000:],stderr=completed.stderr[-10000:])
    return completed


def counts(xml):
    if not xml.exists(): return None
    tree=ET.parse(xml).getroot()
    suites=[tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
    return {key:sum(int(x.attrib.get(key,0)) for x in suites) for key in ['tests','failures','errors','skipped']}


def check_file(repo,filename,label):
    xml=repo.parent/(label+'.xml')
    result=run(['bash','scripts/run_tests.sh',filename,'-j','1','--file-timeout','65','--file-retries','0','--','-q','--tb=short','--junitxml='+str(xml)],repo,timeout=100)
    record={'label':label,'file':filename,'exit_code':result.returncode,'junit':counts(xml)}
    emit('test_result',**record)
    return record


def main():
    cwd=Path.cwd(); generated=cwd/'generated'; manifest=prepare(generated)
    emit('prepared',manifest=manifest)
    url='https://codeload.github.com/NousResearch/hermes-agent/tar.gz/'+MAIN
    with urllib.request.urlopen(url,timeout=75) as response:
        archive=response.read(200_000_001)
    if len(archive)>200_000_000: raise RuntimeError('Archive size limit exceeded')
    emit('source_archive',url=url,bytes=len(archive),sha256=hashlib.sha256(archive).hexdigest())
    destination=cwd/'source_checkout'; destination.mkdir(exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
        tar.extractall(destination,filter='data')
    roots=list(destination.iterdir())
    if len(roots)!=1: raise RuntimeError('Unexpected archive root')
    repo=roots[0]
    for entry in manifest['files']:
        p=repo/entry['path']
        if entry['main'] is not None and hashlib.sha256(p.read_bytes()).hexdigest()!=entry['main']:
            raise RuntimeError('Archive identity mismatch: '+entry['path'])
    uv=shutil.which('uv')
    if not uv: raise RuntimeError('No preinstalled uv; do not install an unplanned resolver')
    run([uv,'--version'],repo,30)
    env=run([uv,'sync','--frozen','--extra','dev','--python','3.12'],repo,240)
    if env.returncode: raise RuntimeError('Pinned dependency setup failed')
    run([uv,'pip','freeze','--python',str(repo/'.venv/bin/python')],repo,30)
    # A small local Git index lets the canonical runner find the relevant bytecode files.
    # It has no remotes or credentials and is not pushed anywhere.
    run(['git','init','-q'],repo,30)
    run(['git','add','gateway/run.py','gateway/run_inbound.py','gateway/slash_commands_model.py'],repo,30)
    results=[]
    results.append(check_file(repo,'tests/gateway/test_model_command_reasoning_flag.py','baseline_reasoning'))
    if results[-1]['exit_code']: raise RuntimeError('Baseline test environment is not established')
    for path in FILES:
        p=repo/path; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((generated/'candidate'/path).read_bytes())
    new_test=repo/'tests/gateway/test_model_binding_reasoning_port.py'
    new_test.write_bytes((cwd/'test_model_binding_reasoning_port.py').read_bytes())
    target_files=['tests/gateway/test_model_command_reasoning_flag.py',
                  'tests/gateway/test_model_multiline_payload.py',
                  'tests/gateway/test_model_confirmation_binding.py',
                  'tests/gateway/test_model_binding_reasoning_port.py']
    for i,path in enumerate(target_files):
        results.append(check_file(repo,path,'candidate_'+str(i)))
    candidate_passes=all(x['exit_code']==0 for x in results[1:])
    model_file=repo/'gateway/slash_commands_model.py'; good=model_file.read_bytes()
    # If the candidate works, verify that either one-sided conflict resolution loses a property.
    mutation_results=[]
    if candidate_passes:
        text=good.decode('utf-8')
        marker='        return ModelSwitchConfirmation(reply)\n'
        if text.count(marker)!=1: raise RuntimeError('Mutant target is not unique')
        main_only=text.replace(marker,'        return reply\n')
        begin=text.index('        reply = await self._model_switch_confirmation',text.index('    async def _commit_model_switch'))
        end=text.index(marker,begin)+len(marker)
        head_only=text[:begin]+'        return ModelSwitchConfirmation(\n            await self._model_switch_confirmation(result, ctx, one_turn=one_turn, picker=picker)\n        )\n'+text[end:]
        try:
            for label,mutant in [('main_side_only',main_only),('contribution_side_only',head_only)]:
                model_file.write_text(mutant)
                mutation_results.append(check_file(repo,'tests/gateway/test_model_binding_reasoning_port.py',label))
        finally:
            model_file.write_bytes(good)
    final={
      'main':MAIN,'head':HEAD,'candidate_tests_passed':candidate_passes,
      'tests':results,'one_sided_resolution_controls':mutation_results,
      'candidate_restored':hashlib.sha256(model_file.read_bytes()).hexdigest()==hashlib.sha256(good).hexdigest(),
      'patch_sha256':manifest['patch_sha256'],
      'old_tests_preserved':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest()==next(x['head'] for x in manifest['files'] if x['path']==p) for p in FILES if p.startswith('tests/')},
      'upstream_writes':0,'live_model_calls':0,
      'scope':'Selected actual-source fixture tests, not the full suite or live-provider/platform validation.'}
    (cwd/'PORT_RESULTS.json').write_text(json.dumps(final,indent=2)+'\n')
    emit('final',**final)
    if not candidate_passes: raise SystemExit(2)


if __name__=='__main__': main()
