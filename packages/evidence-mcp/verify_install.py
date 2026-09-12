"""Install the built wheel outside its checkout, then call its installed command.

All environments, inputs and server processes are disposable. No language model
is used, and no user's existing Python environment or application is modified.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import venv
import zipfile


def save(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')


def wheel_record(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        record = next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
        rows = list(csv.reader(io.StringIO(z.read(record).decode())))
        assert {r[0] for r in rows} == set(z.namelist())
        for name, value, size in rows:
            assert not name.startswith('/') and '..' not in Path(name).parts
            if name == record:
                assert value == size == ''
                continue
            b=z.read(name)
            h=base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b'=').decode()
            assert value == 'sha256='+h and int(size)==len(b)
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'record_entries': len(rows)}


async def installed_client(command: str, output: Path) -> None:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    import second_paddle_evidence
    from second_paddle_evidence.__main__ import preflight
    attempts=[];spawns=[]
    def observe(event, args):
        if event == 'socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6):
            attempts.append(str(args[1])); raise RuntimeError('No external network belongs in the installed stdio exercise.')
        if event == 'subprocess.Popen':
            spawns.append({'executable': None if args[0] is None else str(args[0]),
                           'argv': args[1] if isinstance(args[1], str) else [str(x) for x in args[1]]})
    checked=preflight()
    assert Path(second_paddle_evidence.__file__).is_relative_to(Path(sys.prefix))
    summary={'status':'incomplete','preflight':checked,'interpreter':sys.executable,'python':sys.version,
             'platform':sys.platform,'cases':[],'schema':None}
    trace={'schema':'approval-trace-v1','events':[
        {'type':'propose','request_id':'wheel-A','scope':'install-test','payload':'  한글\n    preserve\n'},
        {'type':'approve','request_id':'wheel-A','scope':'install-test'},
        {'type':'execute','request_id':'wheel-A','scope':'install-test','payload':'  한글\n    preserve\n'}]}
    sys.addaudithook(observe)
    try:
        p=StdioServerParameters(command=command,args=[],cwd=str(output.parent),env={'PYTHONUTF8':'1'})
        async with Client(p,mode='auto',cache=None,read_timeout_seconds=15) as client:
            schema=(await client.list_tools()).model_dump(mode='json',by_alias=True,exclude_none=True)
            summary['schema']=schema
            assert {x['name'] for x in schema['tools']}=={'check_approval_trace','project_tool_result'}
            async def call(label,tool,param,text,error=False):
                response=(await client.call_tool(tool,{param:text})).model_dump(mode='json',by_alias=True,exclude_none=True)
                assert response.get('isError',False) is error
                value=response['structuredContent']
                assert json.loads(response['content'][0]['text'])==value
                summary['cases'].append({'label':label,'tool':tool,'input':text,'response':response})
                return value
            v=await call('matching','check_approval_trace','trace_json',json.dumps(trace))
            assert v['status']=='no_violation_observed' and v['valid_execution_attempts']==1
            trace['events'][-1]['payload']='changed task'
            v=await call('mismatch','check_approval_trace','trace_json',json.dumps(trace))
            assert v['status']=='violations_observed' and any(x['code']=='PAYLOAD_CHANGED' for x in v['issues'])
            v=await call('ambiguous','check_approval_trace','trace_json','{"schema":"approval-trace-v1","events":[],"events":[]}',True)
            assert v['status']=='not_assessed' and v['error']['code']=='DUPLICATE_JSON_MEMBER'
            v=await call('valid_after_error','project_tool_result','result_json','{"content":[],"structuredContent":{"result":[]},"isError":false}')
            assert v['source']=='structured_content' and v['result']['content']==[{'type':'text','text':'{"result":[]}'}]
            v=await call('error_preserved','project_tool_result','result_json','{"content":[],"structuredContent":{"error":"synthetic"},"isError":true}',True)
            assert v['result']['isError'] is True
        assert len(spawns)==1
        launch=spawns[0]
        if os.name=='nt':
            # Windows Popen's audit event can contain executable=None and a
            # quoted command-line string. Preserve it rather than split characters.
            assert launch['argv']==subprocess.list2cmdline([command])
            assert launch['executable'] is None or Path(launch['executable']).resolve()==Path(command).resolve()
        else:
            assert launch['argv']==[command] and Path(launch['executable']).resolve()==Path(command).resolve()
        assert not attempts
        summary['status']='passed'
    except BaseException as exc:
        summary['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        summary.update(network_attempts=attempts,server_launches=spawns)
        save(output,summary)


def verify(wheel: Path, out: Path) -> None:
    wheel=wheel.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    report={'status':'incomplete','wheel':wheel_record(wheel)}
    try:
        # A path with spaces and Korean also exercises Windows console entry quoting.
        envdir=out/'isolated install 한글'
        venv.EnvBuilder(with_pip=True).create(envdir)
        bindir=envdir/('Scripts' if os.name=='nt' else 'bin')
        python=bindir/('python.exe' if os.name=='nt' else 'python')
        command=bindir/('second-paddle-evidence.exe' if os.name=='nt' else 'second-paddle-evidence')
        env={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','HOME','USERPROFILE','APPDATA','LOCALAPPDATA')}
        env.update(PYTHONUTF8='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
        def run(label,args,expected=0,custom_env=None,timeout=100):
            p=subprocess.run([str(x) for x in args],cwd=out,env=custom_env or env,
                             capture_output=True,text=True,encoding='utf-8',timeout=timeout)
            (out/(label+'.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
            assert p.returncode==expected,(label,p.returncode,p.stderr[-3000:])
            return p
        run('pip-install',[python,'-m','pip','install',str(wheel)])
        run('pip-check',[python,'-m','pip','check'])
        assert command.exists()
        p=run('preflight',[command,'--check']);report['preflight']=json.loads(p.stdout)
        assert report['preflight']['status']=='ready' and report['preflight']['verified_files']==8
        assert Path(report['preflight']['package_location']).is_relative_to(envdir)
        no_node=dict(env,PATH='')
        missing=run('missing-node',[python,'-m','second_paddle_evidence','--check'],expected=2,custom_env=no_node)
        assert missing.stdout=='' and 'NODE_MISSING:' in missing.stderr
        report['missing_node_diagnostic']='exit2 and no stdout'
        # Copy only this test client, not the source tree, to its independent CWD.
        client=out/'installed_client.py';shutil.copyfile(Path(__file__),client)
        run('installed-stdio',[python,client,'--exercise',command,'--out',out/'calls.json'],timeout=80)
        report['calls']=json.loads((out/'calls.json').read_text())
        assert report['calls']['status']=='passed' and len(report['calls']['cases'])==5
        run('pip-freeze',[python,'-m','pip','freeze'])
        report['status']='verified-installed-wheel'
    except BaseException as exc:
        report['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        save(out/'summary.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wheel',type=Path);p.add_argument('--exercise');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.exercise:
        asyncio.run(installed_client(a.exercise,a.out))
    else:
        if a.wheel is None: p.error('--wheel is required')
        verify(a.wheel,a.out)
