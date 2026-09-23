"""Offline semantic check of the proposed boolean-def conversion in #8621.

The baseline is a pinned real Pydantic AI checkout. 'conversion_only' is our
literal implementation of the issue's proposed _walk_def conversion, not an
upstream commit or another contributor's unpublished patch. 'false_guard'
is a narrow comparison candidate, not a provider-ready fix. No provider calls.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

TARGET = '06be8e7a0056d6c6c72d2868f6b26ee8e7364c77'
SOURCE = Path('pydantic_ai_slim/pydantic_ai/_json_schema.py')
NEEDLE = "        self.refs_stack.append(key)\n        walked = self._handle({**deepcopy(def_schema), **siblings})"
CONVERSION = "        if isinstance(def_schema, bool):\n            def_schema = {} if def_schema else {'not': {}}\n\n" + NEEDLE
GUARD = "        if isinstance(def_schema, bool):\n            if def_schema is False:\n                # False rejects every instance: a sibling 'not' cannot replace it.\n                return self._handle({**deepcopy(siblings), 'not': {}})\n            def_schema = {}\n\n" + NEEDLE


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block_network(*args, **kwargs):
    raise RuntimeError('OFFLINE_FIXTURE: network connections are not part of this test')


def case_schema(definition: bool, siblings: dict) -> dict:
    return {
        'type': 'object',
        'properties': {'x': {'$ref': '#/$defs/X', **deepcopy(siblings)}},
        'required': ['x'],
        '$defs': {'X': definition},
    }


def phase_result(phase: str, repo: Path) -> dict:
    # This guard is only for this offline Python fixture, not an OS sandbox.
    socket.socket.connect = socket.socket.connect_ex = block_network
    from jsonschema import Draft202012Validator
    from pydantic_ai._json_schema import InlineDefsJsonSchemaTransformer
    import pydantic_ai._json_schema as module

    source = repo / SOURCE
    assert Path(module.__file__).resolve() == source.resolve(), 'Not importing pinned checkout'
    cases = [
        ('true_with_not', True, {'not': {'type': 'string'}}),
        ('false_no_siblings', False, {}),
        ('false_with_description', False, {'description': 'Always reject x'}),
        ('false_with_not', False, {'not': {'type': 'string'}}),
    ]
    witnesses = [{'x': x} for x in [7, 'text', None, True, [], {}]] + [{}]
    rows = []
    for name, definition, siblings in cases:
        original = case_schema(definition, siblings)
        snapshot = deepcopy(original)
        Draft202012Validator.check_schema(original)
        expected = [Draft202012Validator(original).is_valid(x) for x in witnesses]
        row = {'case': name, 'original': original, 'witnesses': witnesses, 'expected': expected}
        try:
            converted = InlineDefsJsonSchemaTransformer(original).walk()
        except TypeError as exc:
            assert phase == 'baseline', f'Unexpected TypeError in {phase}: {exc}'
            row['exception'] = {'type': type(exc).__name__, 'message': str(exc)}
        else:
            assert phase != 'baseline', 'Boolean defs no longer crash: refresh assessment'
            Draft202012Validator.check_schema(converted)
            observed = [Draft202012Validator(converted).is_valid(x) for x in witnesses]
            mismatches = [i for i, (a, b) in enumerate(zip(expected, observed)) if a != b]
            row.update(converted=converted, observed=observed, mismatch_indices=mismatches)
            if phase == 'conversion_only' and name == 'false_with_not':
                assert mismatches == [0, 2, 3, 4, 5], row
                assert converted['properties']['x'] == {'not': {'type': 'string'}}, row
            else:
                assert not mismatches, row
        assert original == snapshot, 'Transformer changed caller input'
        rows.append(row)
    return {
        'phase': phase, 'source_sha256': digest(source.read_bytes()),
        'versions': {x: importlib.metadata.version(x) for x in ['pydantic-ai-slim', 'pydantic', 'jsonschema']},
        'cases': rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--result', type=Path)
    parser.add_argument('--phase', choices=['baseline', 'conversion_only', 'false_guard'])
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.phase:
        print(json.dumps(phase_result(args.phase, repo), ensure_ascii=False), flush=True)
        return 0

    def git(*argv):
        return subprocess.check_output(['git', *argv], cwd=repo, text=True).strip()

    assert git('rev-parse', 'HEAD') == TARGET, 'Unexpected source revision'
    assert not git('status', '--porcelain'), 'Checkout must be disposable and clean'
    source = repo / SOURCE
    before = source.read_bytes()
    text = before.decode('utf-8')
    assert text.count(NEEDLE) == 1, 'Source shape changed'
    report = {
        'target': TARGET,
        'scope': 'real generic InlineDefsJsonSchemaTransformer + Draft202012Validator; synthetic schemas; no provider/application E2E',
        'candidate_status': 'locally authored interpretations of a proposed direction; not upstream patches',
        'checks_completed': False, 'source_restored': False, 'phases': [],
        'candidate_diffs': {},
        'author': 'Zero (ChatGPT), for Youngseok Oh / YS-OH-CORE',
    }
    clean_env = {
        'PATH': os.environ['PATH'], 'HOME': os.environ['HOME'],
        'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
        'OTEL_SDK_DISABLED': 'true', 'LOGFIRE_SEND_TO_LOGFIRE': 'false',
    }
    try:
        for phase, replacement in [('baseline', NEEDLE), ('conversion_only', CONVERSION), ('false_guard', GUARD)]:
            candidate = text.replace(NEEDLE, replacement)
            ast.parse(candidate)
            source.write_bytes(candidate.encode('utf-8'))
            if phase != 'baseline':
                report['candidate_diffs'][phase] = git('diff', '--', str(SOURCE))
            completed = subprocess.run(
                [sys.executable, '-B', str(Path(__file__).resolve()), '--repo', str(repo), '--phase', phase],
                cwd=repo, env=clean_env, text=True, capture_output=True, timeout=35,
            )
            if completed.returncode:
                raise RuntimeError(f'{phase}: {completed.stdout[-2000:]} {completed.stderr[-3000:]}')
            row = json.loads(completed.stdout)
            row['stderr'] = completed.stderr
            report['phases'].append(row)
        report['checks_completed'] = True
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        source.write_bytes(before)
        report['source_restored'] = source.read_bytes() == before and not git('status', '--porcelain')
        print('ZERO_BOOL_DEFS_RESULT ' + json.dumps(report, ensure_ascii=False), flush=True)
        if args.result:
            args.result.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if report['checks_completed'] and report['source_restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
