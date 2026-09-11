#!/usr/bin/env python3
"""Anonymous public upgrade from a1 to a2 in a fresh disposable environment.

Faults affect only receipt fsync in the installed-module CLI process. Actual child
markers/exit codes are real. No physical disk fault or user installation is used.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import venv
from publish import REPO, TAG, SOURCE, WHEEL, WHEEL_SHA, MODULES, NAMES, sha, require, dump, wheel_modules

OLD_WHEEL = 'second_paddle_process_receipt-0.2.0a1-py3-none-any.whl'
OLD_SHA = '13b47b0416b519e42596fd0ea7a0c2c929edbdd17488ae53adfa7031745c7032'
TEXT = '실행 결과와 기록 실패는 다르다.\n  공백 보존  \n'
DRIVER = r'''
import json,os,runpy,sys
from pathlib import Path
receipt,marker,trace,worker,exit_code=sys.argv[1:]
real=os.fsync
calls=0
fired=False
def fault(fd):
 global calls,fired
 calls+=1
 if calls==3:
  fired=True
  raise OSError('INJECTED_RECEIPT_FAULT_DETAIL_NOT_FOR_OUTPUT')
 return real(fd)
os.fsync=fault
code='from pathlib import Path; Path('+repr(marker)+').write_bytes(b"child actually ran\\n"); raise SystemExit('+exit_code+')'
sys.argv=['process-receipt','--receipt',receipt,'--timeout','10','--',worker,'-I','-c',code]
try:
 runpy.run_module('process_receipt_cli',run_name='__main__')
finally:
 os.fsync=real
 Path(trace).write_text(json.dumps({'fsync_calls':calls,'injected':fired}),encoding='utf-8')
'''


def public_get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'process-receipt-corrective-upgrade/0.2',
        'Accept':'application/octet-stream' if '/download/' in url else 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        require(response.status == 200 and response.url.startswith('https://'), 'Unexpected public response')
        raw = response.read(1_000_001)
    require(len(raw) <= 1_000_000, 'Public response too large')
    return raw


def consume(out, local_old=None, local_new=None):
    out = out.resolve(); out.mkdir(parents=True, exist_ok=False)
    offline = local_old is not None and local_new is not None
    base = f'https://github.com/{REPO}/releases/download/{TAG}/'
    if offline:
        old, new = local_old.read_bytes(), local_new.read_bytes()
        release_id = None
    else:
        release = json.loads(public_get(f'https://api.github.com/repos/{REPO}/releases/tags/{TAG}'))
        require(not release['draft'] and release['prerelease'] and release['target_commitish'] == SOURCE, 'Wrong release')
        require(len(release['assets']) == 3 and {a['name'] for a in release['assets']} == NAMES, 'Wrong release assets')
        release_id = release['id']
        new = public_get(base+WHEEL)
        old = public_get(f'https://github.com/{REPO}/releases/download/process-receipt-v0.2.0a1/{OLD_WHEEL}')
        provenance = public_get(base+'BUILD_PROVENANCE.json')
        p = json.loads(provenance)
        require(p['source_commit'] == SOURCE and p['wheel_sha256'] == WHEEL_SHA, 'Wrong provenance')
        sums = ''.join(f'{sha(raw)}  {name}\n' for name,raw in ((WHEEL,new),('BUILD_PROVENANCE.json',provenance)))
        require(public_get(base+'SHA256SUMS').decode() == sums, 'Wrong checksums')
    require(sha(old) == OLD_SHA, 'Wrong old wheel')
    modules = wheel_modules(new)
    for name, raw in ((OLD_WHEEL,old),(WHEEL,new)):
        (out/name).write_bytes(raw)
    work = out/'outside-source'; work.mkdir()
    home = out/'home'; home.mkdir()
    allowed = ('PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','TMPDIR','PATHEXT','LANG')
    env = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(HOME=str(home),USERPROFILE=str(home),PYTHONIOENCODING='utf-8',PYTHONUTF8='1',
               PIP_CONFIG_FILE=os.devnull,PIP_NO_INPUT='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
    environment = out/'consumer'
    venv.EnvBuilder(with_pip=True,system_site_packages=False).create(environment)
    bins = environment/('Scripts' if os.name=='nt' else 'bin')
    py = bins/('python.exe' if os.name=='nt' else 'python')
    cli = bins/('process-receipt.exe' if os.name=='nt' else 'process-receipt')
    commands=[]
    def run(args, expected=0):
        r = subprocess.run([str(a) for a in args],cwd=work,env=env,capture_output=True,timeout=40)
        commands.append(dict(exit_code=r.returncode,stdout=r.stdout.decode('utf-8','replace'),stderr=r.stderr.decode('utf-8','replace')))
        dump(out/'commands.json',commands)
        require(r.returncode==expected,'Installed operation failed; see commands.json')
        return r
    def install(name):
        run([py,'-I','-m','pip','--isolated','install','--no-index','--no-deps','--no-cache-dir',out/name])
    def identity():
        return json.loads(run([py,'-I','-c','import importlib,importlib.metadata as m,json,sys; print(json.dumps({"version":m.version("second-paddle-process-receipt"),"python":sys.version,"worker":sys._base_executable,"modules":{n:importlib.import_module(n[:-3]).__file__ for n in '+repr(list(MODULES))+'}}))']).stdout)
    def fault_case(label,worker,code,fixed):
        receipt,marker,trace=[work/(label+s) for s in ('.receipt.json','.marker','.trace.json')]
        r=run([py,'-I','-c',DRIVER,receipt,marker,trace,worker,str(code)],2)
        injection=json.loads(trace.read_bytes())
        require(injection==dict(fsync_calls=3,injected=True) and marker.read_bytes()==b'child actually ran\n','Missing actual execution/fault evidence')
        stderr=r.stderr.decode('utf-8')
        require('INJECTED_RECEIPT_FAULT_DETAIL_NOT_FOR_OUTPUT' not in stderr,'Raw fault detail leaked')
        summary=json.loads(stderr) if fixed else None
        if fixed:
            require(summary['status']=='receipt_persistence_failed' and summary['receipt_finalization_confirmed'] is False,'Missing distinct receipt failure')
            require(summary['execution']==dict(status='completed' if code==0 else 'failed',task_started=True,
                direct_child_exit_observed=True,child_exit_code=code,stop_reason=None),'Observed execution was lost')
        else:
            require('OSError' in stderr and not stderr.lstrip().startswith('{'),'Unexpected a1 behavior')
        row=dict(case=label,child_marker=marker.read_text(),injection=injection,stderr=stderr,
                 summary=summary,cli_exit_code=r.returncode,child_requested_exit=code)
        dump(out/(label+'.json'),row)
        return row
    install(OLD_WHEEL)
    old_info=identity();require(old_info['version']=='0.2.0a1','Wrong baseline installed version')
    before=fault_case('before-a1',old_info['worker'],0,False)
    install(WHEEL)
    info=identity();require(info['version']=='0.2.0a2','Upgrade not installed')
    for name,path in info['modules'].items():
        path=Path(path).resolve()
        require(path.is_relative_to(environment) and path.read_bytes()==modules[name],'Not the exact upgraded installation')
    after0=fault_case('after-a2-zero',info['worker'],0,True)
    after7=fault_case('after-a2-seven',info['worker'],7,True)
    output=work/'한글 result.txt';receipt=work/'normal.json'
    code='from pathlib import Path; Path('+repr(str(output))+').write_bytes('+repr(TEXT.encode())+')'
    run([cli,'--receipt',receipt,'--timeout','10','--',info['worker'],'-I','-c',code])
    r=json.loads(receipt.read_bytes())
    require(output.read_bytes()==TEXT.encode() and r['status']=='completed','Ordinary installed console command failed')
    dump(out/'verification.json',dict(status='offline_upgrade_verified' if offline else 'anonymous_public_upgrade_verified',
        observed_at=datetime.now(timezone.utc).isoformat(),platform=sys.platform,release_id=release_id,
        old_sha256=sha(old),wheel_sha256=sha(new),wheel_bytes=len(new),used_authorization_header=False,
        installed_before=old_info,installed_after=info,observations=[before,after0,after7],
        ordinary_console_command_verified=True,upgraded_modules_match=True,
        scope='Same disposable venv upgraded from exact a1 to a2. Installed module CLI with receipt-only injected fsync fault and real base-Python child; normal console executable separately tested. No real storage fault, user-PC change, automatic retry, model call or third-party adoption.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--local-old',type=Path)
    p.add_argument('--local-new',type=Path)
    a=p.parse_args()
    if (a.local_old is None)!=(a.local_new is None):p.error('Both local wheels are required for offline mode')
    consume(a.out,a.local_old,a.local_new)
