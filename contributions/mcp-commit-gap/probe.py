"""Inject abrupt client exit after real MCP completion, before graph checkpoint.

Linux stdio fixture, not an HTTP, power-loss, or real-human authorization test.
"""
from __future__ import annotations
import argparse
import asyncio
from copy import deepcopy
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import traceback
from receipt_store import ARGS, KEY, MODES, NOTE, ReceiptStore, canonical

PINS = {'langchain': '1.4.0', 'langchain-core': '1.6.2', 'langgraph': '1.2.11',
        'fastmcp': '4.0.1', 'mcp': '2.1.1', 'langgraph-checkpoint-sqlite': '3.1.1'}
GRAPH_BLOB = '8c1ec3585af66b47ab1744c1a621ca106fe34780'
EXIT_CODE = 73
NETWORK = []


def save(path: Path, value: dict):
    with path.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def emit(path: Path, value: dict):
    with path.open('a', encoding='utf-8') as f:
        f.write(canonical(value) + '\n')
        f.flush()
        os.fsync(f.fileno())


def audit(event, args):
    if event == 'socket.connect' and args[0].family in (socket.AF_INET, socket.AF_INET6):
        NETWORK.append(str(args[1]))
        raise RuntimeError('NO_IP_CONNECTIONS_IN_FIXTURE')


def metadata():
    here = Path(__file__).resolve().parent
    names = ['probe.py', 'receipt_store.py', '../preserved-mcp-rounds/round_graph.py',
             '../preserved-mcp-rounds/requirements.txt']
    packages = {k: md.version(k) for k in PINS}
    assert packages == PINS, packages
    return {'pid': os.getpid(), 'started_ns': time.monotonic_ns(), 'packages': packages,
            'python': sys.version, 'source_sha256': {name: hashlib.sha256((here / name).read_bytes()).hexdigest() for name in names}}


def answer():
    return {KEY: {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}}


async def server(root: Path, mode: str, phase: str):
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (CallToolResult, ElicitRequest, ElicitRequestFormParams,
                           InputRequiredResult, ListToolsResult, Tool)
    store = ReceiptStore(root / 'server.sqlite', mode)
    log = root / ('server-' + phase + '.jsonl')
    emit(log, {'event': 'start', **metadata()})
    async def list_tools(ctx, params):
        return ListToolsResult(tools=[Tool(name='preview', description='Synthetic local label only.',
            input_schema={'type': 'object', 'properties': {'label': {'type': 'string'}}, 'required': ['label']})])
    async def call_tool(ctx, params):
        assert params.name == 'preview'
        responses = {k: v.model_dump(mode='json', by_alias=True, exclude_none=True)
                     for k, v in (params.input_responses or {}).items()}
        if params.request_state is None:
            assert params.arguments == ARGS and not responses
            token = store.issue(params.arguments)
            result = InputRequiredResult(request_state=token, input_requests={KEY: ElicitRequest(
                params=ElicitRequestFormParams(mode='form', message='Preview draft-1? 한글 표본',
                    requested_schema={'type': 'object', 'properties': {'yes': {'type': 'boolean'},
                                      'note': {'type': 'string'}}, 'required': ['yes', 'note']}))})
            route = 'initial'
        else:
            body, route = store.complete(params.name, params.arguments, params.request_state, responses)
            result = CallToolResult.model_validate(body)
        emit(log, {'event': 'call', 'pid': os.getpid(), 'at_ns': time.monotonic_ns(),
            'name': params.name, 'arguments': params.arguments, 'request_state': params.request_state,
            'input_responses': responses, 'result': result.model_dump(mode='json', by_alias=True, exclude_none=True),
            'route': route, 'store': store.snapshot()})
        return result
    fixture = Server('commit-gap-fixture', on_list_tools=list_tools, on_call_tool=call_tool)
    try:
        async with stdio_server() as (read, write):
            await fixture.run(read, write, fixture.create_initialization_options())
    finally:
        emit(log, {'event': 'exit', 'pid': os.getpid(), 'at_ns': time.monotonic_ns(), 'network_attempts': NETWORK})


class RecordedSession:
    def __init__(self, session, root: Path, phase: str):
        self.session, self.root, self.phase, self.calls = session, root, phase, []
    async def call_tool(self, name, arguments, **kwargs):
        result = await self.session.call_tool(name, arguments, **kwargs)
        record = {'name': name, 'arguments': deepcopy(arguments), 'request_state': kwargs.get('request_state'),
            'input_responses': {k: v.model_dump(mode='json', by_alias=True, exclude_none=True)
                                for k, v in (kwargs.get('input_responses') or {}).items()},
            'result': result.model_dump(mode='json', by_alias=True, exclude_none=True)}
        self.calls.append(record)
        emit(self.root / ('wire-' + self.phase + '.jsonl'), record)
        if self.phase == 'crash':
            assert kwargs.get('request_state') is not None and not record['result'].get('isError', False)
            assert record['result']['structuredContent']['effect_id'] == 1
            save(self.root / 'crash-observed.json', {'pid': os.getpid(), 'at_ns': time.monotonic_ns(),
                 'exit_code': EXIT_CODE, 'network_attempts': NETWORK, 'call': record,
                 'point': 'reply received; returning to the graph and its checkpoint has not occurred'})
            os._exit(EXIT_CODE)
        return result


