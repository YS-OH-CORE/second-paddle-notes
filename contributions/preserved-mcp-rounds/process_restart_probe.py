"""Verify that a saved MCP form round survives a fresh Python process.

This deliberately uses a deterministic synthetic session rather than a live MCP
transport. It tests the narrower boundary left open by probe.py: process A saves
the question and exits; process B opens the same SQLite checkpoint, supplies the
answer to the original key/state, and completes without issuing a new initial
request. It does not establish MCP transport/session recreation or exactly-once
remote effects.
"""
from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

from round_graph import build_round_graph

TOKEN = 'opaque-process-A-state'
KEY = 'confirm-process-A'
NOTE = 'answer after a fresh interpreter'


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
        assert kwargs.get('request_state') is None
        self.calls.append({'kind': 'initial', 'name': name, 'arguments': arguments})
        return question()


class PhaseTwoSession:
    def __init__(self): self.calls = []
    async def call_tool(self, name, arguments, **kwargs):
        from mcp.types import CallToolResult, TextContent
        state = kwargs.get('request_state')
        responses = kwargs.get('input_responses') or {}
        assert state == TOKEN, state
        assert set(responses) == {KEY}, set(responses)
        answer = responses[KEY]
        assert answer.action == 'accept'
        assert answer.content == {'yes': True, 'note': NOTE}
        self.calls.append({'kind': 'resume', 'state': state, 'keys': list(responses)})
        return CallToolResult(content=[TextContent(type='text', text='completed-from-process-B')])


async def phase_one(db: Path, evidence: Path):
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
        assert state.values['frame']['value']['requestState'] == TOKEN
    evidence.write_text(json.dumps({'phase_one_calls': session.calls, 'shown': shown}, indent=2) + '\n')


async def phase_two(db: Path, evidence: Path):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.types import Command
    session = PhaseTwoSession()
    config = {'configurable': {'thread_id': 'process-restart'}}
    answer = {'responses': {KEY: {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}}}
    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        graph = build_round_graph(session, saver)
        before = await graph.aget_state(config)
        assert before.values['frame']['value']['requestState'] == TOKEN
        result = await graph.ainvoke(Command(resume=answer), config, durability='sync')
        assert result['status'] == 'completed'
        assert not result.get('__interrupt__')
        assert 'completed-from-process-B' in json.dumps(result['result'])
    old = json.loads(evidence.read_text())
    old.update(phase_two_calls=session.calls, status='verified', boundary=(
        'Fresh Python interpreter reopened the SQLite checkpoint and resumed the exact saved form round. '
        'Synthetic session only; no MCP transport/session recreation, remote side effect, or exactly-once claim.'))
    evidence.write_text(json.dumps(old, indent=2) + '\n')


def orchestrate(root: Path):
    root.mkdir(parents=True, exist_ok=False)
    db, evidence = root / 'restart.sqlite', root / 'process_restart.json'
    script = Path(__file__).resolve()
    first = subprocess.run([sys.executable, str(script), '--phase', 'one', '--db', str(db), '--evidence', str(evidence)])
    assert first.returncode == 0
    second = subprocess.run([sys.executable, str(script), '--phase', 'two', '--db', str(db), '--evidence', str(evidence)])
    assert second.returncode == 0
    data = json.loads(evidence.read_text())
    assert data['status'] == 'verified'
    assert [x['kind'] for x in data['phase_one_calls']] == ['initial']
    assert [x['kind'] for x in data['phase_two_calls']] == ['resume']
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path)
    p.add_argument('--phase', choices=['one', 'two'])
    p.add_argument('--db', type=Path)
    p.add_argument('--evidence', type=Path)
    a = p.parse_args()
    if a.phase:
        asyncio.run(phase_one(a.db, a.evidence) if a.phase == 'one' else phase_two(a.db, a.evidence))
    else:
        if a.out is None: p.error('--out is required without --phase')
        orchestrate(a.out.resolve())
