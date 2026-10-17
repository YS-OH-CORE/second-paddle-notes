"""Bounded public-source test execution, plus two explicitly local mutants.
No installed Hermes or user data. Temporary HOME, mocked SDK, and no model calls.
"""
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import hashlib, json, os, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PIN = '91b3b31dc91aec04abac8be5d240f2d0ad491054'
EXPECTED = {'plugins/memory/honcho/__init__.py':'0e4c4e5bc853038baeee2aed33f2415d5b2ec8ca',
            'plugins/memory/honcho/client.py':'cc1da55ffaf4c8d7aacfccc4eb15b153f6f5e6eb',
            'plugins/memory/honcho/session.py':'97bdb3b35eed896223a2390583dc4a5a35b0b251'}

def emit(kind, value):
    print('HONCHO_'+kind+' '+json.dumps(value, ensure_ascii=False), flush=True)

def execute(repo, out, label):
    test = HERE/'test_real_config.py'
    xml = out/(label+'.xml')
    env = {**os.environ, 'PYTHONPATH':str(repo), 'HOME':str(out/'home'),
           'HERMES_HOME':str(out/'home/profile'), 'PYTHONDONTWRITEBYTECODE':'1',
           'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1', 'DO_NOT_TRACK':'1'}
    for k in list(env):
        if k.startswith(('HONCHO_', 'HERMES_HONCHO_')):env.pop(k)
    Path(env['HERMES_HOME']).mkdir(parents=True, exist_ok=True)
    p = subprocess.run([sys.executable,'-B','-m','pytest','--noconftest','-o','addopts=',
                        '-p','no:cacheprovider',str(test),'-q','--junitxml='+str(xml)],
                       cwd=repo, env=env, capture_output=True, text=True, timeout=70)
    (out/(label+'.log')).write_text(p.stdout+'\n'+p.stderr, encoding='utf-8')
    root = ET.parse(xml).getroot() if xml.exists() else None
    cases=[]
    if root is not None:
        for c in root.iter('testcase'):
            state=next((s for s in ('error','failure','skipped') if c.find(s) is not None),'passed')
            cases.append({'name':c.attrib['name'],'outcome':state})
    record={'variant':label,'exit':p.returncode,'cases':cases,'stdout':p.stdout,'stderr':p.stderr}
    emit('EXECUTION', record)
    return record