async def client(root: Path, mode: str, phase: str):
    from mcp import Client, StdioServerParameters
    from mcp.types import ElicitResult
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.types import Command
    graph_dir = Path(__file__).resolve().parent.parent / 'preserved-mcp-rounds'
    raw = (graph_dir / 'round_graph.py').read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == GRAPH_BLOB
    sys.path.insert(0, str(graph_dir))
    from round_graph import build_round_graph
    info = metadata()
    save(root / ('client-' + phase + '-start.json'), info)
    config = {'configurable': {'thread_id': 'gap-' + mode}}
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).resolve()), '--root', str(root), '--role', 'server', '--mode', mode, '--phase', phase],
        env={'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'})
    async with Client(params, cache=None, read_timeout_seconds=15) as connected:
        info['protocol'] = connected.session.protocol_version
        assert info['protocol'] == '2026-07-28'
        catalog = await connected.list_tools()
        assert [tool.name for tool in catalog.tools] == ['preview']
        wire = RecordedSession(connected.session, root, phase)
        async with AsyncSqliteSaver.from_conn_string(str(root / 'client.sqlite')) as saver:
            graph = build_round_graph(wire, saver)
            if phase == 'prepare':
                result = await graph.ainvoke({'tool_name': 'preview', 'arguments': ARGS}, config, durability='sync')
                assert len(result['__interrupt__']) == 1
                info['shown'] = deepcopy(result['__interrupt__'][0].value)
            elif phase == 'crash':
                await graph.ainvoke(Command(resume={'responses': answer()}), config, durability='sync')
                raise AssertionError('INJECTED_EXIT_DID_NOT_HAPPEN')
            else:
                before = await graph.aget_state(config)
                info['before'] = {'values': deepcopy(before.values), 'next': list(before.next)}
                save(root / 'reopened-before-recovery.json', info['before'])
                assert before.values['status'] == 'answered'
                assert before.next == ('continue_original_round',)
                assert 'result' not in before.values
                assert before.values['answers'] == answer()
                result = await graph.ainvoke(None, config, durability='sync')
                assert not result.get('__interrupt__')
                info['result'], info['status'] = result['result'], result['status']
            after = await graph.aget_state(config)
            info['after'] = {'values': deepcopy(after.values), 'next': list(after.next)}
        if phase == 'recover' and mode == 'receipt':
            changed = answer()
            changed[KEY]['content']['note'] += 'changed'
            token = info['before']['values']['frame']['value']['requestState']
            rejected = await wire.call_tool('preview', ARGS, request_state=token,
                input_responses={k: ElicitResult.model_validate(v) for k, v in changed.items()}, allow_input_required=True)
            info['changed_answer_result'] = rejected.model_dump(mode='json', by_alias=True, exclude_none=True)
        info['calls'] = wire.calls
    info['network_attempts'] = NETWORK
    assert not NETWORK
    save(root / ('client-' + phase + '.json'), info)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check(root: Path, mode: str, process_order: list[dict]):
    prep, recovered = [read_json(root / ('client-' + p + '.json')) for p in ('prepare', 'recover')]
    crashed = read_json(root / 'crash-observed.json')
    after_crash = read_json(root / 'parent-after-crash.json')
    logs = [[json.loads(x) for x in (root / ('server-' + p + '.jsonl')).read_text().splitlines()]
            for p in ('prepare', 'crash', 'recover')]
    starts = [read_json(root / ('client-' + p + '-start.json')) for p in ('prepare', 'crash', 'recover')]
    pids = [x['pid'] for x in starts] + [log[0]['pid'] for log in logs]
    assert len(set(pids)) == 6
    assert [p['returncode'] for p in process_order] == [0, EXIT_CODE, 0]
    for i, (start, log) in enumerate(zip(starts, logs)):
        assert log[0]['event'] == 'start' and log[-1]['event'] == 'exit'
        assert start['started_ns'] < log[0]['started_ns'] < log[-1]['at_ns'] < process_order[i]['finished_ns']
        assert log[0]['source_sha256'] == start['source_sha256'] == starts[0]['source_sha256']
        assert log[0]['packages'] == start['packages'] == PINS
        assert not log[-1]['network_attempts']
        if i:
            assert process_order[i - 1]['finished_ns'] < start['started_ns']
    calls = prep['calls'] + [crashed['call']] + recovered['calls']
    server_calls = [x for log in logs for x in log if x['event'] == 'call']
    assert len(calls) == len(server_calls) == (4 if mode == 'receipt' else 3)
    stamp = {'io.modelcontextprotocol/serverInfo': {'name': 'commit-gap-fixture', 'version': ''}}
    for a, b in zip(calls, server_calls):
        for key in ('name', 'arguments', 'request_state', 'input_responses'):
            assert canonical(a[key]) == canonical(b[key])
        assert a['result']['_meta'] == stamp
        assert {k: v for k, v in a['result'].items() if k != '_meta'} == b['result']
    token = prep['after']['values']['frame']['value']['requestState']
    assert token not in canonical(prep['shown'])
    assert recovered['before']['values']['frame'] == prep['after']['values']['frame']
    assert calls[0]['request_state'] is None and all(x['request_state'] == token for x in calls[1:])
    assert canonical(calls[1]['input_responses']) == canonical(calls[2]['input_responses']) == canonical(answer())
    assert server_calls[1]['at_ns'] < crashed['at_ns'] < process_order[1]['finished_ns']
    assert len(after_crash['store']['effects']) == 1
    assert server_calls[1]['store'] == after_crash['store']
    assert not crashed['network_attempts']
    assert recovered['after']['next'] == []
    final = ReceiptStore(root / 'server.sqlite', mode).snapshot()
    expected_count = 2 if mode == 'naive' else 1
    assert len(final['effects']) == expected_count
    original_result, resumed_result = calls[1]['result'], recovered['result']
    assert resumed_result == calls[2]['result'] == recovered['after']['values']['result']
    if mode == 'naive':
        assert resumed_result['structuredContent']['effect_id'] == 2 and resumed_result != original_result
        assert recovered['status'] == 'completed'
    elif mode == 'closed_guard':
        assert resumed_result['isError'] is True and resumed_result['content'][0]['text'] == 'ROUND_ALREADY_CLOSED'
        assert recovered['status'] == 'tool_error'
    else:
        assert resumed_result == original_result and recovered['status'] == 'completed'
        assert server_calls[2]['route'] == 'receipt_replayed'
        assert recovered['changed_answer_result']['isError'] is True
        assert recovered['changed_answer_result']['content'][0]['text'] == 'REQUEST_BINDING_DIFFER'
        assert final == after_crash['store']
    return {'mode': mode, 'effects_after_crash': 1, 'effects_after_recovery': expected_count,
            'same_original_result': original_result == resumed_result, 'status': recovered['status'],
            'tool_calls': len(calls), 'pids': pids, 'process_order': process_order, 'final_store': final}


