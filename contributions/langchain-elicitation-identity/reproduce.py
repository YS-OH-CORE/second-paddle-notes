"""Observe whether replayed elicitation consumes an answer for another preview.

Companion to langchain-ai/langchain#40263 (Totoro-qaq): this asks what happens
when the key stays stable but an initial call creates a fresh synthetic draft.
No provider, real document, credential, purchase, or production operation.
Only the in-memory completed_previews list represents an effect.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata as md
import json
from pathlib import Path
import socket
import sys
import traceback

PINNED = {
    'langchain': '1.4.0', 'langchain-core': '1.6.2', 'langgraph': '1.2.11',
    'fastmcp': '4.0.1', 'mcp': '2.1.1',
}
ELICITATION_BLOB = 'efab8d70a74c74392f883df229c2053a58b2eddb'
CASE_SPEC = {
    'stable_same': {'drift': False, 'fresh_key': False, 'bound_answer': False},
    'stable_changed': {'drift': True, 'fresh_key': False, 'bound_answer': False},
    'fresh_changed': {'drift': True, 'fresh_key': True, 'bound_answer': False},
    'stable_changed_bound': {'drift': True, 'fresh_key': False, 'bound_answer': True},
    'stable_changed_decline': {'drift': True, 'fresh_key': False, 'bound_answer': False},
    'direct_original_state': {'drift': True, 'fresh_key': False, 'bound_answer': False},
}


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


async def observe(report: dict) -> None:
    from fastmcp import FastMCP, Context
    from langchain.mcp import MCPAdapter
    from langchain_core.messages import AIMessage
    from langgraph.graph import StateGraph, MessagesState, START, END
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from mcp.types import ElicitRequest, ElicitRequestFormParams, ElicitResult, InputRequiredResult
    # FastMCP resolves postponed annotations in the function's module namespace.
    globals().update(Context=Context, InputRequiredResult=InputRequiredResult)

    server = FastMCP('synthetic-preview-identity')
    rounds = {name: 0 for name in CASE_SPEC}
    issued: dict[str, dict] = {}
    completed: list[dict] = []
    log: list[dict] = []
    report.update(server_log=log, completed_previews=completed, observations=[])

    @server.tool
    async def preview(case: str, ctx: Context) -> str | InputRequiredResult:
        """Ask before adding a synthetic preview label to an in-memory list."""
        spec = CASE_SPEC[case]
        state = ctx.request_state
        if state is not None:
            if state not in issued or issued[state]['case'] != case:
                raise ValueError('Unknown synthetic round state')
            question = issued[state]
            responses = ctx.input_responses or {}
            answer = responses.get(question['key'])
            entry = {'phase': 'resume', 'case': case, 'state': state,
                     'subject': question['subject'], 'key': question['key'],
                     'answer_keys': list(responses),
                     'action': getattr(answer, 'action', None),
                     'content': deepcopy(getattr(answer, 'content', None))}
            log.append(entry)
            if not isinstance(answer, ElicitResult):
                raise ValueError('Missing answer for this original round')
            if answer.action != 'accept':
                entry['outcome'] = 'declined_or_cancelled'
                return 'no preview created'
            if not answer.content or answer.content.get('yes') is not True:
                raise ValueError('No affirmative answer')
            # This application-side control binds the answer to the exact draft.
            # It is a diagnostic alternative, not a patch to MCPAdapter.
            if spec['bound_answer'] and answer.content.get('subject') != question['subject']:
                entry['outcome'] = 'subject_mismatch_rejected'
                raise ValueError('ANSWER_SUBJECT_MISMATCH')
            completed.append({'case': case, 'subject': question['subject'], 'state': state})
            entry['outcome'] = 'preview_created'
            return 'previewed:' + question['subject']

        rounds[case] += 1
        number = rounds[case]
        subject = 'draft-B' if spec['drift'] and number > 1 else 'draft-A'
        key = f'confirm-{number}' if spec['fresh_key'] else 'confirm'
        state = json.dumps({'case': case, 'round': number}, sort_keys=True)
        question = {'case': case, 'round': number, 'subject': subject, 'key': key}
        issued[state] = question
        schema = {'type': 'object', 'properties': {'yes': {'type': 'boolean'}}, 'required': ['yes']}
        if spec['bound_answer']:
            schema['properties']['subject'] = {'type': 'string', 'enum': [subject]}
            schema['required'].append('subject')
        message = f'Create the synthetic preview for {subject}? 한글 표본'
        log.append({'phase': 'initial', **question, 'state': state, 'message': message,
                    'schema': deepcopy(schema)})
        return InputRequiredResult(
            input_requests={key: ElicitRequest(method='elicitation/create', params=ElicitRequestFormParams(
                mode='form', message=message, requested_schema=schema))},
            request_state=state,
        )

    async with MCPAdapter(server) as adapter:
        tools = await adapter.list_tools()
        report['tools'] = [t.name for t in tools]
        assert report['tools'] == ['preview']
        for case, spec in CASE_SPEC.items():
            if case == 'direct_original_state':
                continue
            builder = StateGraph(MessagesState)
            builder.add_node('tools', ToolNode(tools))
            builder.add_edge(START, 'tools'); builder.add_edge('tools', END)
            graph = builder.compile(checkpointer=InMemorySaver())
            config = {'configurable': {'thread_id': 'synthetic-' + case}}
            start_log = len(log); start_effects = len(completed)
            initial = await graph.ainvoke({'messages': [AIMessage(content='', tool_calls=[{
                'name': 'preview', 'args': {'case': case}, 'id': 'call-' + case, 'type': 'tool_call',
            }])]}, config)
            displayed = deepcopy(initial['__interrupt__'][0].value)
            assert len(displayed['requests']) == 1 and len(completed) == start_effects
            first = deepcopy(log[start_log])
            assert first['subject'] == 'draft-A'
            answer = {'action': 'accept', 'content': {'yes': True}}
            if spec['bound_answer']:
                answer['content']['subject'] = first['subject']
            if case.endswith('_decline'):
                answer = {'action': 'decline'}
            resume = {'responses': {displayed['requests'][0]['key']: answer}}
            row = {'case': case, 'displayed_interrupt': displayed, 'submitted_answer': deepcopy(resume),
                   'initial_state': first['state'], 'displayed_subject': first['subject']}
            try:
                final = await graph.ainvoke(Command(resume=resume), config)
                row['outcome'] = 'returned'
                row['remaining_interrupt_count'] = len(final.get('__interrupt__', []))
                row['final_message'] = final['messages'][-1].model_dump(mode='json')
            except Exception as exc:
                row.update(outcome='raised', exception_type=type(exc).__name__, exception=str(exc))
            row['server_log'] = deepcopy(log[start_log:])
            row['completed_previews'] = deepcopy(completed[start_effects:])
            row['subject_preserved'] = all(e['subject'] == first['subject'] for e in row['completed_previews'])
            row['initial_call_count'] = sum(e['phase'] == 'initial' for e in row['server_log'])
            report['observations'].append(row)

        case = 'direct_original_state'
        start_log = len(log); start_effects = len(completed)
        session = adapter.client.session
        first_result = await session.call_tool('preview', {'case': case}, allow_input_required=True)
        assert isinstance(first_result, InputRequiredResult)
        key = next(iter(first_result.input_requests))
        first = deepcopy(log[start_log])
        result = await session.call_tool('preview', {'case': case}, request_state=first_result.request_state,
            input_responses={key: ElicitResult(action='accept', content={'yes': True})}, allow_input_required=True)
        assert not isinstance(result, InputRequiredResult) and not result.is_error
        report['observations'].append({'case': case, 'outcome': 'returned', 'displayed_subject': first['subject'],
            'initial_state': first_result.request_state, 'server_log': deepcopy(log[start_log:]),
            'completed_previews': deepcopy(completed[start_effects:]),
            'initial_call_count': sum(e['phase'] == 'initial' for e in log[start_log:]),
            'wire_result': result.model_dump(mode='json', by_alias=True, exclude_none=True)})

    rows = {row['case']: row for row in report['observations']}
    subjects = lambda case: [e['subject'] for e in rows[case]['completed_previews']]
    assert subjects('stable_same') == ['draft-A']
    assert subjects('stable_changed') == ['draft-B']
    assert rows['stable_changed']['final_message']['status'] == 'success'
    assert rows['stable_changed']['remaining_interrupt_count'] == 0
    assert rows['stable_changed']['subject_preserved'] is False
    assert subjects('fresh_changed') == [] and rows['fresh_changed']['outcome'] == 'raised'
    assert 'confirm-2' in rows['fresh_changed']['exception']
    assert subjects('stable_changed_bound') == []
    assert 'ANSWER_SUBJECT_MISMATCH' in json.dumps(rows['stable_changed_bound'])
    assert subjects('stable_changed_decline') == []
    assert subjects('direct_original_state') == ['draft-A']
    assert rows['direct_original_state']['initial_call_count'] == 1
    report.update(status='completed_with_subject_drift_observed', all_accepted_answers_kept_original_subject=False,
        contrast='Stable key alone is insufficient when replay creates a different question/opaque round state.',
        scope='Six synthetic cases on an actual in-process FastMCP/MCPAdapter/ToolNode graph. Five use InMemorySaver; one is a direct-session control. No LLM, HTTP host, restart, live user approval, or real preview operation.')


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)
    report: dict = {'status': 'incomplete', 'python': sys.version, 'packages': {}, 'network_attempts': []}
    try:
        report['packages'] = {name: md.version(name) for name in PINNED}
        assert report['packages'] == PINNED, report['packages']
        sources = {}
        for name in ('langchain.mcp.elicitation', 'langchain.mcp.tools', 'langchain.mcp.adapter'):
            p = Path(importlib.import_module(name).__file__)
            raw = p.read_bytes()
            sources[name] = {'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest(),
                'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}
        report['sources'] = sources
        assert sources['langchain.mcp.elicitation']['git_blob'] == ELICITATION_BLOB
        def block_network(event, args):
            if event == 'socket.connect' and args[0].family in (socket.AF_INET, socket.AF_INET6):
                report['network_attempts'].append(str(args[1]))
                raise RuntimeError('This in-process experiment needs no network')
        sys.addaudithook(block_network)
        asyncio.run(asyncio.wait_for(observe(report), timeout=45))
        assert not report['network_attempts']
    except BaseException as exc:
        report.update(error=type(exc).__name__ + ': ' + str(exc), traceback=traceback.format_exc())
        raise
    finally:
        save(out / 'observations.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    main(parser.parse_args().out.resolve())
