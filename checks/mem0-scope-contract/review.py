"""Reproduce a scoped-deletion contract using the pinned native SQLite module.

Usage: python review.py --storage /path/to/pinned/storage.py --out result.json
Only fictional in-memory databases are created. No API or model calls. The
provided source must match the published Git blob before it is imported.

Review code: Zero, with Youngseok Oh's direction; Apache-2.0.
Canonical scope helper excerpt: Mem0 contributors, Apache-2.0,
Sai-Sreenath-1819/mem0 af93b81bc9573be1b78014b5005a0b0d950605bb.
The reference is experimental and is not installed into any SDK.
"""
from pathlib import Path
import importlib.util
import sys
SOURCE_PATH = None
SQLiteManager = None

from typing import Any


def _escape_scope_value(val: Any) -> str:
    """Escape the structural delimiters of the session scope key."""
    return str(val).replace("%", "%25").replace("&", "%26").replace("=", "%3D")


def _build_session_scope(filters):
    """Build deterministic session scope string from entity IDs."""
    parts = []
    for key in sorted(["user_id", "agent_id", "run_id"]):
        val = filters.get(key)
        if val:
            parts.append(f"{key}={_escape_scope_value(val)}")
    return "&".join(parts)

from collections.abc import Mapping

FIELDS = frozenset(('user_id', 'agent_id', 'run_id'))


def checked_filter(filters):
    if not isinstance(filters, Mapping) or not filters or set(filters) - FIELDS:
        raise ValueError('A nonempty identity-only filter is required')
    if any(type(v) is not str or not v or any(c.isspace() for c in v) for v in filters.values()):
        raise ValueError('Use already-normalized, nonempty string identities')
    return dict(filters)


def parse_canonical_scope(scope):
    """Decode exactly the known canonical form once; ambiguous rows abort."""
    if not isinstance(scope, str) or not scope:
        raise ValueError('Unknown or empty stored scope')
    fields = {}
    for part in scope.split('&'):
        key, sep, value = part.partition('=')
        if not sep or key not in FIELDS or key in fields or not value:
            raise ValueError('Unknown, repeated, or empty scope field')
        fields[key] = value.replace('%3D', '=').replace('%26', '&').replace('%25', '%')
    checked_filter(fields)
    if _build_session_scope(fields) != scope:
        raise ValueError('Non-canonical stored key; do not guess')
    return fields


def delete_matching_reference(manager, filters):
    """One SQLite transaction, confined to an in-memory test instance.

    This scans distinct keys and performs parameterized exact-key deletes for
    matching fields. It is a behavior reference, not a scalable migration plan.
    """
    filters = checked_filter(filters)
    if manager.db_path != ':memory:':
        raise ValueError('Reference adapter is limited to disposable in-memory tests')
    with manager._lock:
        con = manager.connection
        con.execute('BEGIN IMMEDIATE')
        try:
            keys = [row[0] for row in con.execute('SELECT DISTINCT session_scope FROM messages')]
            selected = []
            for key in keys:
                values = parse_canonical_scope(key)
                if all(values.get(k) == v for k, v in filters.items()):
                    selected.append(key)
            before = con.total_changes
            con.executemany('DELETE FROM messages WHERE session_scope = ?', [(key,) for key in selected])
            changed = con.total_changes - before
            con.execute('COMMIT')
        except BaseException:
            con.execute('ROLLBACK')
            raise
    return {'selected_keys': len(selected), 'deleted_rows': changed}

from copy import deepcopy

