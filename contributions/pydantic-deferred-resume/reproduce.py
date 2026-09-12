"""Reproduce pydantic/pydantic-ai#8181 across actual process boundaries.

Run after installing pydantic-ai-slim[ui]==2.43.0. No upstream edits, provider
credentials or remote model: FunctionModel is a deterministic local test double.
The two resume branches load the same immutable, synthetic persisted history.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

VERSION = '2.43.0'
ANSWER = {'answer': '  첫 번째\n    keep indentation\n'}
CALL_ID = 'synthetic-call-8181'


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def child(mode, root):
    from pydantic import TypeAdapter
    from pydantic_ai import Agent, CallDeferred, DeferredToolRequests, DeferredToolResults
    from pydantic_ai import models
    from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
    from pydantic_ai.models.function import FunctionModel, DeltaToolCall
    from pydantic_ai.ui.vercel_ai import VercelAIAdapter
    from pydantic_ai.ui.vercel_ai.request_types import RequestData
    from pydantic_ai.usage import UsageLimits

    assert importlib.metadata.version('pydantic-ai-slim') == VERSION
    models.ALLOW_MODEL_REQUESTS = False
    connections = []
    original_connect = socket.socket.connect
    def forbid_network(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            connections.append(repr(address))
            raise RuntimeError('Network disabled for this synthetic reproduction')
        return original_connect(sock, address)
    socket.socket.connect = forbid_network
    counts = {'tool_body': 0, 'function_model': 0}
    received = []
    def answer_from(messages):
        returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart) and p.tool_call_id == CALL_ID]
        if returns:
            received.append(returns[-1].content)
            return json.dumps(returns[-1].content, ensure_ascii=False)
        return None
    async def respond(messages, info):
        counts['function_model'] += 1
        value = answer_from(messages)
        return ModelResponse([TextPart(value)]) if value is not None else ModelResponse([ToolCallPart('ask', {}, tool_call_id=CALL_ID)])
    async def stream(messages, info):
        counts['function_model'] += 1
        value = answer_from(messages)
        if value is not None:
            yield value
        else:
            yield {0: DeltaToolCall(name='ask', json_args='{}', tool_call_id=CALL_ID)}
    agent = Agent(FunctionModel(respond, stream_function=stream), output_type=[str, DeferredToolRequests])
    @agent.tool_plain
    def ask() -> str:
        """Return an externally supplied choice, after resumption."""
        counts['tool_body'] += 1
        raise CallDeferred
    result = {'mode':mode, 'pid':os.getpid(), 'version':VERSION}
    history_path = root/'history.json'
    if mode == 'prepare':
        run = agent.run_sync('Choose an option.', usage_limits=UsageLimits(request_limit=3))
        assert isinstance(run.output, DeferredToolRequests)
        assert [c.tool_call_id for c in run.output.calls] == [CALL_ID]
        history_path.write_bytes(ModelMessagesTypeAdapter.dump_json(run.all_messages()))
        wire = {'id':'synthetic-chat-8181','trigger':'submit-message','messages':[
            {'id':'u1','role':'user','parts':[{'type':'text','text':'Choose an option.'}]},
            {'id':'a1','role':'assistant','parts':[{'type':'tool-ask','toolCallId':CALL_ID,
                'state':'output-available','input':{},'output':ANSWER}]}]}
        write(root/'request.json',wire)
        result.update(status='deferred', pending_calls=[CALL_ID])
    else:
        stored = history_path.read_bytes()
        history = ModelMessagesTypeAdapter.validate_json(stored)
        wire = json.loads((root/'request.json').read_text(encoding='utf-8'))
        run_input = TypeAdapter(RequestData).validate_python(wire)
        adapter = VercelAIAdapter(agent=agent, run_input=run_input, sdk_version=7)
        # Inspect conversion without populating adapter.messages' cached_property.
        converted = VercelAIAdapter.load_messages(run_input.messages)
        loaded_returns = [p.content for m in converted for p in m.parts if isinstance(p, ToolReturnPart) and p.tool_call_id == CALL_ID]
        extracted = adapter.deferred_tool_results  # Read BEFORE messages are emptied.
        assert loaded_returns == [ANSWER]
        assert extracted is None
        result.update(frontend_result_survives_load_messages=True, adapter_extracted_results=None)
        supplied = DeferredToolResults(calls={CALL_ID: wire['messages'][1]['parts'][0]['output']}) if mode == 'explicit' else extracted
        run_input.messages = []
        assert adapter.messages == []
        events_seen, final = [], []
        async def consume():
            async for event in adapter.run_stream_native(message_history=history, deferred_tool_results=supplied,
                                                        usage_limits=UsageLimits(request_limit=3)):
                events_seen.append(type(event).__name__)
                if hasattr(event, 'result') and hasattr(event.result, 'output'):
                    final.append(event.result.output)
        try:
            asyncio.run(consume())
        except Exception as exc:
            result.update(status='exception', exception_type=type(exc).__name__, exception=str(exc))
        else:
            assert len(final) == 1, (events_seen, final)
            if isinstance(final[0], DeferredToolRequests):
                result.update(status='deferred_again', pending_calls=[c.tool_call_id for c in final[0].calls])
            else:
                result.update(status='completed', output=final[0], exact_answer=json.loads(final[0]) == ANSWER)
        result.update(events=events_seen, persisted_history_unchanged=history_path.read_bytes() == stored)
    result.update(counts=counts, received_tool_results=received, attempted_network_connections=connections,
                  history_sha256=hashlib.sha256(history_path.read_bytes()).hexdigest())
    write(root/(mode+'.json'), result)
    assert not connections
    return result


def main(root):
    root.mkdir(parents=True, exist_ok=False)
    env = {k:os.environ[k] for k in ('PATH','SYSTEMROOT','TMPDIR','TEMP','TMP','LANG') if k in os.environ}
    env.update(HOME=str(root/'home'), PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', OTEL_SDK_DISABLED='true')
    (root/'home').mkdir()
    results = {}
    for mode in ('prepare','adapter','explicit'):
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--out', str(root), '--stage', mode],
                              env=env, capture_output=True, text=True, timeout=60)
        (root/(mode+'.log')).write_text(proc.stdout+'\n'+proc.stderr, encoding='utf-8')
        assert proc.returncode == 0, mode+': '+proc.stderr
        results[mode] = json.loads((root/(mode+'.json')).read_text(encoding='utf-8'))
    write(root/'observations.json', results)  # Keep observations even if a following expectation fails.
    assert len({r['pid'] for r in results.values()}) == 3
    assert len({r['history_sha256'] for r in results.values()}) == 1
    assert results['prepare']['counts']['tool_body'] == 1
    assert results['adapter']['status'] != 'completed'
    if results['adapter']['status'] == 'exception':
        assert results['adapter']['exception_type'] in ('UserError','UnexpectedModelBehavior')
    assert results['adapter']['received_tool_results'] == []
    assert results['explicit']['status'] == 'completed' and results['explicit']['exact_answer']
    assert results['explicit']['counts']['tool_body'] == 0
    assert results['explicit']['received_tool_results'] == [ANSWER]
    assert results['adapter']['persisted_history_unchanged'] and results['explicit']['persisted_history_unchanged']
    write(root/'summary.json', {'status':'reproduced_with_explicit_result_control','version':VERSION,
        'issue':'https://github.com/pydantic/pydantic-ai/issues/8181','results':results,
        'limits':['FunctionModel is a deterministic test double, not a remote language model.',
                  'Real Python agent, Vercel adapter and JSON persistence; no HTTP frontend server or user data.',
                  'Explicit calls is a single-known-pending-call control, not a proposed generic client-trust adapter.',
                  'No upstream fix or fresh incident is claimed. This extends the original report.']})
    print(json.dumps({m:{'status':r['status'],'counts':r['counts']} for m,r in results.items()},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--stage',choices=['prepare','adapter','explicit'])
    args = parser.parse_args()
    child(args.stage,args.out.resolve()) if args.stage else main(args.out.resolve())