def main():
    with tempfile.TemporaryDirectory(prefix='honcho-reviewed-config-') as td:
        root=Path(td);repo=root/'repo';out=root/'results';out.mkdir()
        # The whole ZIP exceeded the 64-MiB cap before any tests in attempt 1.
        # Fetch only git metadata and selected source blobs, not repository media.
        repo.mkdir()
        git_env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,
                 'GIT_TERMINAL_PROMPT':'0','GIT_LFS_SKIP_SMUDGE':'1'}
        def git(*args):
            p=subprocess.run(['git','-c','core.hooksPath=/dev/null',*args],cwd=repo,
                             env=git_env,capture_output=True,text=True,timeout=65)
            if p.returncode:raise RuntimeError('Sparse source acquisition failed: '+p.stderr[-700:])
            return p.stdout.strip()
        git('init','-q')
        git('remote','add','origin','https://github.com/saurabhmeddo/hermes-agent.git')
        git('config','core.sparseCheckout','true')
        git('config','core.sparseCheckoutCone','false')
        patterns='/*.py\n/agent/**/*.py\n/hermes_cli/**/*.py\n/tools/**/*.py\n/plugins/**/*.py\n/gateway/**/*.py\n/cron/**/*.py\n/pyproject.toml\n'
        (repo/'.git/info/sparse-checkout').write_text(patterns)
        git('fetch','--filter=blob:none','--depth=1','origin',PIN)
        git('checkout','--detach','--quiet','FETCH_HEAD')
        if git('rev-parse','HEAD')!=PIN:raise ValueError('Unexpected checked out commit')
        selected=[p for p in repo.rglob('*') if p.is_file() and '.git' not in p.relative_to(repo).parts]
        if any(p.is_symlink() for p in selected):raise ValueError('No source symlinks allowed')
        total=sum(p.stat().st_size for p in selected)
        emit('ACQUISITION',{'selected_files':len(selected),'selected_bytes':total,'largest':[(str(p.relative_to(repo)),p.stat().st_size) for p in sorted(selected,key=lambda p:p.stat().st_size,reverse=True)[:5]]})
        if total>64*1024*1024:raise ValueError('Selected source exceeds 64 MiB')
        metadata_bytes=sum(p.stat().st_size for p in (repo/'.git').rglob('*') if p.is_file())
        for path, wanted in EXPECTED.items():
            b=(repo/path).read_bytes()
            got=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
            if got!=wanted:raise ValueError('Upstream source blob mismatch: '+path)
        emit('SOURCE', {'commit':PIN,'blobs':EXPECTED,'acquisition':'depth-1 blob-filtered sparse checkout',
                        'git_metadata_bytes':metadata_bytes,'selected_source_files':len(selected),'selected_source_bytes':total,
                        'packages':{p:version(p) for p in ('honcho-ai','pytest','PyYAML','python-dotenv','rich')}})
        rows=[]
        rows.append(execute(repo,out,'original_pr_head'))
        if len(rows[-1]['cases'])!=4 or any(c['outcome']!='passed' for c in rows[-1]['cases']):
            emit('STOP',{'why':'Initial test must pass before any mutant is meaningful','model_calls':0})
            return 1
        provider=repo/'plugins/memory/honcho/__init__.py'
        client=repo/'plugins/memory/honcho/client.py'
        original_provider, original_client = provider.read_bytes(), client.read_bytes()
        try:
            src=original_provider.decode();old='if not self._automatic_persistence_enabled():\n                logger.debug('
            if src.count(old)!=1:raise ValueError('Startup mutation scope differs')
            provider.write_text(src.replace(old,'if False:  # test-only disabled startup guard\n                logger.debug(',1))
            rows.append(execute(repo,out,'startup_guard_bypassed'))
            provider.write_bytes(original_provider)
            src=original_client.decode();old='save_messages = host_save if host_save is not None else raw.get("saveMessages", True)'
            if src.count(old)!=1:raise ValueError('Config mutation scope differs')
            client.write_text(src.replace(old,'save_messages = True  # test-only ignored on-disk setting',1))
            rows.append(execute(repo,out,'disk_setting_ignored'))
        finally:
            provider.write_bytes(original_provider);client.write_bytes(original_client)
        fail_names={'test_disk_config_controls_startup_content_upload[root-false]',
                    'test_disk_config_controls_startup_content_upload[host-false-over-root-true]'}
        for row in rows[1:]:
            if len(row['cases'])!=4 or {c['name'] for c in row['cases'] if c['outcome']=='failure'}!=fail_names:
                raise ValueError('Mutant outcome differs; do not claim discrimination')
            if any(c['outcome'] not in ('passed','failure') for c in row['cases']):
                raise ValueError('Setup failures are not detected regressions')
        emit('SUMMARY', {'status':'four_config_paths_verified_with_two_detector_controls','utc':datetime.now(timezone.utc).isoformat(),
             'pinned_head':PIN,'variants':[{k:r[k] for k in ('variant','exit','cases')} for r in rows],
             'upstream_source_restored':provider.read_bytes()==original_provider and client.read_bytes()==original_client,
             'new_model_calls':0,'user_pc_accesses':0,'live_remote_service_used':False,
             'not_tested':['live Honcho transport','CLI initialization','concurrent profiles','complete lifecycle coverage','current main']})
        return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        emit('ABORT',{'error_type':type(exc).__name__,'message':str(exc)[:400]});raise