CORPUS = (
    ('alice-root', {'user_id':'alice'}),
    ('alice-r1', {'user_id':'alice', 'run_id':'r1'}),
    ('alice-r2', {'user_id':'alice', 'run_id':'r2'}),
    ('alice-bot-r1', {'user_id':'alice', 'agent_id':'bot', 'run_id':'r1'}),
    ('alice-other-r1', {'user_id':'alice', 'agent_id':'other', 'run_id':'r1'}),
    ('bob-r1', {'user_id':'bob', 'run_id':'r1'}),
    ('bob-bot-r1', {'user_id':'bob', 'agent_id':'bot', 'run_id':'r1'}),
    ('bot-only', {'agent_id':'bot'}),
    ('run-only', {'run_id':'r1'}),
    ('alice2-r1', {'user_id':'alice2', 'run_id':'r1'}),
    ('literal-delimiters', {'user_id':'alice&run_id=r1', 'run_id':'r2'}),
    ('literal-percent', {'user_id':'alice%26run_id%3Dr1', 'run_id':'r2'}),
    ('unicode-user', {'user_id':'user-가', 'agent_id':'bot', 'run_id':'r1'}),
    ('wildcard-user', {'user_id':'user_%', 'run_id':'r1'}),
)
CASES = (
    ('user-all-scopes', {'user_id':'alice'}),
    ('user-and-run', {'user_id':'alice', 'run_id':'r1'}),
    ('agent-all-users', {'agent_id':'bot'}),
    ('run-all-users', {'run_id':'r1'}),
    ('user-and-agent', {'user_id':'alice', 'agent_id':'bot'}),
    ('agent-and-run', {'agent_id':'bot', 'run_id':'r1'}),
    ('exact-triple', {'user_id':'alice', 'agent_id':'bot', 'run_id':'r1'}),
    ('different-user', {'user_id':'bob'}),
    ('no-match', {'user_id':'absent'}),
    ('similar-name', {'user_id':'alice2'}),
    ('literal-delimiters', {'user_id':'alice&run_id=r1'}),
    ('literal-percent', {'user_id':'alice%26run_id%3Dr1'}),
    ('unicode-user', {'user_id':'user-가'}),
    ('wildcard-user', {'user_id':'user_%'}),
)


def snapshot(manager):
    return manager.connection.execute(
        'SELECT id, session_scope, role, content, name, created_at FROM messages ORDER BY id'
    ).fetchall()


def seeded():
    manager = SQLiteManager()
    for label, metadata in CORPUS:
        key = _build_session_scope(metadata)
        manager.save_messages([
            {'role':'user', 'content':f'FICTITIOUS:{label}:old-1'},
            {'role':'assistant', 'content':f'FICTITIOUS:{label}:old-2'},
        ], key)
    manager.add_history('unrelated-audit', None, 'separate audit-table event', 'ADD')
    return manager


def exact_baseline(manager, filters):
    # Same builder -> exact-key cleanup composition used by the proposed SDK fix.
    manager.delete_messages(_build_session_scope(filters))


def delete_everything_mutant(manager, filters):
    # Deliberately defective test-double, never a proposed fix.
    manager.connection.execute('DELETE FROM messages')
    manager.connection.commit()


def no_delete_mutant(manager, filters):
    return None