def run(root: Path):
    root.mkdir(parents=True, exist_ok=False)
    report = {'status': 'incomplete', 'cases': [], 'scope': 'Real stdio; injected os._exit(73) after reply, before graph checkpoint. Local SQLite labels only; no power loss, HTTP, live authorization, or general exactly-once claim.'}
    try:
        for mode in MODES:
            case = root / mode
            case.mkdir()
            order = []
            for phase in ('prepare', 'crash', 'recover'):
                with (case / ('process-' + phase + '.log')).open('wb') as log:
                    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--root', str(case),
                        '--role', 'client', '--mode', mode, '--phase', phase], stdout=log,
                        stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        rc = proc.wait(timeout=40)
                        assert rc == (EXIT_CODE if phase == 'crash' else 0), (mode, phase, rc)
                        server_log = case / ('server-' + phase + '.jsonl')
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            rows = server_log.read_text().splitlines() if server_log.exists() else []
                            if rows and json.loads(rows[-1]).get('event') == 'exit':
                                break
                            time.sleep(0.05)
                        else:
                            raise AssertionError('SERVER_DID_NOT_EXIT')
                    except BaseException:
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        proc.wait(timeout=5)
                        raise
                order.append({'phase': phase, 'client_pid': proc.pid, 'returncode': rc, 'finished_ns': time.monotonic_ns()})
                save(case / 'process-order.json', {'processes': order})
                if phase == 'crash':
                    save(case / 'parent-after-crash.json', {'store': ReceiptStore(case / 'server.sqlite', mode).snapshot()})
            report['cases'].append(check(case, mode, order))
        report['status'] = 'verified'
    except BaseException as exc:
        report.update(status='failed', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        save(root / 'observations.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Probe assertions must be enabled')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--role', choices=('client', 'server'))
    p.add_argument('--mode', choices=MODES)
    p.add_argument('--phase', choices=('prepare', 'crash', 'recover'))
    a = p.parse_args()
    if a.role:
        if not a.mode or not a.phase:
            p.error('--role requires --mode and --phase')
        sys.addaudithook(audit)
        asyncio.run(server(a.root, a.mode, a.phase) if a.role == 'server' else client(a.root, a.mode, a.phase))
    else:
        run(a.root.resolve())
