"""One actual MCP result, two Python SSE -> official TypeScript client paths.

Four synthetic MCP tools are each called once in-process. Cached original results
are then sent over loopback HTTP using either undeclared fields or explicit app
metadata. No source-package edits, provider/model calls, or live UI rendering.
"""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from bridge import KEY, result_metadata

TEXT = "[Synthetic UI result]\n  한글 텍스트 그대로\n"
CANARY = "HOST_ONLY_CANARY_DO_NOT_FORWARD"
FIXTURES = {
    'ui': {'tree':{'type':'text','value':'  한글\n    keep\n'},'items':[],'enabled':False,'count':0,'optional':None},
    'empty_object': {},
    'error': {'reason':'synthetic failure','retry':False},
    'absent': None,
}


def save(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


async def collect_once():
    from mcp import Client
    from mcp.server.mcpserver import MCPServer
    from mcp_types import CallToolResult, TextContent
    # Postponed annotations are resolved against module globals by the SDK.
    globals()['CallToolResult']=CallToolResult
    calls=Counter()
    server=MCPServer('synthetic-handoff-source')
    @server.tool()
    def render_fixture(case: str) -> CallToolResult:
        calls[case]+=1
        data={'content':[{'type':'text','text':TEXT}], 'isError':case=='error', '_meta':{'private_demo':CANARY}}
        if FIXTURES[case] is not None:data['structuredContent']=deepcopy(FIXTURES[case])
        return CallToolResult.model_validate(data)
    received={}
    async with Client(server,mode='auto',cache=None) as client:
        for case in FIXTURES:
            value=await client.call_tool('render_fixture',{'case':case})
            received[case]=value.model_dump(mode='json',by_alias=True,exclude_none=True)
    assert calls == Counter({k:1 for k in FIXTURES})
    return received,dict(calls)


def main(out):
    from ag_ui.core import (RunStartedEvent,ToolCallStartEvent,ToolCallArgsEvent,
                            ToolCallEndEvent,ToolCallResultEvent,RunFinishedEvent)
    from ag_ui.encoder import EventEncoder
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    versions={name:md.version(name) for name in ['ag-ui-protocol','mcp','pydantic']}
    assert versions['ag-ui-protocol']=='0.1.22' and versions['mcp']=='2.2.0'
    source={}
    for name in ['ag_ui.core.events','ag_ui.core.types','ag_ui.encoder.encoder','mcp.client.client']:
        p=Path(importlib.import_module(name).__file__)
        source[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    report={'status':'incomplete','versions':versions,'imports':source,'requests':[],'server_errors':[]}
    # Deny Internet destinations after imports; only this test's loopback is allowed.
    connections=[]
    def audit(event,args):
        if event=='socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6):
            host=str(args[1][0]);connections.append(host)
            if host not in ('127.0.0.1','::1'):raise RuntimeError('Unexpected network destination')
    sys.addaudithook(audit)
    received,calls=asyncio.run(collect_once())
    report['mcp_calls']=calls
    save(out/'received-once.json',received)
    original=deepcopy(received)
    encoder=EventEncoder()
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def do_POST(self):
            try:
                mode,case=self.path.strip('/').split('/')
                assert mode in ('top_level','metadata') and case in FIXTURES
                n=int(self.headers.get('Content-Length','0'));assert 0<n<100000
                request=json.loads(self.rfile.read(n))
                call_id=f'call-{mode}-{case}';message_id=f'result-{mode}-{case}'
                response=received[case]
                fields={'message_id':message_id,'tool_call_id':call_id,'content':TEXT,'role':'tool'}
                if mode=='metadata':
                    fields['metadata']=result_metadata(response,{'application':'synthetic-handoff'})
                elif 'structuredContent' in response:
                    fields['structuredContent']=deepcopy(response['structuredContent'])
                    fields['isError']=response.get('isError',False)
                event=ToolCallResultEvent(**fields)
                events=[RunStartedEvent(thread_id=request['threadId'],run_id=request['runId']),
                    ToolCallStartEvent(tool_call_id=call_id,tool_call_name='render_fixture',parent_message_id=f'assistant-{mode}-{case}'),
                    ToolCallArgsEvent(tool_call_id=call_id,delta=json.dumps({'case':case})),
                    ToolCallEndEvent(tool_call_id=call_id),event,
                    RunFinishedEvent(thread_id=request['threadId'],run_id=request['runId'])]
                body=''.join(encoder.encode(e) for e in events).encode('utf-8')
                assert CANARY.encode() not in body
                (out/f'{mode}-{case}.sse').write_bytes(body)
                report['requests'].append({'mode':mode,'case':case,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),
                    'content_type':encoder.get_content_type(),'event':event.model_dump(mode='json',by_alias=True)})
                self.send_response(200);self.send_header('Content-Type',encoder.get_content_type())
                self.send_header('Content-Length',str(len(body)));self.send_header('Connection','close');self.end_headers()
                self.wfile.write(body);self.wfile.flush()
            except BaseException as e:
                report['server_errors'].append(type(e).__name__+': '+str(e))
                self.send_error(500,'Synthetic test failed')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        job=subprocess.run(['node',str(Path(__file__).with_name('consume.cjs')),f'http://127.0.0.1:{server.server_port}',str(out/'consumer.json')],
             capture_output=True,text=True,timeout=75)
        (out/'consumer.log').write_text(job.stdout+'\n'+job.stderr,encoding='utf-8')
        assert job.returncode==0,job.stderr[-3000:]
        consumer=json.loads((out/'consumer.json').read_text())
        assert consumer['status']=='passed' and len(consumer['cases'])==8
        assert len(report['requests'])==8 and not report['server_errors']
        for c in consumer['cases']:
            source_event=next(r['event'] for r in report['requests'] if (r['mode'],r['case'])==(c['mode'],c['case']))
            assert c['event']['content']==source_event['content']==c['message']['content']==TEXT
            expected=FIXTURES[c['case']]
            if c['mode']=='metadata' and expected is not None:
                packet={'structuredContent':expected,'isError':c['case']=='error'}
                assert c['event']['metadata'][KEY]==c['message']['metadata'][KEY]==packet
            elif expected is None:
                assert KEY not in c['event'].get('metadata',{})
                assert KEY not in c['message'].get('metadata',{})
        assert received==original and calls=={k:1 for k in FIXTURES}
        report.update(status='verified',consumer=consumer,originals_unchanged=True,network_destinations=connections,
          scope='Four in-process synthetic MCP calls, eight actual loopback HTTP SSE streams, published Python/TypeScript SDKs. No LLM, remote MCP, iframe renderer, integration-specific host, or general adoption claim.')
    except BaseException as e:
        report['error']=type(e).__name__+': '+str(e);raise
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        save(out/'summary.json',report)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args().out)
