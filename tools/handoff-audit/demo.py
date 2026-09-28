"""Apply the auditor to a pinned real helper and four fully fictional histories.

No vLLM import, Mistral validator, tokenizer, image download, endpoint or model.
A hash-verified function is extracted unchanged from the vendored Apache source.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, cast
import audit

HERE = Path(__file__).resolve().parent
SOURCE_SHA256 = '74fa5093b91ed69d79ff402f0f86633be8017f110455f0843513404d6799b6d0'
SOURCE_COMMIT = 'a9cdfa3b645773684b40359e11e78fb49f4c57e8'
TOOL_IDS = ('abc123XYZ', 'def456UVW')
URLS = ('https://example.invalid/X.png', 'https://example.invalid/Y.png')
QUESTION = 'Which tool call returned https://example.invalid/Y.png?'


def load_helper():
    data = (HERE / 'vendor/mistral.py').read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Pinned upstream source has changed')
    tree = ast.parse(data.decode('utf-8'))
    matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_adapt_tool_images_for_mistral']
    if len(matches) != 1:
        raise ValueError('Expected one helper definition')
    namespace = {'Any': Any, 'cast': cast, 'ChatCompletionMessageParam': dict}
    exec(compile(ast.Module(body=matches, type_ignores=[]), 'pinned_vllm_helper', 'exec'), namespace)
    return namespace['_adapt_tool_images_for_mistral']


def histories():
    for owners in itertools.product(TOOL_IDS, repeat=2):
        calls = [{'id': t, 'type': 'function', 'function': {'name': 'inspect', 'arguments': '{}'}} for t in TOOL_IDS]
        messages = [{'role': 'user', 'content': 'Use both tools.'},
                    {'role': 'assistant', 'content': None, 'tool_calls': calls}]
        for t in TOOL_IDS:
            content = [{'type': 'image_url', 'image_url': {'url': url}} for url, owner in zip(URLS, owners) if owner == t]
            messages.append({'role': 'tool', 'tool_call_id': t, 'content': content})
        yield {'id': ''.join('A' if t == TOOL_IDS[0] else 'B' for t in owners),
               'messages': messages, 'owners': dict(zip(URLS, owners))}


def datasets():
    adapt = load_helper()
    original = list(histories())
    result = {}
    for mode in ('v15_identity', 'v13_messages_only', 'v13_with_sidecar', 'v13_clarification_allowed'):
        rows = []
        for h in original:
            before = deepcopy(h['messages'])
            adapted = adapt(h['messages'], 15 if mode == 'v15_identity' else 13)
            if h['messages'] != before:
                raise ValueError('Original history was changed')
            available = {'messages': adapted}
            if mode == 'v13_with_sidecar':
                available['image_owners'] = h['owners']
            actions = [h['owners'][URLS[1]]]
            if mode == 'v13_clarification_allowed':
                actions.append('request_original_tool_result')
            rows.append({'id': h['id'], 'request': QUESTION, 'available': available,
                         'acceptable_actions': actions, 'weight': 1})
        result[mode] = {'schema': audit.SCHEMA,
                        'scope': mode + ': four equiprobable synthetic ownership histories; only declared JSON at this one-step decision.',
                        'expected_case_ids': [h['id'] for h in original], 'cases': rows}
    return result


def run():
    cases = datasets()
    return {
        'scope': 'New finite software audit of the previously documented source-attribution tradeoff, not a new upstream defect.',
        'source_commit': SOURCE_COMMIT, 'source_sha256': SOURCE_SHA256,
        'synthetic_source_histories': 4, 'model_calls': 0,
        'reports': {name: audit.audit(data) for name, data in cases.items()},
        'sidecar_status': 'Analyst diagnostic control, not a vLLM patch or validated renderer integration.',
        'clarification_status': 'Shared permitted immediate action, not successful identification or retrieval execution.',
        'not_executed': ['full vLLM import', 'message validator', 'tokenizer', 'model inference', 'real tool execution'],
    }


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=True, indent=2))
