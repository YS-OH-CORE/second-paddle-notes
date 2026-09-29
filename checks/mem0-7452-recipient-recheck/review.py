"""Bounded storage-layer review of Mem0 #7452. No model/provider calls."""
import argparse
import ast
import asyncio
import hashlib
import importlib.util
import json
import logging
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
TARGET = '2bdfb63e5c0b594bcd339b9222f971d416b681fa'
BASE = 'af93b81bc9573be1b78014b5005a0b0d950605bb'
logging.disable(logging.CRITICAL)

def load_storage(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SQLiteManager

# Import the complete unchanged storage module; select only the two unchanged
# serialization helpers from main.py to avoid importing provider dependencies.
main_source = (ROOT / 'mem0/memory/main.py').read_text(encoding='utf-8')
nodes = [node for node in ast.parse(main_source).body
         if isinstance(node, ast.FunctionDef)
         and node.name in {'_build_session_scope', '_escape_scope_value'}]
assert len(nodes) == 2
ns = {'Any': Any}
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'selected_upstream_builders', 'exec'), ns)
build = ns['_build_session_scope']
legacy = ROOT / 'baseline_storage.py'
legacy.write_bytes(urlopen('https://raw.githubusercontent.com/Sai-Sreenath-1819/mem0/'
                          + BASE + '/mem0/memory/storage.py', timeout=25).read())
classes = {'before': load_storage(legacy, 'legacy_storage'),
           'after': load_storage(ROOT / 'mem0/memory/storage.py', 'candidate_storage')}
users = ['alice', 'bob', 'alice-extra', 'ALICE', 'a+b', 'a b', 'a%2Bb',
         'a&run_id=r2', 'a=b', '100%', 'under_score', 'back\\slash',
         '\uD55C\uAE00-id', '\u96EA', 'caf\u00e9', 'cafe\u0301']
agents = [None, 'agent-main', 'a&b']
runs = [None, 'r1', 'r+2']
scopes = [{k: v for k, v in {'user_id': u, 'agent_id': a, 'run_id': r}.items()
           if v is not None} for u in users for a in agents for r in runs]
scopes += [{'agent_id': 'agent-main'}, {'run_id': 'r1'},
           {'agent_id': 'agent-main', 'run_id': 'r1'}]
assert len(set(map(build, scopes))) == len(scopes)
filters = []
for user in users:
    filters.extend([{'user_id': user}, {'user_id': user, 'run_id': 'r1'},
                    {'user_id': user, 'agent_id': 'agent-main'},
                    {'user_id': user, 'agent_id': 'a&b', 'run_id': 'r+2'}])
filters += [{'agent_id': a} for a in agents if a]
filters += [{'run_id': r} for r in runs if r]
filters += [{'agent_id': a, 'run_id': r} for a in agents if a for r in runs if r]

def populate(cls, dictionaries):
    db = cls(':memory:')
    for idx, scope in enumerate(dictionaries):
        db.save_messages([{'role': 'user', 'content': 'SYNTHETIC_%04d' % idx}], build(scope))
    return db

def retained(db):
    return sorted(row[0] for row in db.connection.execute('SELECT content FROM messages'))

def expected_retained(dictionaries, selected):
    return sorted('SYNTHETIC_%04d' % i for i, scope in enumerate(dictionaries)
                  if not all(scope.get(k) == v for k, v in selected.items()))

report = {'target': TARGET, 'baseline': BASE,
          'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
          'platform': platform.system(), 'scope_count': len(scopes),
          'filter_count': len(filters), 'matrix': {}, 'controls': []}
for label, cls in classes.items():
    cells = []
    for selected in filters:
        db = populate(cls, scopes)
        try:
            initial = retained(db)
            assert len(initial) == len(scopes)
            db.delete_messages(build(selected) if label == 'before' else selected)
            actual = retained(db)
            expected = expected_retained(scopes, selected)
            cells.append({'filter': selected, 'passed': actual == expected,
                          'retained_count': len(actual), 'expected_count': len(expected),
                          'unexpectedly_retained': sorted(set(actual) - set(expected)),
                          'unexpectedly_deleted': sorted(set(expected) - set(actual))})
        finally:
            db.connection.close()
    report['matrix'][label] = cells
    print(label, 'matrix', sum(x['passed'] for x in cells), '/', len(cells), flush=True)

cls = classes['after']
db = populate(cls, scopes)
try:
    initial = retained(db)
    db.delete_messages({})
    report['controls'].append({'name': 'storage_empty_filter_is_noop', 'passed': retained(db) == initial})
    asyncio.run(asyncio.to_thread(db.delete_messages, {'user_id': 'alice'}))
    report['controls'].append({'name': 'storage_thread_dispatch',
                              'passed': retained(db) == expected_retained(scopes, {'user_id': 'alice'})})
finally:
    db.connection.close()

triplet = [{'user_id': 'alice', 'run_id': 'r1'},
           {'user_id': 'alice', 'run_id': 'r2'}, {'user_id': 'bob', 'run_id': 'r1'}]
db = populate(cls, triplet)
try:
    initial = retained(db)
    db.connection.execute("CREATE TRIGGER synthetic_delete_failure BEFORE DELETE ON messages "
                          "WHEN OLD.content = 'SYNTHETIC_0001' BEGIN "
                          "SELECT RAISE(ABORT, 'synthetic deletion failure'); END")
    db.connection.commit()
    error_type = None
    try:
        db.delete_messages({'user_id': 'alice'})
    except sqlite3.IntegrityError as error:
        error_type = type(error).__name__
    report['controls'].append({'name': 'failure_propagates_and_transaction_rolls_back',
                              'error_type': error_type,
                              'passed': error_type == 'IntegrityError' and retained(db) == initial})
    db.connection.execute('DROP TRIGGER synthetic_delete_failure')
    db.connection.commit()
    db.delete_messages({'user_id': 'alice'})
    report['controls'].append({'name': 'retry_after_rollback',
                              'passed': retained(db) == ['SYNTHETIC_0002']})
finally:
    db.connection.close()

large = [{'user_id': 'alice', 'run_id': 'r%04d' % i} for i in range(1205)]
large.append({'user_id': 'bob', 'run_id': 'keep'})
db = populate(cls, large)
try:
    db.delete_messages({'user_id': 'alice'})
    report['controls'].append({'name': '1205_target_scopes_plus_unrelated_control',
                              'passed': retained(db) == ['SYNTHETIC_1205']})
finally:
    db.connection.close()

report['source_hashes'] = {str(p.relative_to(ROOT)).replace('\\', '/'):
    {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
     'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(p.read_bytes())).encode()
                                 + b'\0' + p.read_bytes()).hexdigest()}
    for p in [ROOT / 'mem0/memory/storage.py', ROOT / 'mem0/memory/main.py', legacy]}
report['limits'] = ['Complete unchanged SQLiteManager modules with real SQLite databases.',
                    'Only two original serializer helpers are AST-selected from main.py.',
                    'No installed Memory/AsyncMemory, vector store, LLM, hosted API or TypeScript execution.',
                    'The thread control is storage dispatch, not AsyncMemory integration.',
                    'All messages and IDs are synthetic; cases are not independent users or statistical estimates.']
report['candidate_passed'] = all(c['passed'] for c in report['matrix']['after'] + report['controls'])
(ROOT / 'results.json').write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
print('CONTROLS', json.dumps(report['controls']), flush=True)
print('SOURCE_HASHES', json.dumps(report['source_hashes']), flush=True)
print('CANDIDATE_PASSED', report['candidate_passed'], flush=True)
sys.exit(0 if report['candidate_passed'] else 1)
