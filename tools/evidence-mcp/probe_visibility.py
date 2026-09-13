"""Compare two actually installed wheels over MCP stdio using synthetic data.

The parent receives public SDK dependencies from CI. Each child imports only its
selected --target wheel and those dependencies. No host configuration or model.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from test_visibility import CANARY, cases

async def run(old: Path, new: Path, out: Path) -> None:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    report={'status':'incomplete','cases':[],'imports':{},'network_attempts':[]}
    env={k:os.environ[k] for k in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','HOME','USERPROFILE') if k in os.environ}
    env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    try:
        for label, site, version in [('old',old,'0.1.0a1'),('new',new,'0.1.0a2')]:
            child_env=dict(env,PYTHONPATH=str(site.resolve()))
            info=json.loads(subprocess.check_output([sys.executable,'-c',
                'import json,importlib.metadata as m,second_paddle_evidence as p; '
                'print(json.dumps({"file":p.__file__,"version":m.version("second-paddle-evidence"),"mcp":m.version("mcp")}))'],
                env=child_env,text=True,timeout=15))
            assert Path(info['file']).is_relative_to(site.resolve()) and info['version']==version and info['mcp']=='2.2.0'
            report['imports'][label]=info
        def audit(event,args):
            if event=='socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6):
                report['network_attempts'].append(str(args[1]));raise RuntimeError('No network needed for stdio exercise')
        sys.addaudithook(audit)
        for label, site in [('old',old),('new',new)]:
            p=StdioServerParameters(command=sys.executable,args=['-m','second_paddle_evidence'],
                  cwd=str(out),env=dict(env,PYTHONPATH=str(site.resolve())))
            async with Client(p,mode='auto',cache=None,read_timeout_seconds=15) as client:
                names={t.name for t in (await client.list_tools()).tools}
                assert names=={'project_tool_result','check_approval_trace'}
                for name,value,expected in cases():
                    text=json.dumps(value,ensure_ascii=True)
                    raw=(await client.call_tool('project_tool_result',{'result_json':text})).model_dump(mode='json',by_alias=True,exclude_none=True)
                    parsed=json.loads(raw['content'][0]['text'])
                    assert parsed==raw['structuredContent']
                    visible=json.dumps({'content':raw['content'],'structuredContent':raw['structuredContent']},ensure_ascii=True)
                    entry={'version':label,'case':name,'input':value,'response':raw,'marker_in_output':CANARY in visible}
                    report['cases'].append(entry)
                    if label=='new' and expected:
                        assert raw.get('isError') is True
                        assert parsed=={'status':'not_assessed','error':{'code':expected}}
                        assert not entry['marker_in_output']
                    elif expected is None:
                        assert raw.get('isError',False)==value.get('isError',False)
                        assert parsed['status']=='projected'
                        for key in value:
                            if key!='content':assert parsed['result'][key]==value[key]
                        if value['content']:assert parsed['result']['content']==value['content']
        old_rows=[x for x in report['cases'] if x['version']=='old']
        new_rows=[x for x in report['cases'] if x['version']=='new']
        assert next(x for x in old_rows if x['case']=='result_metadata')['marker_in_output']
        assert len(old_rows)==len(new_rows)==12 and not report['network_attempts']
        for a,b in zip(old_rows,new_rows):
            assert a['case']==b['case']
            if not any(n==a['case'] and code for n,_,code in cases()):
                assert a['response']==b['response']
        report.update(status='verified',old_marker_cases=[x['case'] for x in old_rows if x['marker_in_output']],
            new_marker_cases=[x['case'] for x in new_rows if x['marker_in_output']],
            scope='Actual installed-wheel MCP stdio responses;12 cases in2 versions, no real model or private input. Output rejection cannot remove an already exposed input argument.')
    except BaseException as e:
        report['error']=type(e).__name__+': '+str(e);raise
    finally:
        (out/'visibility.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old',type=Path,required=True);p.add_argument('--new',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();asyncio.run(run(a.old,a.new,a.out))
