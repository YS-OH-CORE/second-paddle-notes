"""Compare current replay with an application graph that checkpoints each round.

All effects are synthetic labels. Reopen the SQLite saver and rebuild the graph
between every review and resume; keep the in-process MCP server alive. This is
not a process-crash, remote-service, or language-model experiment.
"""
from __future__ import annotations
import argparse
import asyncio
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import socket
import sys
import traceback
from round_graph import build_round_graph

PINS={'langchain':'1.4.0','langchain-core':'1.6.2','langgraph':'1.2.11',
      'fastmcp':'4.0.1','mcp':'2.1.1','langgraph-checkpoint-sqlite':'3.1.1'}
SPECS={
 'baseline_stable': {'fresh':False,'drift':True,'rounds':1},
 'baseline_fresh': {'fresh':True,'drift':True,'rounds':1},
 'saved_same': {'fresh':False,'drift':False,'rounds':1},
 'saved_stable': {'fresh':False,'drift':True,'rounds':1},
 'saved_fresh': {'fresh':True,'drift':True,'rounds':1},
 'saved_two_rounds': {'fresh':True,'drift':True,'rounds':2},
 'saved_decline': {'fresh':False,'drift':True,'rounds':1,'decision':'decline'},
 'saved_cancel': {'fresh':False,'drift':True,'rounds':1,'decision':'cancel'},
 'saved_wrong_key': {'fresh':False,'drift':True,'rounds':1,'wrong_key':True},
 'saved_error': {'fresh':False,'drift':True,'rounds':1,'error':True},
}
NOTE='  한글 원래 답\n    keep indentation\n'


