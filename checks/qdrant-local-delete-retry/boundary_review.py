"""Exercise committed/unknown deletion outcomes using real Qdrant local mode.
Zero x Youngseok Oh. Only synthetic persistence-boundary failures are injected.
"""
import argparse
import collections
import inspect
import json
import math
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from unittest.mock import patch

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(a.source.resolve()))
NETWORK = []
def audit(event, args):
    if event == 'socket.connect':
        NETWORK.append(str(args[1]))
        raise RuntimeError('Network is not part of this local-only review')
sys.addaudithook(audit)
from qdrant_client import QdrantClient, models
from qdrant_client.local.local_collection import LocalCollection
from qdrant_client.local.persistence import CollectionPersistence
assert Path(inspect.getfile(LocalCollection)).resolve() == (a.source/'qdrant_client/local/local_collection.py').resolve()
TOKENS = {1: [1, 3], 2: [1, 2], 3: [2, 3], 9: [1, 4]}
POINTS = [models.PointStruct(id=i, payload={'owner': 'other' if i == 9 else 'target'},
    vector={'d': [float(i), 1.0], 's': models.SparseVector(indices=t, values=[1.0, 1.0])})
    for i, t in TOKENS.items()]
FILTER = models.Filter(must=[models.FieldCondition(key='owner', match=models.MatchValue(value='target'))])
CASES = ['normal', 'before-first', 'after-sql-middle', 'after-commit-middle', 'unknown-after-commit']
KEYS = {CollectionPersistence.encode_key(i): i for i in TOKENS}
READER = "import sqlite3,sys,json,os;c=sqlite3.connect(sys.argv[1],uri=True); keys=json.loads(sys.argv[2]);print(json.dumps({'pid':os.getpid(),'ids':sorted(keys[r[0]] for r in c.execute('SELECT id FROM points'))}));c.close()"

def create(path, selected=POINTS):
    c = QdrantClient(path=str(path)) if path else QdrantClient(':memory:')
    c.create_collection('case', vectors_config={'d': models.VectorParams(size=2, distance=models.Distance.COSINE)},
        sparse_vectors_config={'s': models.SparseVectorParams(modifier=models.Modifier.IDF)})
    c.upsert('case', points=selected)
    return c

def durable(path):
    r = subprocess.run([sys.executable, '-I', '-S', '-c', READER,
        path.resolve().as_uri()+'?mode=ro', json.dumps(KEYS)], capture_output=True, text=True, timeout=15)
    assert r.returncode == 0, r.stderr
    value = json.loads(r.stdout)
    assert value['pid'] != os.getpid()
    return value

def view(client):
    rows = client.scroll('case', limit=100)[0]
    coll = client._client.collections['case']
    counts = {int(k): int(v) for k, v in coll.sparse_vectors_idf['s'].items() if v}
    scores = {}
    for name, query in [('d', [1.0, 0.0]), ('s', models.SparseVector(indices=[1, 2, 3, 4], values=[1.0]*4))]:
        scores[name] = {str(x.id): float(x.score) for x in client.query_points('case', using=name, query=query, limit=100).points}
    return {'ids': sorted(x.id for x in rows), 'idf': counts, 'scores': scores}

def matches(client, stored):
    actual = view(client)
    expected_counts = dict(collections.Counter(t for i in stored for t in TOKENS[i]))
    fresh = create(None, [pt for pt in POINTS if pt.id in stored])
    try:
        expected = view(fresh)
    finally:
        fresh.close()
    ok = actual['ids'] == stored and actual['idf'] == expected_counts
    for name in ('d', 's'):
        ok = ok and actual['scores'][name].keys() == expected['scores'][name].keys()
        ok = ok and all(math.isclose(v, expected['scores'][name].get(k, float('nan')),
            rel_tol=(1e-6 if name == 'd' else 1e-10), abs_tol=(1e-7 if name == 'd' else 1e-10)) for k, v in actual['scores'][name].items())
    return actual, ok

def outcome(fn):
    try:
        fn(); return {'kind': 'success'}
    except Exception as exc:
        return {'kind': 'error', 'type': type(exc).__name__, 'message': str(exc)}

