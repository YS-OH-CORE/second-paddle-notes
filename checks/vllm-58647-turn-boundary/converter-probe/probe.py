# SPDX-License-Identifier: Apache-2.0
"""Pinned source-method converter -> explicit HF projection -> template probe.

Youngseok Oh x Zero. Synthetic data. This does NOT import the full vLLM server.
The selected upstream method/class ASTs are executed unchanged; their original
files and hashes are retained. Projection is ours, not vLLM's renderer.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import socket
import sys
import time
import types
from typing import Any, Literal
from pydantic import BaseModel, ValidationError
from jinja2 import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment

PIN = 'ddd6fbca148a867aad1fcab7ec72f582b9977db4'
BLOBS = {'serving.py': '08f208f8249e2fb9d31d89bb7d7a2a0e7530514f',
         'protocol.py': '48202831fe397a1ccea5a89c264a9da6e7ce032b'}
TEMPLATE_SHA = 'c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041'
METHODS = ('_convert_image_source_to_url', '_extract_system_text', '_convert_messages',
           '_convert_message_content', '_convert_block', '_convert_tool_use_block',
           '_convert_tool_result_block', '_convert_user_tool_result')
OLD, CURRENT = 'OLD_REASONING_SENTINEL', 'CURRENT_REASONING_SENTINEL'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def load_sources(assets):
    sources, parsed, provenance = {}, {}, {}
    for name, expected in BLOBS.items():
        raw = (assets / name).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != expected:
            raise ValueError(f'{name}: source identity differs from declared pin')
        sources[name] = raw.decode('utf-8')
        parsed[name] = ast.parse(sources[name])
        provenance[name] = {'git_blob': blob, 'sha256': sha(raw)}
    protocol = [n for n in parsed['protocol.py'].body if isinstance(n, ast.ClassDef)
                and n.name in ('AnthropicContentBlock', 'AnthropicMessage')]
    assert [n.name for n in protocol] == ['AnthropicContentBlock', 'AnthropicMessage']
    cls = next(n for n in parsed['serving.py'].body if isinstance(n, ast.ClassDef)
               and n.name == 'AnthropicServingMessages')
    selected = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in METHODS]
    assert {n.name for n in selected} == set(METHODS)
    # Ensure no selected method calls an omitted cls method. No branch is rewritten.
    dependencies = {n.attr for method in selected for n in ast.walk(method)
                    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == 'cls' and n.attr.startswith('_')}
    assert dependencies <= set(METHODS), dependencies - set(METHODS)
    if any(isinstance(n, ast.Name) and n.id == 'super' for m in selected for n in ast.walk(m)):
        raise ValueError('Inherited semantics require a full-package test')
    projection = ast.parse('class SourceConverter:\n    pass\n').body[0]
    projection.body = selected
    module = types.ModuleType('zero_pinned_converter')
    sys.modules[module.__name__] = module
    module.__dict__.update(BaseModel=BaseModel, Any=Any, Literal=Literal, json=json, time=time)
    future = ast.parse('from __future__ import annotations').body[0]
    code = ast.fix_missing_locations(ast.Module(body=[future, *protocol, projection], type_ignores=[]))
    exec(compile(code, str(assets / 'selected_upstream.py'), 'exec'), module.__dict__)
    module.AnthropicMessage.model_rebuild()
    provenance['selected_asts'] = {n.name: sha(ast.dump(n, include_attributes=False).encode())
                                   for n in [*protocol, *selected]}
    return module.AnthropicMessage, module.SourceConverter, provenance

def fixture(language, count, shape):
    followup = {'en': 'Do not publish the report. Keep it private.',
                'ko': '보고서를 공개하지 마. 비공개로 유지해.'}[language]
    results = [{'type': 'tool_result', 'tool_use_id': f'call_{i}',
                'content': f'LEDGER_{i}: PRIVATE'} for i in range(count)]
    messages = [
        {'role': 'user', 'content': 'Previous task: inspect a fictional note.'},
        {'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': OLD},
                                          {'type': 'text', 'text': 'Previous task complete.'}]},
        {'role': 'user', 'content': 'Current task: inspect the fictional publication ledger.'},
        {'role': 'assistant', 'content': [{'type': 'thinking', 'thinking': CURRENT}] + [
            {'type': 'tool_use', 'id': f'call_{i}', 'name': 'read_status', 'input': {'index': i}}
            for i in range(count)]},
    ]
    if shape == 'same_message':
        messages += [{'role': 'user', 'content': results + [{'type': 'text', 'text': followup}]}]
    elif shape == 'adjacent_messages':
        messages += [{'role': 'user', 'content': results}, {'role': 'user', 'content': followup}]
    elif shape == 'completed_then_new_user':
        messages += [{'role': 'user', 'content': results},
                     {'role': 'assistant', 'content': 'The inspection is complete.'},
                     {'role': 'user', 'content': followup}]
    elif shape == 'tool_only':
        messages += [{'role': 'user', 'content': results}]
    else:
        raise ValueError(shape)
    return messages, followup

def hf_projection(messages):
    """Explicit narrow bridge, NOT the vLLM chat_utils/renderer implementation."""
    projected = deepcopy(messages)
    for message in projected:
        message.setdefault('content', '')
        if 'reasoning' in message:
            message['reasoning_content'] = message.pop('reasoning')
        for call in message.get('tool_calls', []):
            call['function']['arguments'] = json.loads(call['function']['arguments'])
    return projected

def analyze(rows):
    assert len(rows) == 16 and len({r['id'] for r in rows}) == 16
    groups = []
    for language in ('en', 'ko'):
        for count in (1, 2):
            group = {r['shape']: r for r in rows if r['language'] == language and r['tool_count'] == count}
            same, adjacent = group['same_message'], group['adjacent_messages']
            assert same['native'] != adjacent['native']
            equal = same['converted'] == adjacent['converted']
            assert group['completed_then_new_user']['converted'] != adjacent['converted']
            groups.append({'language': language, 'tool_count': count,
                           'distinct_native_messages': True, 'same_converted_messages': equal,
                           'completed_assistant_boundary_stays_distinct': True})
    for row in rows:
        assert row['input_unchanged'] and row['tool_ids_matched']
        assert row['current_trace_in_converted'] and row['old_trace_in_converted']
        assert len(row['renderings']) == 2
        for rendering in row['renderings']:
            assert sha(rendering['text'].encode()) == rendering['sha256']
            expected_old = rendering['preserve']
            expected_current = rendering['preserve'] or row['shape'] == 'tool_only'
            assert rendering['old'] == expected_old
            assert rendering['current'] == expected_current
            assert rendering['followup_count'] == (0 if row['shape'] == 'tool_only' else 1)
    return {'native_conversions': len(rows), 'template_renders': 2 * len(rows),
            'same_message_vs_adjacent_pairs': len(groups),
            'equal_converted_pairs': sum(g['same_converted_messages'] for g in groups),
            'completed_assistant_controls_distinct': len(groups),
            'all_followup_text_preserved': True, 'all_tool_ids_matched': True,
            'groups': groups, 'model_calls': 0, 'full_vllm_server_imports': 0,
            'execution_scope': 'unaltered extracted Pydantic classes and converter methods; explicit local HF projection; official Jinja template'}

def run(assets, output):
    output.mkdir(parents=True, exist_ok=False)
    Message, Converter, provenance = load_sources(assets)
    raw = (assets / 'chat_template.jinja').read_bytes()
    assert sha(raw) == TEMPLATE_SHA
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    def fail(message):
        raise TemplateError(message)
    env.globals['raise_exception'] = fail
    template = env.from_string(raw.decode())
    # Actual extracted Pydantic schema must reject an invalid role.
    try:
        Message.model_validate({'role': 'invented_role', 'content': 'invalid'})
    except ValidationError:
        schema_control = True
    else:
        raise AssertionError('Invalid protocol role accepted')
    attempted = []
    def blocked(*a, **kw):
        attempted.append('socket_or_dns')
        raise RuntimeError('Network forbidden in the measurement phase')
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.getaddrinfo = blocked
    rows = []
    for language in ('en', 'ko'):
        for count in (1, 2):
            for shape in ('tool_only', 'same_message', 'adjacent_messages', 'completed_then_new_user'):
                native, followup = fixture(language, count, shape)
                validated = [Message.model_validate(m) for m in native]
                before = [m.model_dump() for m in validated]
                converted = []
                Converter._convert_messages(validated, converted)
                calls = [c['id'] for m in converted for c in m.get('tool_calls', [])]
                result_ids = [m['tool_call_id'] for m in converted if m['role'] == 'tool']
                row = {'id': f'{language}-{count}-{shape}', 'language': language,
                       'tool_count': count, 'shape': shape, 'native': native,
                       'converted': converted, 'projected': hf_projection(converted),
                       'input_unchanged': before == [m.model_dump() for m in validated],
                       'tool_ids_matched': calls == result_ids == [f'call_{i}' for i in range(count)],
                       'old_trace_in_converted': any(m.get('reasoning') == OLD for m in converted),
                       'current_trace_in_converted': any(m.get('reasoning') == CURRENT for m in converted),
                       'renderings': []}
                for preserve in (False, True):
                    text = template.render(messages=row['projected'], add_generation_prompt=True,
                                           enable_thinking=False, preserve_thinking=preserve)
                    row['renderings'].append({'preserve': preserve, 'old': OLD in text,
                        'current': CURRENT in text, 'followup_count': text.count(followup),
                        'sha256': sha(text.encode()), 'text': text})
                rows.append(row)
    write(output / 'OBSERVATIONS.json', rows)
    summary = analyze(rows)
    write(output / 'SUMMARY.json', summary)
    write(output / 'PROVENANCE.json', {'upstream_commit': PIN, **provenance,
          'template_sha256': TEMPLATE_SHA, 'python': sys.version,
          'pydantic': importlib.metadata.version('pydantic'),
          'jinja2': importlib.metadata.version('jinja2'), 'invalid_role_rejected': schema_control,
          'network_attempts': attempted})
    print(json.dumps(summary), flush=True)

def audit(output):
    rows = json.loads((output / 'OBSERVATIONS.json').read_text())
    summary = analyze(rows)
    assert summary == json.loads((output / 'SUMMARY.json').read_text())
    for row in rows:
        assert fixture(row['language'], row['tool_count'], row['shape'])[0] == row['native']
        assert hf_projection(row['converted']) == row['projected']
    bad = deepcopy(rows)
    bad[0]['renderings'][0]['text'] += 'CORRUPTED'
    try:
        analyze(bad)
    except AssertionError:
        pass
    else:
        raise AssertionError('Corrupted observation undetected')
    report = {'summary_exact': True, 'fixtures_exact': True,
              'projection_recomputed': True, 'text_corruption_rejected': True,
              'independent_external_replication': False, 'new_model_calls': 0}
    write(output / 'READBACK_AUDIT.json', report)
    print(json.dumps(report), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'audit'))
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'run':
        if not args.assets:
            parser.error('--assets is required for run')
        run(args.assets, args.out)
    else:
        audit(args.out)