def save(path, data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


async def exercise(out: Path, report: dict):
    from fastmcp import FastMCP, Context
    from langchain.mcp import MCPAdapter
    from langchain_core.messages import AIMessage
    from langgraph.graph import StateGraph, MessagesState, START, END
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.types import Command
    from mcp.types import ElicitRequest,ElicitRequestFormParams,ElicitResult,InputRequiredResult,CallToolResult,TextContent
    globals().update(Context=Context,InputRequiredResult=InputRequiredResult,CallToolResult=CallToolResult)
    server=FastMCP('checkpointed-synthetic-previews')
    sequence={case:0 for case in SPECS};issued={};completed=[];server_log=[]
    report.update(server_log=server_log,completed=completed,cases=[])

    def question(case,subject,round_index,serial):
        spec=SPECS[case]
        key=f'confirm-{serial}-{round_index}' if spec['fresh'] else f'confirm-{round_index}'
        state=json.dumps({'case':case,'subject':subject,'round':round_index,'serial':serial},sort_keys=True)
        issued[state]={'case':case,'subject':subject,'round':round_index,'serial':serial,'key':key}
        message=f'Preview {subject}, round {round_index}? 한글 표본'
        schema={'type':'object','properties':{'yes':{'type':'boolean'},'note':{'type':'string'}},'required':['yes','note']}
        return InputRequiredResult(input_requests={key:ElicitRequest(method='elicitation/create',
            params=ElicitRequestFormParams(mode='form',message=message,requested_schema=schema))},request_state=state)

    @server.tool
    async def preview(case: str, ctx: Context) -> str | InputRequiredResult | CallToolResult:
        """Ask before recording only a harmless synthetic preview label."""
        spec=SPECS[case]
        if ctx.request_state is None:
            sequence[case]+=1;serial=sequence[case]
            subject='draft-B' if spec['drift'] and serial>1 else 'draft-A'
            result=question(case,subject,1,serial)
            server_log.append({'phase':'initial','case':case,'subject':subject,'state':result.request_state,
                               'key':next(iter(result.input_requests))})
            return result
        state=ctx.request_state
        if state not in issued or issued[state]['case']!=case:raise ValueError('UNKNOWN_ROUND')
        original=issued[state];answer=(ctx.input_responses or {}).get(original['key'])
        row={'phase':'resume','case':case,'state':state,'subject':original['subject'],'round':original['round'],
             'key':original['key'],'action':getattr(answer,'action',None),'content':deepcopy(getattr(answer,'content',None))}
        server_log.append(row)
        if not isinstance(answer,ElicitResult):raise ValueError('MISSING_ORIGINAL_ANSWER')
        if answer.action!='accept':row['outcome']=answer.action;return 'skipped:'+answer.action
        if not answer.content or answer.content.get('yes') is not True or answer.content.get('note')!=NOTE:
            raise ValueError('FORM_CONTENT_DIFFER')
        if spec.get('error'):
            row['outcome']='synthetic_tool_error'
            return CallToolResult(content=[TextContent(type='text',text='SYNTHETIC_FAILURE')],is_error=True)
        if original['round']<spec['rounds']:
            row['outcome']='next_round'
            return question(case,original['subject'],original['round']+1,original['serial'])
        row['outcome']='preview_recorded';completed.append({'case':case,'subject':original['subject']})
        return 'previewed:'+original['subject']

    async with MCPAdapter(server) as adapter:
        tools=await adapter.list_tools()
        for case in ['baseline_stable','baseline_fresh']:
            start=len(server_log);effects=len(completed)
            b=StateGraph(MessagesState);b.add_node('tools',ToolNode(tools));b.add_edge(START,'tools');b.add_edge('tools',END)
            graph=b.compile(checkpointer=InMemorySaver());config={'configurable':{'thread_id':case}}
            initial=await graph.ainvoke({'messages':[AIMessage(content='',tool_calls=[{'name':'preview','args':{'case':case},'id':case,'type':'tool_call'}])]},config)
            shown=deepcopy(initial['__interrupt__'][0].value)
            key=shown['requests'][0]['key'];answer={'responses':{key:{'action':'accept','content':{'yes':True,'note':NOTE}}}}
            row={'case':case,'path':'original_adapter','shown':[shown],'answers':[answer]}
            try:
                result=await graph.ainvoke(Command(resume=answer),config)
                row.update(outcome='returned',result=result['messages'][-1].model_dump(mode='json'),
                           remaining_interrupts=len(result.get('__interrupt__',[])))
            except Exception as exc:row.update(outcome='raised',error=type(exc).__name__+': '+str(exc))
            row.update(server_log=deepcopy(server_log[start:]),completed=deepcopy(completed[effects:]))
            report['cases'].append(row)

        class SessionRecorder:
            def __init__(self):self.calls=[]
            async def call_tool(self,*args,**kwargs):
                call={'tool':args[0],'arguments':deepcopy(args[1]),'supplied_state':kwargs.get('request_state'),
                      'input_responses':{k:v.model_dump(mode='json',by_alias=True,exclude_none=True) for k,v in (kwargs.get('input_responses') or {}).items()}}
                self.calls.append(call)
                received=await adapter.client.session.call_tool(*args,**kwargs)
                call['received_state']=getattr(received,'request_state',None)
                call['received_kind']='input' if isinstance(received,InputRequiredResult) else 'terminal'
                return received

        for case,spec in SPECS.items():
            if case.startswith('baseline_'):continue
            start=len(server_log);effects=len(completed);recorder=SessionRecorder()
            db=out/(case+'.sqlite');config={'configurable':{'thread_id':case}}
            row={'case':case,'path':'checkpointed_round_graph','shown':[],'answers':[],'saved_frames':[],
                 'reopened_frames':[],'graph_instances':0,'process_id':os.getpid()}
            pending={'tool_name':'preview','arguments':{'case':case}}
            for phase in range(4):
                try:
                    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
                        graph=build_round_graph(recorder,saver);row['graph_instances']+=1
                        if phase:
                            old=await graph.aget_state(config)
                            row['reopened_frames'].append(deepcopy(old.values['frame']))
                            assert old.values['frame']==row['saved_frames'][-1]
                        current=await graph.ainvoke(pending,config,durability='sync')
                        snapshot=await graph.aget_state(config)
                        if current.get('__interrupt__'):
                            shown=deepcopy(current['__interrupt__'][0].value)
                            assert 'draft-A' in shown['requests'][0]['message']
                            assert 'request_state' not in json.dumps(shown) and 'requestState' not in json.dumps(shown)
                            row['shown'].append(shown);row['saved_frames'].append(deepcopy(snapshot.values['frame']))
                            action=spec.get('decision','accept');key=shown['requests'][0]['key']
                            decision={'action':action}
                            if action=='accept':decision['content']={'yes':True,'note':NOTE}
                            answer={'responses':{('not-the-question' if spec.get('wrong_key') else key):decision}}
                            row['answers'].append(deepcopy(answer));pending=Command(resume=answer)
                        else:
                            row.update(outcome='returned',status=current['status'],result=current['result']);break
                    # The old graph and database handle are no longer reused.
                except Exception as exc:
                    row.update(outcome='raised',error=type(exc).__name__+': '+str(exc));break
            else:raise AssertionError('Unexpected number of review rounds')
            row.update(server_log=deepcopy(server_log[start:]),completed=deepcopy(completed[effects:]),
                       wire_calls=recorder.calls,database_bytes=db.stat().st_size)
            assert len(row['reopened_frames'])==len(row['saved_frames'])
            for prior,next_call in zip(recorder.calls,recorder.calls[1:]):
                assert next_call['supplied_state']==prior['received_state']
            assert sum(e['phase']=='initial' for e in row['server_log'])==1
            report['cases'].append(row)

    rows={r['case']:r for r in report['cases']};subjects=lambda c:[x['subject'] for x in rows[c]['completed']]
    assert subjects('baseline_stable')==['draft-B'] and rows['baseline_stable']['result']['status']=='success'
    assert rows['baseline_fresh']['outcome']=='raised' and not subjects('baseline_fresh')
    for case in ['saved_same','saved_stable','saved_fresh','saved_two_rounds']:
        assert subjects(case)==['draft-A'] and rows[case]['status']=='completed'
        assert all(e['subject']=='draft-A' for e in rows[case]['server_log'])
    assert len(rows['saved_two_rounds']['shown'])==2 and rows['saved_two_rounds']['graph_instances']==3
    for case in ['saved_decline','saved_cancel','saved_error','saved_wrong_key']:assert not subjects(case)
    assert rows['saved_error']['status']=='tool_error' and rows['saved_error']['result']['isError'] is True
    assert rows['saved_wrong_key']['outcome']=='raised' and 'ANSWER_KEYS_DIFFER' in rows['saved_wrong_key']['error']
    assert len(rows['saved_wrong_key']['wire_calls'])==1
    assert all(len(r['wire_calls'])==len(r['server_log']) for r in rows.values() if 'wire_calls' in r)
    report.update(status='verified',baseline_subject_drift_observed=True,checkpointed_subjects_preserved=True,
                  checkpointed_initial_requests=8,checkpointed_case_count=8,baseline_case_count=2,
                  scope='One Python process with real in-process MCP calls. SQLite handles and graphs are rebuilt between review phases. No OS-process restart, LLM, human answer, real remote effect or crash-atomicity test.')


def main(out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    r={'status':'incomplete','packages':{},'network_attempts':[],'python':sys.version}
    try:
        r['packages']={name:md.version(name) for name in PINS};assert r['packages']==PINS,r['packages']
        # Import before the network audit so optional package setup is separate.
        imports=['langchain.mcp.elicitation','langchain.mcp.tools','fastmcp','langgraph.checkpoint.sqlite.aio']
        r['source']={}
        for name in imports:
            file=Path(importlib.import_module(name).__file__);raw=file.read_bytes()
            r['source'][name]={'path':str(file),'sha256':hashlib.sha256(raw).hexdigest(),
                'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
        assert r['source']['langchain.mcp.elicitation']['git_blob']=='efab8d70a74c74392f883df229c2053a58b2eddb'
        def block(event,args):
            if event=='socket.connect' and args[0].family in (socket.AF_INET,socket.AF_INET6):
                r['network_attempts'].append(str(args[1]));raise RuntimeError('NO_NETWORK_IN_SYNTHETIC_EXERCISE')
        sys.addaudithook(block)
        asyncio.run(asyncio.wait_for(exercise(out,r),timeout=90))
        assert not r['network_attempts']
    except BaseException as exc:
        r.update(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc());raise
    finally:save(out/'observations.json',r)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args().out)
