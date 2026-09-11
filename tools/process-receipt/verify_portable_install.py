"""Build-independent, native installed-command verification with inert workloads.

Run only in a disposable directory. No model/API calls, private data or taskkill.
Both normal output and stopped-work receipts are inspected outside the source tree.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import venv
import zipfile

VERSION = '0.2.0a2'
MODULES = ('process_receipt.py', 'process_receipt_cli.py', 'process_receipt_windows.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(wheel: Path, out: Path, repo: Path) -> dict:
    wheel, repo, out = wheel.resolve(strict=True), repo.resolve(strict=True), out.resolve()
    package = repo/'tools/process-receipt'
    sources = {n: (package/n).read_bytes() for n in MODULES}
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None
        assert sorted(n for n in z.namelist() if n.endswith('.py')) == sorted(MODULES)
        assert all(z.read(n) == b for n, b in sources.items())
    out.mkdir(parents=True, exist_ok=False)
    work = out/'outside-source'; work.mkdir()
    results = out/'results'; results.mkdir()
    home = out/'temporary-home'; home.mkdir()
    environment = out/'fresh-env'
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    bin_dir = environment/('Scripts' if os.name == 'nt' else 'bin')
    py = bin_dir/('python.exe' if os.name == 'nt' else 'python')
    cli = bin_dir/('process-receipt.exe' if os.name == 'nt' else 'process-receipt')
    allowed = ('PATH','SYSTEMROOT','WINDIR','SYSTEMDRIVE','COMSPEC','PATHEXT','TEMP','TMP','TMPDIR','LANG')
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    transcript, observations = [], []

    def execute(args, expected=0):
        result = subprocess.run([str(a) for a in args], cwd=work, env=env,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=35)
        transcript.append(dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        (results/'commands.json').write_text(json.dumps(transcript, indent=2), encoding='utf-8')
        assert result.returncode == expected, (result.returncode, expected, result.stderr)
        return result

    execute([py,'-I','-m','pip','--isolated','--disable-pip-version-check','install',
             '--no-index','--no-deps','--no-cache-dir',wheel])
    inspection = """import importlib,importlib.metadata as m,json,sys
names=('process_receipt','process_receipt_cli','process_receipt_windows')
print(json.dumps({'modules':{n:importlib.import_module(n).__file__ for n in names},
'version':m.version('second-paddle-process-receipt'),'requires':m.requires('second-paddle-process-receipt') or [],
'python':sys.version,'base_executable':sys._base_executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix}))
"""
    info = json.loads(execute([py,'-I','-c',inspection]).stdout)
    assert info['version'] == VERSION and not info['requires'] and info['prefix'] != info['base_prefix']
    for module, path in info['modules'].items():
        path = Path(path).resolve()
        assert path.is_relative_to(environment) and path.read_bytes() == sources[module+'.py']
    worker_python = Path(info['base_executable']).resolve(strict=True)
    execute([cli,'--help'])
    execute([py,'-I','-m','process_receipt_cli','--help'])

    def run_case(name, code, *, flags=(), expected=0, args=()):
        receipt_path = results/(name+'.receipt.json')
        execute([cli,'--receipt',receipt_path,*flags,'--',worker_python,'-I','-c',code,*args], expected)
        receipt = json.loads(receipt_path.read_bytes())
        assert receipt.get('finished_at')
        observations.append(dict(case=name, status=receipt['status'], task_started=receipt['task_started'],
                                  child_exit_code=receipt['child_exit_code']))
        return receipt

    payload = '새 작업의 결과\n  들여쓰기와 공백  \n'.encode('utf-8')
    target = results/'한글 경로 with spaces.txt'
    r = run_case('normal', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(bytes.fromhex(sys.argv[2]))',
                 args=(target, payload.hex()))
    assert r['status'] == 'completed' and r['child_exit_code'] == 0 and target.read_bytes() == payload
    if os.name == 'nt':
        assert r['backend'] == 'windows-direct-child' and r['signals_requested'] == []
    r = run_case('nonzero','raise SystemExit(7)',expected=2)
    assert r['status'] == 'failed' and r['child_exit_code'] == 7
    stop = results/'PRESTOP'; stop.write_text('retain this stop',encoding='utf-8')
    forbidden = results/'must-not-exist'
    mutation = 'from pathlib import Path; import sys; Path(sys.argv[1]).touch()'
    r = run_case('prestop', mutation, flags=('--stop-file',stop), args=(forbidden,), expected=2)
    assert r['status']=='not_started' and not r['task_started'] and not forbidden.exists()
    assert stop.read_text() == 'retain this stop'
    old_receipt = (results/'prestop.receipt.json').read_bytes()
    execute([cli,'--receipt',results/'prestop.receipt.json','--',worker_python,'-I','-c',mutation,forbidden],2)
    assert (results/'prestop.receipt.json').read_bytes() == old_receipt and not forbidden.exists()
    observations.append(dict(case='existing_receipt',preserved=True,task_started=False))
    r = run_case('deadline','import time; time.sleep(20)',flags=('--timeout','0.5','--grace','2'),expected=124)
    assert r['status']=='deadline_reached' and r['direct_child_exit_observed']

    running = results/'running'; running.mkdir()
    ready, heartbeat, complete = running/'READY', running/'heartbeat.txt', running/'NATURAL_COMPLETE'
    runtime_code = """from pathlib import Path
