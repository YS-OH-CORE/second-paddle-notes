"""Stress the prior ordered-writes experiment, using real compiled graphs.

Supplemental work: Youngseok Oh x Zero, AI collaboration partners.
This is a design experiment, not an upstream-approved patch.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import traceback
from typing import Annotated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-probe', type=Path, required=True)
    parser.add_argument('--source-module', type=Path, required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    baseline = args.baseline_probe.read_bytes()
    assert hashlib.sha256(baseline).hexdigest() == '86b4a500e79568eae246894d70b6b59893e7a714477f800119627b99319b68c1'
    spec = importlib.util.spec_from_file_location('baseline_probe', args.baseline_probe)
    base = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base
    spec.loader.exec_module(base)  # Real imports; also denies sockets/DNS and tracing.

    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.tools import tool, InjectedToolCallId
    from langgraph.graph import StateGraph, START, END
    from langgraph.prebuilt import ToolNode
    from langgraph.types import Command
    from pydantic import BaseModel

    source = Path(inspect.getfile(ToolNode)).resolve()
    assert source == args.source_module.resolve()

    @dataclass
    class Delta:
        messages: list
        total: int
        best: list[str]

    class ModelDelta(BaseModel):
        messages: list
        total: int
        best: list[str]

    class EdgeState(base.State):
        exclusive: int

    # Tool annotation evaluation must see these real classes in module globals.
    globals().update(Command=Command, InjectedToolCallId=InjectedToolCallId)

    def make_command(name, call_id, shape, conflict):
        command = base.command_for(name, call_id, 'sends')
        values = command.update
        if conflict:
            values['exclusive'] = base.VALUES[name][0]
        if shape == 'tuple':
            update = tuple(values.items())
        elif shape == 'dataclass':
            update = Delta(**values)
        elif shape == 'pydantic':
            update = ModelDelta(**values)
        elif shape == 'none':
            update = None
        else:
            assert shape == 'dict'
            update = values
        return Command(graph=Command.PARENT, goto=command.goto, update=update)

    def case(left, right, conflict, asynchronous):
        shapes = {'alpha': left, 'beta': right}
        row = {'case': f'{left}_{right}' + ('_conflict' if conflict else '') + ('_async' if asynchronous else '_sync'),
               'group': 'representation_and_conflict', 'shapes': shapes,
               'conflict': conflict, 'async': asynchronous}
        def make_tool(name):
            @tool(name, description='Deterministic offline representation fixture')
            def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
                return make_command(name, tool_call_id, shapes[name], conflict)
            return handoff
        node = ToolNode([make_tool(n) for n in shapes], handle_tool_errors=False)
        try:
            commands = node._combine_tool_outputs([make_command(n, 'call-' + n, shapes[n], conflict) for n in shapes], 'dict')
            row['boundary_commands'] = len(commands)
        except Exception as exc:
            row['boundary_error'] = {'type': type(exc).__name__, 'message': str(exc)}
        child = StateGraph(EdgeState)
        child.add_node('tools', node)
        child.add_edge(START, 'tools')
        child.add_edge('tools', END)
        parent = StateGraph(EdgeState)
        parent.add_node('child', child.compile(), destinations=('worker',))
        parent.add_node('worker', lambda state: {'visited': [state['job']]})
        parent.add_edge(START, 'child')
        parent.add_edge('worker', END)
        graph = parent.compile()
        initial = {'messages': [AIMessage(content='', id='request', tool_calls=[
            {'name': n, 'args': {}, 'id': 'call-' + n, 'type': 'tool_call'} for n in shapes])],
                   'total': 0, 'best': [], 'visited': [], 'exclusive': 0}
        live = [n for n in shapes if shapes[n] != 'none']
        row['expected'] = ({'error': 'InvalidUpdateError'} if conflict else {
            'total': sum(base.VALUES[n][0] for n in live),
            'best': max((base.VALUES[n][1] for n in live), key=len, default=[]),
            'tool_ids': ['call-' + n for n in live], 'visited': ['alpha', 'beta'], 'exclusive': 0})
        try:
            config = {'recursion_limit': 12, 'max_concurrency': 2}
            result = asyncio.run(graph.ainvoke(initial, config)) if asynchronous else graph.invoke(initial, config)
            row['actual'] = {'total': result['total'], 'best': result['best'],
                             'tool_ids': [m.tool_call_id for m in result['messages'] if isinstance(m, ToolMessage)],
                             'visited': sorted(result['visited']), 'exclusive': result['exclusive']}
        except Exception as exc:
            row['actual'] = {'error': type(exc).__name__}
            row['error_message'] = str(exc)
            row['traceback'] = traceback.format_exc()
        row['contract_met'] = row['actual'] == row['expected']
        return row

    rows = []
    for names, route in ((['alpha'], 'sends'), (['alpha', 'beta'], 'sends'),
                         (['beta', 'alpha'], 'sends'), (['alpha'], 'string')):
        for asynchronous in (False, True):
            row = base.run_case(names, route, asynchronous)
            row.update(group='prior_controls', contract_met=row['preserved'])
            rows.append(row)
    for left, right, conflict in (
        ('dict', 'tuple', False), ('tuple', 'dict', False), ('tuple', 'tuple', False),
        ('dataclass', 'tuple', False), ('tuple', 'pydantic', False),
        ('none', 'tuple', False), ('tuple', 'none', False), ('dict', 'dict', True),
    ):
        for asynchronous in (False, True):
            rows.append(case(left, right, conflict, asynchronous))
    assert len(rows) == 24 and len({r['case'] for r in rows}) == 24
    report = {'variant': args.variant, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'source': str(source), 'python': sys.version, 'count': len(rows),
              'contract_met': sum(r['contract_met'] for r in rows), 'model_calls': 0,
              'rows': rows, 'scope': 'Real tools and compiled graphs; no mocks; resume/root/mixed-goto not tested.'}
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for row in rows:
        print(json.dumps({'variant': args.variant, **row}), flush=True)
    assert all(r['contract_met'] for r in rows if r['case'].startswith('string_'))
    # Other failures remain evidence. The audit checks the declared matrix.


if __name__ == '__main__':
    main()
