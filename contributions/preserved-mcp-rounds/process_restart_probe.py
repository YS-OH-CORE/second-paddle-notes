"""Verify a saved form round across two sequential Python interpreters.

The session is a deterministic test double, not an MCP transport. Process A
saves one question and exits cleanly; process B reopens the SQLite checkpoint.
Only the existing graph and SQLite saver implement persistence. No operating-
system crash, live authorization, remote effect, or exactly-once claim is made.
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
import socket
import subprocess
import sys
import time

from round_graph import build_round_graph

TOKEN = 'opaque-process-A-state'
KEY = 'confirm-process-A'
NOTE = 'answer after a fresh interpreter'
PINS = {'langchain': '1.4.0', 'langchain-core': '1.6.2', 'langgraph': '1.2.11',
        'fastmcp': '4.0.1', 'mcp': '2.1.1', 'langgraph-checkpoint-sqlite': '3.1.1'}
NETWORK_ATTEMPTS: list[str] = []


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def process_metadata(started_ns: int) -> dict:
    packages = {name: md.version(name) for name in PINS}
    assert packages == PINS, packages
    files = ('process_restart_probe.py', 'round_graph.py', 'requirements.txt')
    return {'pid': os.getpid(), 'started_monotonic_ns': started_ns,
            'python': sys.version, 'packages': packages,
            'source_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                              for name in files},
            'network_attempts': list(NETWORK_ATTEMPTS)}


def block_external_network(event, args):
    if event == 'socket.connect' and args[0].family in (socket.AF_INET, socket.AF_INET6):
        NETWORK_ATTEMPTS.append(str(args[1]))
        raise RuntimeError('NO_NETWORK_IN_SYNTHETIC_EXERCISE')


def question():
    from mcp.types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult
    schema = {'type': 'object', 'properties': {'yes': {'type': 'boolean'}, 'note': {'type': 'string'}},
              'required': ['yes', 'note']}
    return InputRequiredResult(
        input_requests={KEY: ElicitRequest(method='elicitation/create', params=ElicitRequestFormParams(
            mode='form', message='Keep the process-A question?', requested_schema=schema))},
        request_state=TOKEN,
    )


class PhaseOneSession:
    def __init__(self): self.calls = []
    async def call_tool(self, name, arguments, **kwargs):
        assert name == 'preview' and arguments == {'case': 'restart'}
        assert kwargs.get('request_state') is None
        self.calls.append({'kind': 'initial', 'name': name, 'arguments': deepcopy(arguments)})
        return question()


class PhaseTwoSession:
    def __init__(self): self.calls = []
    async def call_tool(self, name, arguments, **kwargs):
        from mcp.types import CallToolResult, TextContent
        assert name == 'preview' and arguments == {'case': 'restart'}
        state = kwargs.get('request_state')
        responses = kwargs.get('input_responses') or {}
        # A regenerated initial call cannot satisfy these checks.
        assert state == TOKEN, state
        assert set(responses) == {KEY}, set(responses)
        answer = responses[KEY]
        assert answer.action == 'accept'
        assert answer.content == {'yes': True, 'note': NOTE}
        self.calls.append({'kind': 'resume', 'name': name, 'arguments': deepcopy(arguments),
                           'state': state, 'keys': list(responses),
                           'answer': answer.model_dump(mode='json', by_alias=True, exclude_none=True)})
        return CallToolResult(content=[TextContent(type='text', text='completed-from-process-B')])


async def phase_one(db: Path, evidence: Path):
    started = time.monotonic_ns()
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    session = PhaseOneSession()
    config = {'configurable': {'thread_id': 'process-restart'}}
    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        graph = build_round_graph(session, saver)
        result = await graph.ainvoke({'tool_name': 'preview', 'arguments': {'case': 'restart'}}, config,
                                     durability='sync')
        assert len(result['__interrupt__']) == 1
        shown = result['__interrupt__'][0].value
        assert shown['requests'][0]['key'] == KEY
        assert TOKEN not in json.dumps(shown)
        state = await graph.aget_state(config)
        frame = deepcopy(state.values['frame'])
        assert frame['value']['requestState'] == TOKEN
    assert not NETWORK_ATTEMPTS
    write_json(evidence, {'status': 'phase_one_saved', 'phase_one_calls': session.calls,
                         'shown': shown, 'saved_frame': frame, 'phase_one': process_metadata(started)})


async def phase_two(db: Path, evidence: Path):
    started = time.monotonic_ns()
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.types import Command
    assert db.is_file() and db.stat().st_size > 0, 'CHECKPOINT_REQUIRED'
    old = json.loads(evidence.read_text(encoding='utf-8'))
    session = PhaseTwoSession()
    config = {'configurable': {'thread_id': 'process-restart'}}
    # The answer is a programmed fixture to the displayed key, not human consent.
    answer = {'responses': {old['shown']['requests'][0]['key']:
                           {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}}}
    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        graph = build_round_graph(session, saver)
        before = await graph.aget_state(config)
        frame = deepcopy(before.values['frame'])
        assert frame == old['saved_frame']
        assert frame['value']['requestState'] == TOKEN
        result = await graph.ainvoke(Command(resume=answer), config, durability='sync')
        assert result['status'] == 'completed'
        assert not result.get('__interrupt__')
        assert result['result']['content'] == [{'type': 'text', 'text': 'completed-from-process-B'}]
        assert not result['result'].get('isError', False)
    assert not NETWORK_ATTEMPTS
    old.update(phase_two_calls=session.calls, reopened_frame=frame, supplied_answer=answer,
               phase_two=process_metadata(started), result=result['result'], status='phase_two_completed')
    write_json(evidence, old)


def orchestrate(root: Path):
    root.mkdir(parents=True, exist_ok=False)
    db, evidence = root / 'restart.sqlite', root / 'process_restart.json'
    script = Path(__file__).resolve()
    try:
        first = subprocess.run([sys.executable, str(script), '--phase', 'one', '--db', str(db),
                                '--evidence', str(evidence)], check=True, timeout=90)
        first_exited = time.monotonic_ns()
        second = subprocess.run([sys.executable, str(script), '--phase', 'two', '--db', str(db),
                                 '--evidence', str(evidence)], check=True, timeout=90)
        data = json.loads(evidence.read_text(encoding='utf-8'))
        assert data['status'] == 'phase_two_completed'
        assert [x['kind'] for x in data['phase_one_calls']] == ['initial']
        assert [x['kind'] for x in data['phase_two_calls']] == ['resume']
        assert data['phase_one']['pid'] != data['phase_two']['pid']
        assert data['phase_one']['started_monotonic_ns'] < first_exited < data['phase_two']['started_monotonic_ns']
        assert data['phase_one']['source_sha256'] == data['phase_two']['source_sha256']
        assert data['saved_frame'] == data['reopened_frame']
        assert not data['phase_one']['network_attempts'] and not data['phase_two']['network_attempts']
        data.update(status='verified', parent_pid=os.getpid(), phase_one_exited_monotonic_ns=first_exited,
                    child_returncodes=[first.returncode, second.returncode], boundary=(
            'Two distinct sequential Python processes; A exited cleanly before B started. '
            'The real SQLite saver reopened the exact saved frame. Deterministic session test doubles; '
            'no MCP transport/session recreation, OS crash, human authorization, remote effect, or exactly-once claim.'))
        write_json(evidence, data)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as exc:
        data = json.loads(evidence.read_text(encoding='utf-8')) if evidence.is_file() else {}
        data.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
        write_json(evidence, data)
        raise


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Assertions must be enabled for this probe')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path)
    p.add_argument('--phase', choices=['one', 'two'])
    p.add_argument('--db', type=Path)
    p.add_argument('--evidence', type=Path)
    a = p.parse_args()
    if a.phase:
        if a.db is None or a.evidence is None: p.error('--phase requires --db and --evidence')
        sys.addaudithook(block_external_network)
        asyncio.run(phase_one(a.db, a.evidence) if a.phase == 'one' else phase_two(a.db, a.evidence))
    else:
        if a.out is None: p.error('--out is required without --phase')
        orchestrate(a.out.resolve())
