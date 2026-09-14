"""Actual MCP stdio across fresh client/server processes; synthetic effects only.

The original saved-round graph is used unchanged. This is not an HTTP, crash,
authentication, live-consent, or exactly-once remote-effect demonstration.
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
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import traceback

KEY = 'confirm-preview'
NOTE = '  원래 질문의 답\n    keep whitespace\n'
CASES = ('preserved', 'lost_server_state', 'replayed_initial', 'declined')
PINS = {'langchain': '1.4.0', 'langchain-core': '1.6.2', 'langgraph': '1.2.11',
        'fastmcp': '4.0.1', 'mcp': '2.1.1', 'langgraph-checkpoint-sqlite': '3.1.1'}
GRAPH_BLOB = '8c1ec3585af66b47ab1744c1a621ca106fe34780'
NETWORK_ATTEMPTS: list[str] = []


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def audit(event, args):
    if event == 'socket.connect' and args[0].family in (socket.AF_INET, socket.AF_INET6):
        NETWORK_ATTEMPTS.append(str(args[1]))
        raise RuntimeError('NO_IP_CONNECTIONS_IN_STDIO_EXERCISE')


def metadata() -> dict:
    versions = {key: md.version(key) for key in PINS}
    assert versions == PINS, versions
    return {'pid': os.getpid(), 'monotonic_ns': time.monotonic_ns(), 'python': sys.version,
            'versions': versions, 'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


class RoundStore:
    """Fixture state and harmless labels in one private, local SQLite database."""
    def __init__(self, path: Path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS rounds (id INTEGER PRIMARY KEY, token TEXT UNIQUE, status TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS effects (token TEXT UNIQUE, subject TEXT)')

    def issue(self) -> tuple[str, str]:
        token = 'fixture-' + secrets.token_hex(16)
        with sqlite3.connect(self.path) as db:
            row = db.execute('INSERT INTO rounds(token,status) VALUES (?,?)', (token, 'pending'))
            return token, 'draft-' + str(row.lastrowid)

    def answer(self, token: str, responses: dict) -> tuple[str, bool]:
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT id,status FROM rounds WHERE token=?', (token,)).fetchone()
            if row is None: return 'UNKNOWN_ROUND', True
            if row[1] != 'pending': return 'ROUND_ALREADY_CLOSED', True
            if set(responses) != {KEY}: return 'ANSWER_KEYS_DIFFER', True
            answer = responses[KEY]
            action, content = answer.get('action'), answer.get('content')
            if action not in ('accept', 'decline', 'cancel'): return 'ANSWER_ACTION', True
            if action != 'accept' and content is not None: return 'CONTENT_WITHOUT_ACCEPT', True
            if action == 'accept' and (not isinstance(content, dict) or set(content) != {'yes', 'note'}
                                      or content['yes'] is not True or content['note'] != NOTE):
                return 'FORM_CONTENT_DIFFER', True
            db.execute('UPDATE rounds SET status=? WHERE token=?', (action, token))
            if action != 'accept': return 'skipped:' + action, False
            subject = 'draft-' + str(row[0])
            db.execute('INSERT INTO effects VALUES (?,?)', (token, subject))
            return 'previewed:' + subject, False

    def snapshot(self) -> dict:
        with sqlite3.connect(self.path) as db:
            return {'rounds': [list(x) for x in db.execute('SELECT id,token,status FROM rounds ORDER BY id')],
                    'effects': [list(x) for x in db.execute('SELECT token,subject FROM effects ORDER BY rowid')]}


async def serve(root: Path, phase: str, case: str) -> None:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (CallToolResult, ElicitRequest, ElicitRequestFormParams,
                           InputRequiredResult, ListToolsResult, TextContent, Tool)
    store = RoundStore(root / ('empty-server.sqlite' if case == 'lost_server_state' and phase == 'b' else 'server.sqlite'))
    log = root / ('server-' + phase + '.jsonl')
    def emit(data):
        with log.open('a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    emit({'event': 'start', **metadata()})

    async def list_tools(ctx, params):
        return ListToolsResult(tools=[Tool(name='preview', description='Record a synthetic draft label after form review.',
            input_schema={'type': 'object', 'properties': {'case': {'type': 'string'}}, 'required': ['case']})])

    async def call_tool(ctx, params):
        assert params.name == 'preview' and params.arguments == {'case': case}
        responses = {k: v.model_dump(mode='json', by_alias=True, exclude_none=True)
                     for k, v in (params.input_responses or {}).items()}
        entry = {'event': 'call', 'pid': os.getpid(), 'name': params.name, 'arguments': params.arguments,
                 'request_state': params.request_state, 'input_responses': responses}
        if params.request_state is None:
            assert not responses
            token, subject = store.issue()
            result = InputRequiredResult(request_state=token, input_requests={KEY: ElicitRequest(
                params=ElicitRequestFormParams(mode='form', message=f'Preview {subject}? 한글 표본',
                    requested_schema={'type': 'object', 'properties': {'yes': {'type': 'boolean'},
                        'note': {'type': 'string'}}, 'required': ['yes', 'note']}))})
        else:
            text, error = store.answer(params.request_state, responses)
            result = CallToolResult(content=[TextContent(type='text', text=text)], is_error=error)
        entry.update(result=result.model_dump(mode='json', by_alias=True, exclude_none=True), snapshot=store.snapshot())
        emit(entry)
        return result

    server = Server('stdio-round-restart-fixture', on_list_tools=list_tools, on_call_tool=call_tool)
    try:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    finally:
        emit({'event': 'exit', 'pid': os.getpid(), 'monotonic_ns': time.monotonic_ns(),
              'network_attempts': list(NETWORK_ATTEMPTS)})


class Recorder:
    """Delegates each call to the actual SDK session, not to a session double."""
    def __init__(self, session): self.session, self.calls = session, []
    async def call_tool(self, name, arguments, **kwargs):
        row = {'name': name, 'arguments': deepcopy(arguments), 'request_state': kwargs.get('request_state'),
               'input_responses': {k: v.model_dump(mode='json', by_alias=True, exclude_none=True)
                                   for k, v in (kwargs.get('input_responses') or {}).items()}}
        self.calls.append(row)
        result = await self.session.call_tool(name, arguments, **kwargs)
        row['result'] = result.model_dump(mode='json', by_alias=True, exclude_none=True)
        return result


async def client_phase(root: Path, phase: str, case: str) -> None:
    from mcp import Client, StdioServerParameters
    from mcp.types import ElicitResult, InputRequiredResult
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.types import Command
    graph_dir = Path(__file__).resolve().parent.parent / 'preserved-mcp-rounds'
    raw = (graph_dir / 'round_graph.py').read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == GRAPH_BLOB
    sys.path.insert(0, str(graph_dir))
    from round_graph import build_round_graph
    observed = metadata()
    observed['graph_sha256'] = hashlib.sha256(raw).hexdigest()
    cfg = {'configurable': {'thread_id': 'stdio-' + case}}
    old = json.loads((root / 'client-a.json').read_text(encoding='utf-8')) if phase == 'b' else None
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).resolve()), '--role', 'server', '--root', str(root), '--phase', phase, '--case', case],
        env={'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'})
    async with Client(params, cache=None, read_timeout_seconds=20) as client:
        observed['protocol_version'] = client.session.protocol_version
        assert observed['protocol_version'] == '2026-07-28'
        catalog = await client.list_tools()
        assert [x.name for x in catalog.tools] == ['preview']
        observed['catalog'] = catalog.model_dump(mode='json', by_alias=True, exclude_none=True)
        wire = Recorder(client.session)
        async with AsyncSqliteSaver.from_conn_string(str(root / 'client.sqlite')) as saver:
            graph = build_round_graph(wire, saver)
            if phase == 'a':
                result = await graph.ainvoke({'tool_name': 'preview', 'arguments': {'case': case}}, cfg, durability='sync')
                assert len(result['__interrupt__']) == 1
                observed['shown'] = deepcopy(result['__interrupt__'][0].value)
                snapshot = await graph.aget_state(cfg)
                observed['frame'] = deepcopy(snapshot.values['frame'])
                assert observed['frame']['value']['requestState'] not in json.dumps(observed['shown'])
            else:
                snapshot = await graph.aget_state(cfg)
                observed['reopened_frame'] = deepcopy(snapshot.values['frame'])
                assert observed['reopened_frame'] == old['frame']
                decision = {'action': 'decline'} if case == 'declined' else {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}
                answer = {'responses': {old['shown']['requests'][0]['key']: decision}}
                observed['supplied_answer'] = deepcopy(answer)
                if case == 'replayed_initial':
                    # Deliberately wrong application control: regenerate a question,
                    # then attach the earlier answer using the same stable key.
                    replacement = await wire.call_tool('preview', {'case': case}, allow_input_required=True)
                    assert isinstance(replacement, InputRequiredResult)
                    observed['replacement_question'] = replacement.model_dump(mode='json', by_alias=True, exclude_none=True)
                    terminal = await wire.call_tool('preview', {'case': case}, request_state=replacement.request_state,
                        input_responses={k: ElicitResult.model_validate(v) for k, v in answer['responses'].items()},
                        allow_input_required=True)
                    observed.update(status='naive_control_returned', result=terminal.model_dump(mode='json', by_alias=True, exclude_none=True))
                else:
                    result = await graph.ainvoke(Command(resume=answer), cfg, durability='sync')
                    assert not result.get('__interrupt__')
                    observed.update(status=result['status'], result=result['result'])
        observed['calls'] = wire.calls
    observed['network_attempts'] = list(NETWORK_ATTEMPTS)
    assert not NETWORK_ATTEMPTS
    save(root / ('client-' + phase + '.json'), observed)


def compare_results(received: dict, handler_result: dict) -> None:
    """Validate the SDK-added identity stamp, then compare every body field.

    Handler observations precede the SDK runtime's serverInfo stamping. Keep
    both originals in evidence; do not silently discard arbitrary metadata.
    """
    expected = {'io.modelcontextprotocol/serverInfo': {'name': 'stdio-round-restart-fixture', 'version': ''}}
    assert '_meta' not in handler_result, 'UNEXPECTED_HANDLER_METADATA'
    assert received.get('_meta') == expected, 'SERVER_IDENTITY_STAMP_DIFFER'
    body = {key: value for key, value in received.items() if key != '_meta'}
    assert body == handler_result, 'RESULT_BODY_DIFFER'


def check_case(root: Path, case: str, exit_a: int, returncodes: list[int]) -> dict:
    a, b = [json.loads((root / ('client-' + p + '.json')).read_text(encoding='utf-8')) for p in ('a', 'b')]
    logs = [[json.loads(line) for line in (root / ('server-' + p + '.jsonl')).read_text(encoding='utf-8').splitlines()] for p in ('a', 'b')]
    assert a['pid'] != b['pid'] and a['monotonic_ns'] < exit_a < b['monotonic_ns']
    assert len({a['pid'], b['pid'], logs[0][0]['pid'], logs[1][0]['pid']}) == 4
    for log in logs:
        assert log[0]['event'] == 'start' and log[-1]['event'] == 'exit'
        assert not log[-1]['network_attempts']
    assert logs[0][-1]['monotonic_ns'] < exit_a
    assert not a['network_attempts'] and not b['network_attempts']
    assert logs[1][0]['monotonic_ns'] > exit_a
    assert a['probe_sha256'] == b['probe_sha256'] == logs[0][0]['probe_sha256'] == logs[1][0]['probe_sha256']
    assert a['versions'] == b['versions'] == logs[0][0]['versions'] == logs[1][0]['versions'] == PINS
    assert a['frame'] == b['reopened_frame']
    assert len(a['calls']) == 1 and a['calls'][0]['request_state'] is None
    assert a['calls'][0]['result'] == a['frame']['value']
    token = a['frame']['value']['requestState']
    calls = [x for log in logs for x in log if x['event'] == 'call']
    for client_call, server_call in zip(a['calls'] + b['calls'], calls, strict=True):
        assert all(client_call[k] == server_call[k] for k in ('name', 'arguments', 'request_state', 'input_responses')), 'REQUEST_FIELDS_DIFFER'
        compare_results(client_call['result'], server_call['result'])
    text = b['result']['content'][0]['text']
    error = b['result'].get('isError', False)
    effects = calls[-1]['snapshot']['effects']
    if case == 'replayed_initial':
        assert len(b['calls']) == 2 and b['calls'][0]['request_state'] is None
        assert b['calls'][1]['request_state'] != token
        assert b['calls'][1]['request_state'] == b['replacement_question']['requestState']
        assert 'draft-1' in a['shown']['requests'][0]['message']
        assert 'draft-2' in b['replacement_question']['inputRequests'][KEY]['params']['message']
        assert text == 'previewed:draft-2' and error is False and len(effects) == 1
        assert effects[0][1] == 'draft-2'
    else:
        assert len(b['calls']) == 1 and b['calls'][0]['request_state'] == token
        assert b['calls'][0]['input_responses'] == b['supplied_answer']['responses']
        expected = {'preserved': ('previewed:draft-1', False, 1),
                    'lost_server_state': ('UNKNOWN_ROUND', True, 0), 'declined': ('skipped:decline', False, 0)}[case]
        assert (text, error, len(effects)) == expected
        assert b['status'] == ('tool_error' if error else 'completed')
        if effects: assert effects == [[token, 'draft-1']]
    assert returncodes == [0, 0]
    return {'case': case, 'client_a': a, 'client_b': b, 'server_logs': logs,
            'a_exited_monotonic_ns': exit_a, 'returncodes': returncodes, 'verified': True}


def run(root: Path):
    root.mkdir(parents=True, exist_ok=False)
    report = {'status': 'incomplete', 'cases': [], 'boundary': 'Real MCP stdio and new client/server processes; synthetic labels and programmed answers. No HTTP, injected crash, live consent, authorization, or exactly-once remote-effect claim.'}
    try:
        for case in CASES:
            case_root = root / case
            case_root.mkdir()
            codes = []
            for phase in ('a', 'b'):
                with (case_root / ('process-' + phase + '.log')).open('wb') as log:
                    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--role', 'client',
                        '--root', str(case_root), '--phase', phase, '--case', case], stdout=log,
                        stderr=subprocess.STDOUT, timeout=65, check=True)
                codes.append(proc.returncode)
                if phase == 'a': exit_a = time.monotonic_ns()
            save(case_root / 'process-order.json', {'a_exited_monotonic_ns': exit_a, 'returncodes': codes})
            report['cases'].append(check_case(case_root, case, exit_a, codes))
        report['status'] = 'verified'
    except Exception as exc:
        report.update(status='failed', error=type(exc).__name__ + ': ' + str(exc), traceback=traceback.format_exc())
        raise
    finally:
        save(root / 'observations.json', report)
    print(json.dumps({'status': report['status'], 'cases': [x['case'] for x in report['cases']]}, indent=2))


if __name__ == '__main__':
    if not __debug__: raise RuntimeError('Assertions must be enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--role', choices=('client', 'server'))
    parser.add_argument('--phase', choices=('a', 'b'))
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    if args.role:
        if not args.phase or not args.case: parser.error('--role requires --phase and --case')
        sys.addaudithook(audit)
        asyncio.run(serve(args.root, args.phase, args.case) if args.role == 'server' else client_phase(args.root, args.phase, args.case))
    else:
        run(args.root.resolve())