def run(case):
    directory = a.out/case
    directory.mkdir()
    client = create(directory/'store')
    coll = client._client.collections['case']
    storage = coll.storage
    original_delete = CollectionPersistence.delete
    original_connect = sqlite3.connect
    injected = []
    reconciliation_reads = []
    trigger = 1 if case == 'before-first' else 2
    def fail_delete(self, point_id):
        if self is not storage or point_id != trigger or injected or case == 'normal':
            return original_delete(self, point_id)
        injected.append({'point': point_id, 'boundary': case})
        if case == 'after-sql-middle':
            self.storage.execute('DELETE FROM points WHERE id=?', (self.encode_key(point_id),))
        elif case in ('after-commit-middle', 'unknown-after-commit'):
            original_delete(self, point_id)
        raise sqlite3.OperationalError('SYNTHETIC_'+case)
    def read_gate(database, *args, **kwargs):
        if str(database).endswith('?mode=ro') and str(storage.location.name) in str(database):
            reconciliation_reads.append(str(database))
            if case == 'unknown-after-commit':
                raise sqlite3.OperationalError('SYNTHETIC_RECONCILIATION_READ_FAILURE')
        return original_connect(database, *args, **kwargs)
    record = {'case': case, 'injected': injected, 'pid': os.getpid()}
    try:
        client.create_collection('unaffected', vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE))
        client.upsert('unaffected', points=[models.PointStruct(id=900, vector=[1.0, 0.0])])
        with patch.object(CollectionPersistence, 'delete', new=fail_delete), patch.object(sqlite3, 'connect', side_effect=read_gate):
            first = outcome(lambda: client.delete('case', points_selector=FILTER))
        file_state = durable(storage.location)
        checks = {'first_signal': first['kind'] == ('success' if case == 'normal' else 'error'),
            'fault_exercised': bool(injected) == (case != 'normal'),
            'unrelated_point_on_disk': 9 in file_state['ids']}
        record.update(first=first, durable_after_first=file_state,
            reconciliation_read_count=len(reconciliation_reads))
        if case == 'unknown-after-commit':
            operations = {
                'count': lambda: client.count('case'),
                'scroll': lambda: client.scroll('case'),
                'retrieve': lambda: client.retrieve('case', ids=[9]),
                'dense_query': lambda: client.query_points('case', using='d', query=[1.0, 0.0]),
                'sparse_query': lambda: client.query_points('case', using='s', query=models.SparseVector(indices=[1], values=[1.0])),
                'upsert': lambda: client.upsert('case', points=[POINTS[-1]]),
                'set_payload': lambda: client.set_payload('case', payload={}, points=[9]),
                'delete': lambda: client.delete('case', points_selector=[999])}
            guards = {name: outcome(fn) for name, fn in operations.items()}
            checks['unknown_blocks_tested_operations'] = all(v['kind'] == 'error' and
                'outcome is unknown' in v.get('message', '') for v in guards.values())
            record['unknown_operation_results'] = guards
            checks['reconciliation_attempted'] = bool(reconciliation_reads)
        else:
            record['live_after_first'], checks['state_and_search_match_disk'] = matches(client, file_state['ids'])
        checks['other_collection_still_usable'] = client.count('unaffected').count == 1
        retry = outcome(lambda: client.delete('case', points_selector=FILTER))
        after_retry = durable(storage.location)
        record.update(retry=retry, durable_after_retry=after_retry)
        if case == 'unknown-after-commit':
            checks['retry_blocked'] = retry['kind'] == 'error' and 'outcome is unknown' in retry.get('message', '')
            checks['blocked_calls_did_not_modify_disk'] = after_retry['ids'] == file_state['ids']
        else:
            checks['retry_completed'] = retry['kind'] == 'success' and after_retry['ids'] == [9]
            record['live_after_retry'], checks['retry_search_and_idf'] = matches(client, after_retry['ids'])
    finally:
        client.close()
    recovered = QdrantClient(path=str(directory/'store'))
    try:
        before_recovery = durable(storage.location)
        record['live_after_reopen'], checks['reopen_state_and_search'] = matches(recovered, before_recovery['ids'])
        recovered.delete('case', points_selector=FILTER)
        checks['reopened_recovery'] = durable(storage.location)['ids'] == [9]
    finally:
        recovered.close()
    record.update(checks=checks, passed=all(checks.values()))
    (directory/'result.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    return {'case': case, 'passed': record['passed'], 'checks': checks}

rows = [run(case) for case in CASES]
assert not NETWORK, NETWORK
summary = {'cases': rows, 'passed': sum(x['passed'] for x in rows), 'failed': sum(not x['passed'] for x in rows), 'network_attempts': NETWORK}
(a.out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary), flush=True)
sys.exit(1 if summary['failed'] else 0)
