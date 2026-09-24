"""Bounded LME-V2 #7 reader-boundary characterization and cleanup candidate.

Run against a disposable checkout with pinned OpenAI SDK + HTTPX MockTransport.
Normal imports of the full harness, real SDK request/response/error mapping;
no external HTTP during the checks, no model, corpus, score-policy change.
Fixture max_retries=0 deliberately exercises terminal outcomes, not retry timing.
The existing failure report and status-contract proposal remain their authors'.
Zero (ChatGPT), for Youngseok Oh / YS-OH-CORE, 2026-09-24.
"""
from __future__ import annotations
import argparse, asyncio, contextlib, difflib, hashlib, importlib, importlib.metadata
import io, json, os, socket, subprocess, sys
from pathlib import Path
from types import SimpleNamespace

TARGET='2cc8c540bdb87fe6761629b585e727e1c4704520'
BLOB='6a7182440a2cdd3ace6286dd966f7953fc383e8e'
OLD='''    outputs: dict[str, dict[str, Any]] = {}
    with tqdm(total=len(tasks), desc="Generating", unit="q") as progress:
        for task in asyncio.as_completed(tasks):
            question_id, output = await task
            outputs[question_id] = output
            progress.update(1)

    await client.close()
    return outputs'''
NEW='''    outputs: dict[str, dict[str, Any]] = {}
    try:
        with tqdm(total=len(tasks), desc="Generating", unit="q") as progress:
            for task in asyncio.as_completed(tasks):
                question_id, output = await task
                outputs[question_id] = output
                progress.update(1)
        return outputs
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await client.close()'''