def check_case(strategy, case):
    name, filters = case
    original = deepcopy(filters)
    manager = seeded()
    try:
        before = snapshot(manager)
        audit_before = manager.get_history('unrelated-audit')
        expected = {f'FICTITIOUS:{label}:old-{i}'
                    for label, metadata in CORPUS
                    if all(metadata.get(k) == v for k, v in filters.items())
                    for i in (1, 2)}
        strategy(manager, filters)
        after = snapshot(manager)
        old_contents = {r[3] for r in before}
        remaining = {r[3] for r in after}
        missed = sorted(expected & remaining)
        extra = sorted((old_contents - remaining) - expected)
        survivors_before = [r for r in before if r[3] not in expected]
        survivors_after = [r for r in after if r[3] not in expected]
        unchanged = survivors_before == survivors_after
        # Readback through native message access after one new turn in each scope.
        resurfaced = []
        unrelated_lost_on_read = []
        for label, metadata in CORPUS:
            key = _build_session_scope(metadata)
            manager.save_messages([{'role':'user','content':f'FICTITIOUS:{label}:new'}], key)
            read = {r['content'] for r in manager.get_last_messages(key)}
            for i in (1, 2):
                marker = f'FICTITIOUS:{label}:old-{i}'
                if marker in expected and marker in read:
                    resurfaced.append(marker)
                elif marker not in expected and marker not in read:
                    unrelated_lost_on_read.append(marker)
        okay = (not missed and not extra and unchanged and not resurfaced and
                not unrelated_lost_on_read and manager.get_history('unrelated-audit') == audit_before
                and filters == original)
        return {'case':name, 'filter':filters, 'expected_deleted_rows':len(expected),
                'actual_deleted_rows':len(old_contents - remaining), 'target_rows_left':missed,
                'unrelated_rows_deleted':extra, 'non_target_rows_identical':unchanged,
                'old_target_messages_read_back':resurfaced,
                'unrelated_messages_missing_on_readback':unrelated_lost_on_read,
                'history_table_unchanged':manager.get_history('unrelated-audit') == audit_before,
                'contract_satisfied':okay}
    finally:
        manager.close()

from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import platform
import sqlite3

ROOT = Path(__file__).resolve().parent


def check_source():
    raw = SOURCE_PATH.read_bytes()
    blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if blob != '0b49c8e8be46779722a7827b2e98319930433d40':
        raise ValueError('Pinned storage module differs')
    return {'git_blob_sha':blob, 'sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw)}


def run():
    source = check_source()
    names = [('native_exact_cleanup', exact_baseline),
             ('in_memory_field_reference', delete_matching_reference),
             ('delete_everything_mutant', delete_everything_mutant),
             ('no_delete_mutant', no_delete_mutant)]
    rows = {}
    for name, strategy in names:
        rows[name] = [check_case(strategy, c) for c in CASES]
    result = {'schema':'memory-scope-contract-review/1', 'checked_utc':datetime.now(timezone.utc).isoformat(),
              'environment':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version},
              'source_commit':'af93b81bc9573be1b78014b5005a0b0d950605bb',
              'source':source, 'fictional_scopes':len(CORPUS), 'conditions':len(CASES),
              'summary':{name:{'contract_satisfied':sum(r['contract_satisfied'] for r in group),
                               'contract_unsatisfied':sum(not r['contract_satisfied'] for r in group),
                               'denominator':len(group)} for name,group in rows.items()},
              'rows':rows, 'new_model_calls':0, 'user_pc_accesses':0,
              'scope':'Native SQLite storage plus canonical builder excerpt; NOT full Memory or AsyncMemory SDK.',
              'candidate_status':'In-memory reference adapter only; no upstream or user-system installation.',
              'not_tested':['vector and entity stores','full SDK add/delete_all prompt path','TypeScript',
                            'async SDK','multi-process races','large-store performance','backup erasure']}
    if not all(r['contract_satisfied'] for r in rows['in_memory_field_reference']):
        raise AssertionError('Reference did not meet the specified test contract')
    if any(r['contract_satisfied'] for r in rows['delete_everything_mutant']):
        raise AssertionError('Deletion-all negative control escaped')
    if not any(not r['contract_satisfied'] for r in rows['no_delete_mutant']):
        raise AssertionError('No-deletion negative control escaped')
    return result





def main():
    global SOURCE_PATH, SQLiteManager
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', required=True, type=Path, help='Unchanged pinned Mem0 storage.py module')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out and args.out.exists():
        raise SystemExit('Choose a new output; previous results are not overwritten.')
    SOURCE_PATH = args.storage.resolve(strict=True)
    if SOURCE_PATH.stat().st_size != 13546:
        raise ValueError('Pinned source size differs; no import performed')
    check_source()
    spec = importlib.util.spec_from_file_location('_scope_review_native_storage', SOURCE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    SQLiteManager = module.SQLiteManager
    report = run()
    if args.out:
        with args.out.open('x', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
