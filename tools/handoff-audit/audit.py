"""Finite, declared-input handoff audit. Python standard library only.

Groups records by the information available for the same immediate decision.
No model is run, no action is executed, and labels are not supplied to a model.
The reported ceiling applies only to the supplied, weighted finite dataset.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCHEMA = 'handoff-audit/0.1'
MAX_BYTES = 4 * 1024 * 1024
MAX_CASES = 1000


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def reject_constant(value: str) -> None:
    raise ValueError('Non-finite JSON value: ' + value)


def validate_json(value: Any, depth: int = 0) -> None:
    """Use exact, typed JSON structures; floating-point semantics are excluded."""
    if depth > 40:
        raise ValueError('JSON nesting exceeds 40 levels')
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is list:
        for item in value:
            validate_json(item, depth + 1)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            validate_json(item, depth + 1)
        return
    raise ValueError('Only strings, integers, booleans, null, lists and string-keyed objects are supported')


def canonical(value: Any) -> str:
    validate_json(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def label(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > 512:
        raise ValueError(name + ' must be a nonempty string of at most 512 characters')
    return value


def validate(document: Any) -> list[dict[str, Any]]:
    if type(document) is not dict or set(document) != {'schema', 'scope', 'expected_case_ids', 'cases'}:
        raise ValueError('Document must contain exactly schema, scope, expected_case_ids, cases')
    if document['schema'] != SCHEMA:
        raise ValueError('Unsupported schema')
    label(document['scope'], 'scope')
    expected, rows = document['expected_case_ids'], document['cases']
    if type(rows) is not list or not 1 <= len(rows) <= MAX_CASES:
        raise ValueError('Need 1 to 1000 cases')
    if type(expected) is not list or len(expected) != len(rows):
        raise ValueError('Expected inventory and observed inventory differ')
    for case_id in expected:
        label(case_id, 'expected case ID')
    if len(set(expected)) != len(expected):
        raise ValueError('Duplicate expected case ID')
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict or set(row) != {'id', 'request', 'available', 'acceptable_actions', 'weight'}:
            raise ValueError('Each case requires exactly id, request, available, acceptable_actions, weight')
        case_id = label(row['id'], 'case ID')
        if case_id in seen:
            raise ValueError('Duplicate observed case ID')
        seen.add(case_id)
        label(row['request'], 'request')
        canonical(row['available'])
        actions = row['acceptable_actions']
        if type(actions) is not list or not 1 <= len(actions) <= 128:
            raise ValueError('Need 1 to 128 acceptable action labels per case')
        for action in actions:
            label(action, 'action')
        if len(set(actions)) != len(actions):
            raise ValueError('Duplicate acceptable action')
        if type(row['weight']) is not int or not 1 <= row['weight'] <= 1000000:
            raise ValueError('Weights must be positive integers, at most one million')
    if seen != set(expected):
        raise ValueError('Missing or unexpected case ID')
    return rows


def load_bytes(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_BYTES:
        raise ValueError('Input exceeds 4 MiB')
    document = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
    validate(document)
    return document


def audit(document: dict[str, Any]) -> dict[str, Any]:
    rows = validate(document)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        # ID, weight, labels and source inventory are deliberately NOT available information.
        groups[canonical([row['request'], row['available']])].append(row)
    best_total = total = 0
    conflicts = []
    shared_view_groups = compatible_shared_view_groups = 0
    for key in sorted(groups):
        group = groups[key]
        common = set(group[0]['acceptable_actions'])
        mass: dict[str, int] = defaultdict(int)
        group_weight = 0
        for row in group:
            actions = set(row['acceptable_actions'])
            common.intersection_update(actions)
            group_weight += row['weight']
            for action in actions:
                mass[action] += row['weight']
        best = max(mass.values())
        total += group_weight
        best_total += best
        if len(group) > 1:
            shared_view_groups += 1
            compatible_shared_view_groups += bool(common)
        if not common:
            conflicts.append({
                'input_sha256': hashlib.sha256(key.encode('utf-8')).hexdigest(),
                'case_ids': sorted(row['id'] for row in group),
                'acceptable_actions_by_case': {
                    row['id']: sorted(row['acceptable_actions']) for row in sorted(group, key=lambda r: r['id'])},
                'group_weight': group_weight, 'best_covered_weight': best,
                'no_common_acceptable_action': True,
            })
    ceiling = Fraction(best_total, total)
    return {
        'schema': 'handoff-audit-result/0.1',
        'status': 'conflict_witness_found' if conflicts else 'no_conflict_in_supplied_cases',
        'scope': document['scope'], 'cases': len(rows), 'distinct_available_inputs': len(groups),
        'shared_view_groups': shared_view_groups,
        'compatible_shared_view_groups': compatible_shared_view_groups,
        'conflicting_groups': len(conflicts), 'witnesses': conflicts,
        'finite_full_coverage_ceiling': {
            'numerator': ceiling.numerator, 'denominator': ceiling.denominator,
            'best_covered_weight': best_total, 'total_weight': total},
        'interpretation': 'Best achievable by any one-step rule seeing only request+available on this finite weighted inventory. Not measured model accuracy or a deployment distribution.',
        'equality': 'Typed structural JSON with sorted object keys; list order and string contents retained. Supply rendered text as a string if byte/order differences matter.',
        'limits': ['Declared available information must include all relevant retained state and retrieval results.',
                   'No witness is not a proof of universal preservation.',
                   'Acceptable actions and weights are caller-supplied judgments.',
                   'Clarification is an ordinary action only when explicitly acceptable; no free abstention is invented.'],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, help='Create a new report; never overwrite an existing file')
    args = parser.parse_args(argv)
    try:
        with args.input.open('rb') as source:
            data = source.read(MAX_BYTES + 1)
        result = audit(load_bytes(data))
        result['input_file_sha256'] = hashlib.sha256(data).hexdigest()
        text = json.dumps(result, ensure_ascii=True, indent=2) + '\n'
        if args.out:
            with args.out.open('x', encoding='utf-8') as out:
                out.write(text)
        else:
            print(text, end='')
        return int(result['conflicting_groups'] > 0)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({'status': 'invalid_or_unreadable_input', 'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