async def observe(module, name):
    import httpx
    from openai import AsyncOpenAI
    ready=asyncio.Event(); blocker=asyncio.Event()
    state={'requests':0,'slow_cancelled':False}
    async def transport(request):
        state['requests']+=1
        marker=json.loads(request.content)['messages'][-1]['content']
        if name=='mixed' and marker=='slow':
            ready.set()
            try: await blocker.wait()
            except asyncio.CancelledError:
                state['slow_cancelled']=True
                raise
        if name=='mixed': await ready.wait()
        if name=='timeout': raise httpx.ReadTimeout('synthetic read timeout',request=request)
        if name in {'http400','http524','http429','mixed'}:
            status={'http400':400,'http524':524,'http429':429,'mixed':524}[name]
            # Embedded origin code is NOT the HTTP response status.
            return httpx.Response(status,json={'error':{'message':'synthetic origin 524',
                'type':'fixture_error','code':'origin_timeout'}},request=request)
        content='' if name=='empty200' else r'\boxed{OK}'
        return httpx.Response(200,json={'id':'fixture-response','object':'chat.completion',
            'created':1,'model':'fixture','choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':content}}],
            'usage':{'prompt_tokens':11,'completion_tokens':2,'total_tokens':13}},request=request)
    http=httpx.AsyncClient(transport=httpx.MockTransport(transport))
    client=AsyncOpenAI(api_key='fixture-not-a-credential',base_url='https://fixture.invalid/v1',
                       http_client=http,max_retries=0)
    original_factory=module.create_async_client
    module.create_async_client=lambda *args,**kwargs: client
    args=SimpleNamespace(reader_max_concurrent_requests=2,base_url='https://fixture.invalid/v1',
        api_key_env='ZERO_UNUSED_KEY',api_key_file=None,model='fixture',timeout_seconds=2,
        max_completion_tokens=20,reasoning_effort=None,temperature=None,top_p=None,
        presence_penalty=None,top_k=None,repetition_penalty=None,reader_enable_thinking=False)
    markers=['slow','fail'] if name=='mixed' else ['single']
    rows=[{'question_id':x,'messages':[{'role':'user','content':x}]} for x in markers]
    before=set(asyncio.all_tasks()); err=io.StringIO()
    result={'case':name,'output':None,'exception':None}
    try:
        with contextlib.redirect_stderr(err):
            try: result['output']=await asyncio.wait_for(module.generate_all_reader_outputs(args,rows),3)
            except Exception as exc: result['exception']=type(exc).__name__
        pending=[t for t in asyncio.all_tasks() if t not in before and not t.done()]
        result.update(client_closed_on_exit=http.is_closed,pending_child_tasks=len(pending),
                      slow_cancelled_on_exit=state['slow_cancelled'],requests=state['requests'],
                      stderr=err.getvalue())
        return result
    finally:
        # Test-owned cleanup follows measurement; it is not attributed to the baseline.
        pending=[t for t in asyncio.all_tasks() if t not in before and not t.done()]
        for task in pending: task.cancel()
        if pending: await asyncio.gather(*pending,return_exceptions=True)
        await client.close()
        module.create_async_client=original_factory

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();repo=a.repo.resolve();a.out.mkdir(parents=True,exist_ok=True)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    assert head==TARGET
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
    path=repo/'evaluation/harness.py';original=path.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest()==BLOB
    text=original.decode();assert text.count(OLD)==1
    candidate=text.replace(OLD,NEW)
    patch=''.join(difflib.unified_diff(text.splitlines(True),candidate.splitlines(True),
        fromfile='a/evaluation/harness.py',tofile='b/evaluation/harness.py'))
    (a.out/'cleanup-only.patch').write_text(patch)
    sys.path.insert(0,str(repo));module=importlib.import_module('evaluation.harness')
    assert Path(module.__file__).resolve()==path
    assert module.OPENAI_MAX_RETRIES==10
    report={'source_commit':TARGET,'source_blob':BLOB,
        'versions':{x:importlib.metadata.version(x) for x in ['openai','httpx','tqdm']},
        'fixture_max_retries':0,'upstream_retry_constant':10,'phases':{},'success':False,
        'scope':'Real imported harness + real SDK with simulated HTTP transport. Not full benchmark, live provider, retry-budget execution, or leaderboard-denominator validation.',
        'attribution':'Original #7 report: 100yenadmin. Existing status-contract proposal: chengyixu. New executable characterization/cleanup candidate: Zero (ChatGPT) for Youngseok Oh / YS-OH-CORE.'}
    old_connect=(socket.socket.connect,socket.socket.connect_ex)
    def block(*args,**kwargs): raise RuntimeError('Fixture forbids real socket connections')
    socket.socket.connect=socket.socket.connect_ex=block
    cases=['ok200','empty200','http400','http524','timeout','http429','mixed']
    try:
        for phase in ['baseline','cleanup_candidate']:
            if phase!='baseline':
                path.write_text(candidate);module=importlib.reload(module)
            report['phases'][phase]=[asyncio.run(observe(module,n)) for n in cases]
        b={r['case']:r for r in report['phases']['baseline']}
        c={r['case']:r for r in report['phases']['cleanup_candidate']}
        assert b['ok200']['output']['single']['response_raw']==r'\boxed{OK}'
        assert b['http400']['output']['single']['response_raw']==''
        assert 'reader_status' not in b['http400']['output']['single']
        assert b['http400']['output']['single']['usage']=={'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}
        for n,e in [('empty200','RuntimeError'),('http524','InternalServerError'),
                    ('timeout','APITimeoutError'),('http429','RateLimitError'),('mixed','InternalServerError')]:
            assert b[n]['exception']==e and b[n]['output'] is None and not b[n]['client_closed_on_exit'], b[n]
        assert b['mixed']['pending_child_tasks']==1 and not b['mixed']['slow_cancelled_on_exit']
        for n in cases:
            assert c[n]['exception']==b[n]['exception'] and c[n]['output']==b[n]['output'],n
            assert c[n]['client_closed_on_exit'] and c[n]['pending_child_tasks']==0,c[n]
            assert c[n]['requests']==b[n]['requests']==(2 if n=='mixed' else 1),n
        assert c['mixed']['slow_cancelled_on_exit']
        report['success']=True
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)[:1500]
    finally:
        socket.socket.connect,socket.socket.connect_ex=old_connect
        path.write_bytes(original)
        report['source_restored']=path.read_bytes()==original and not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
        (a.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('LME_READER_DIAGNOSTIC '+json.dumps(report,ensure_ascii=False),flush=True)
    return 0 if report['success'] and report['source_restored'] else 1

if __name__=='__main__':raise SystemExit(main())
