# SPDX-License-Identifier: Apache-2.0
"""Bounded live-local-storage checks; never target a user installation."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

CURRENT = '127bb79725aeb09d70e58620fd1d88476abf9aca'
OLDER = 'cec74a8ebf5a9d6724104d4867868da118b58205'
SOURCE = 'mem0/vector_stores/langchain.py'


def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--probe', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    repo, out, home = (root/name for name in ('repo','output','home'))
    for d in (repo, out, home): d.mkdir()
    shutil.copy2(args.probe, out/'test_real_chroma.py')
    shutil.copy2(__file__, out/'run.py')
    env = {'PATH':os.environ['PATH'],'HOME':str(home),'LANG':'C.UTF-8',
           'GIT_LFS_SKIP_SMUDGE':'1','GIT_TERMINAL_PROMPT':'0',
           'PYTHONDONTWRITEBYTECODE':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    report = {'completed':False,'candidate_commit':CURRENT,'older_adapter_commit':OLDER,
              'run_id':os.getenv('GITHUB_RUN_ID'),'workflow_commit':os.getenv('GITHUB_SHA'),
              'model_calls':0,'runs':{}}
    original = None
    def call(argv, name, *, child_env=None, timeout=90, check=True):
        r = subprocess.run(list(map(str,argv)),cwd=repo,env=child_env or env,
                           text=True,capture_output=True,timeout=timeout)
        (out/(name+'.log')).write_text('COMMAND '+repr(argv)+'\n'+r.stdout+'\nSTDERR\n'+r.stderr)
        print(name,r.returncode,r.stdout[-3000:],r.stderr[-1000:],flush=True)
        if check:r.check_returncode()
        return r
    try:
        call(['git','init','-q'],'init')
        call(['git','fetch','--depth=1','https://github.com/Souptik96/mem0.git',CURRENT],'fetch',timeout=120)
        call(['git','checkout','--detach','FETCH_HEAD'],'checkout')
        assert call(['git','rev-parse','HEAD'],'identity').stdout.strip()==CURRENT
        original=(repo/SOURCE).read_bytes()
        assert blob(original)=='09e2ee4f9a5471878c6166b3fdab752389354a9c'
        helper=repo/'tests/memory/test_main.py'
        assert blob(helper.read_bytes())=='df10946acb1821e1a94dedf7cc1854b8f2ebbce8'
        saved=out/'source';saved.mkdir()
        for path in (SOURCE,'tests/memory/test_main.py','mem0/memory/main.py','pyproject.toml','LICENSE'):
            target=saved/path;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(repo/path,target)
        url='https://raw.githubusercontent.com/Souptik96/mem0/'+OLDER+'/'+SOURCE
        with urllib.request.urlopen(url,timeout=25) as response:data=response.read(100001)
        assert len(data)<=100000 and blob(data)=='c3f5f60ebc9418730235493eba2a73f9cb3f8a34'
        old=data;(out/'older_adapter.py').write_bytes(old)
        call([sys.executable,'-m','venv',root/'venv'],'venv',timeout=30)
        py=root/'venv/bin/python'
        requirements=['-e',str(repo)+'[test]','langchain==0.3.30',
                      'langchain-community==0.3.31','langchain-core==0.3.86','chromadb==1.5.9']
        call([py,'-m','pip','install',*requirements],'install',timeout=300)
        (out/'environment.txt').write_text(call([py,'-m','pip','freeze','--all'],'freeze').stdout)
        for variant,raw in (('candidate',original),('older_adapter',old)):
            (repo/SOURCE).write_bytes(raw)
            dest=out/variant;dest.mkdir()
            fresh=root/(variant+'-home');fresh.mkdir()
            child_env={**env,'HOME':str(fresh),'XDG_CONFIG_HOME':str(fresh/'config'),
                       'ZERO_REPO':str(repo),'ZERO_OUTPUT':str(dest),'ZERO_VARIANT':variant,
                       'PYTHONPATH':str(repo),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
                       'ANONYMIZED_TELEMETRY':'False','MEM0_TELEMETRY':'false',
                       'LANGCHAIN_TRACING_V2':'false','LANGSMITH_TRACING':'false','HF_HUB_OFFLINE':'1'}
            xml=dest/'junit.xml'
            pytest_args=['-q','-s','--noconftest','-p','pytest_mock','-p','pytest_asyncio.plugin',
                         '-p','no:cacheprovider','-o','addopts=','--junitxml='+str(xml),str(out/'test_real_chroma.py')]
            entry=('import socket,json,atexit,pathlib\n'
                   'attempts=[]\n'
                   'def deny(*a,**k):\n attempts.append("socket_or_dns");raise RuntimeError("Network forbidden in this local storage test")\n'
                   'socket.socket.connect=socket.socket.connect_ex=socket.getaddrinfo=deny\n'
                   'atexit.register(lambda:pathlib.Path('+repr(str(dest/'network.json'))+').write_text(json.dumps({"attempts":len(attempts)})))\n'
                   'import pytest\nraise SystemExit(pytest.main('+repr(pytest_args)+'))\n')
            (dest/'entry.py').write_text(entry)
            r=call([py,'-B',dest/'entry.py'],variant,child_env=child_env,timeout=100,check=False)
            cases=ET.parse(xml).findall('.//testcase')
            rows=[json.loads(line) for line in (dest/'observations.jsonl').read_text().splitlines()]
            failures=[n.attrib['name'] for n in cases if n.find('failure') is not None]
            errors=[n.attrib['name'] for n in cases if n.find('error') is not None]
            skips=[n.attrib['name'] for n in cases if n.find('skipped') is not None]
            report['runs'][variant]={'cases':len(cases),'observations':len(rows),'failures':failures,
                  'errors':errors,'skips':skips,'passed_contracts':sum(x['contract_met'] for x in rows),
                  'source_blob':blob(raw),'exit':r.returncode}
            assert len(cases)==len(rows)==8 and len({x['case'] for x in rows})==8
            assert not errors and not skips and r.returncode in (0,1)
            assert (r.returncode==0)==(not failures)
            assert json.loads((dest/'network.json').read_text())['attempts']==0
        assert blob(helper.read_bytes())=='df10946acb1821e1a94dedf7cc1854b8f2ebbce8'
        report['completed']=True
    except Exception as exc:
        report['error']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        if original is not None:
            (repo/SOURCE).write_bytes(original)
            report['source_restored']=(repo/SOURCE).read_bytes()==original
        (out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
        print('SUMMARY '+json.dumps(report),flush=True)
    return 0 if report['completed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