import sys,time
p=Path(sys.argv[1]); (p/'READY').touch(); start=time.monotonic()
with (p/'heartbeat.txt').open('w',encoding='utf-8') as f:
 while time.monotonic()-start<20:
  f.write('tick\\n');f.flush();time.sleep(0.05)
(p/'NATURAL_COMPLETE').touch()
"""
    receipt_path, stop_path = running/'receipt.json', running/'STOP'
    parent = subprocess.Popen([str(cli),'--receipt',str(receipt_path),'--stop-file',str(stop_path),
        '--timeout','15','--grace','2','--',str(worker_python),'-I','-c',runtime_code,str(running)],
        cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
    try:
        until = time.monotonic()+12
        while not ready.exists() and parent.poll() is None and time.monotonic()<until:
            time.sleep(0.02)
        assert ready.exists(), 'Actual child readiness was not observed'
        time.sleep(0.2)
        requested = time.monotonic(); stop_path.touch()
        stdout, stderr = parent.communicate(timeout=8)
        latency = time.monotonic()-requested
        assert parent.returncode == 130, (parent.returncode,stdout,stderr)
        r = json.loads(receipt_path.read_bytes())
        assert r['task_started'] and r['alive_when_stop_observed'] and r['direct_child_exit_observed']
        assert r['stop_reason']=='stop_file' and not complete.exists()
        last = heartbeat.read_bytes(); time.sleep(0.2)
        assert last and heartbeat.read_bytes() == last
        if os.name=='nt':
            assert r['status']=='finished_after_stop_request'
            assert r['termination_requests'] and r['exit_observed_after_termination_request']
            assert not r['signal_exit_after_request_observed'] and r['signals_requested']==[]
        else:
            assert r['status']=='interrupted' and r['signal_exit_after_request_observed']
        observations.append(dict(case='running_stop',status=r['status'],child_exit_code=r['child_exit_code'],
            natural_completion_file=False,heartbeat_count=len(last.splitlines()),
            heartbeat_unchanged_after_exit=True,request_to_wrapper_exit_seconds=round(latency,6)))
    finally:
        if parent.poll() is None:
            stop_path.touch(exist_ok=True)
            try:
                parent.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                parent.kill(); parent.communicate(timeout=5)

    for label, options in [('invalid_limit',('--timeout','nan')),('same_path',('--stop-file',results/'same_path.receipt.json'))]:
        path=results/(label+'.receipt.json')
        execute([cli,'--receipt',path,*options,'--',worker_python,'-I','-c',mutation,forbidden],2)
        assert not path.exists() and not forbidden.exists()
        observations.append(dict(case=label,task_started=False))
    missing=results/'missing.exe'
    path=results/'missing.receipt.json'
    execute([cli,'--receipt',path,'--',missing],2)
    r=json.loads(path.read_bytes())
    assert not r['task_started'] and r['status']=='supervisor_error'
    observations.append(dict(case='missing_executable',task_started=False,status=r['status']))
    if os.name=='nt':
        batch=results/'not-run.cmd';batch.write_text('@exit /b 7\n',encoding='utf-8')
        path=results/'batch.receipt.json'
        execute([cli,'--receipt',path,'--',batch],2)
        assert not path.exists()
        observations.append(dict(case='implicit_batch_rejected',task_started=False))

    fixture_count = 0
    if os.name=='posix':
        harness=repo/'experiments/rule-use-eval'
        predictions, metrics = results/'predictions.jsonl', results/'metrics.json'
        for name, task in [('baseline',[harness/'run_baseline.py','--baseline','link-following','--output',predictions]),
                           ('scoring',[harness/'score.py','--predictions',predictions,'--output',metrics])]:
            path=results/(name+'.receipt.json')
            execute([cli,'--receipt',path,'--timeout','15','--',worker_python,'-I',*task])
            r=json.loads(path.read_bytes()); assert r['status']=='completed' and r['direct_child_exit_observed']
        assert predictions.read_bytes()==(harness/'results/link-following.predictions.jsonl').read_bytes()
        assert metrics.read_bytes()==(harness/'results/link-following.metrics.json').read_bytes()
        fixture_count=len(predictions.read_text().splitlines())
    assert all((package/n).read_bytes()==b for n,b in sources.items())
    summary=dict(status='verified',version=VERSION,os_name=os.name,platform=sys.platform,
        observed_at=datetime.now(timezone.utc).isoformat(),installation=info,
        wheel=wheel.name,wheel_sha256=sha(wheel.read_bytes()),wheel_bytes=wheel.stat().st_size,
        modules_sha256={n:sha(b) for n,b in sources.items()},outside_source=True,
        installed_module_identity_checked=True,case_count=len(observations),cases=observations,
        original_linux_fixture_cases=fixture_count,
        scope='Author-run native direct-child EXE checks; base Python worker, not a venv child launcher. No model calls or process-tree guarantee.')
    (results/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True,indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wheel',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    a=p.parse_args();verify(a.wheel,a.out,a.repo)
