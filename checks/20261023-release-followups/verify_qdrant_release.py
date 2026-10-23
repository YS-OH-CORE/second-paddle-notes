"""Local-only release follow-up for qdrant-client #1510.
Zero x Youngseok Oh. Synthetic failures; real SQLite; no model/server calls.
Usage: python -I verify_qdrant_release.py --package EXTRACTED_WHEEL --out NEW_DIR
"""
import argparse
import asyncio
import hashlib
import importlib.metadata as metadata
import inspect
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--package', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(args.package.resolve()))
network = []
def audit(event, values):
    if event == 'socket.connect':
        network.append(repr(values[1]))
        raise RuntimeError('No network is allowed in this local-only test')
from qdrant_client import QdrantClient, AsyncQdrantClient, models
from qdrant_client.local.local_collection import LocalCollection
from qdrant_client.local.persistence import CollectionPersistence
source = Path(inspect.getfile(LocalCollection)).resolve()
assert source == (args.package / 'qdrant_client/local/local_collection.py').resolve()
TOKENS = {1: [1, 3], 2: [1, 2], 3: [2, 3], 9: [1, 4]}
points = [models.PointStruct(id=i, payload={'owner': 'other' if i == 9 else 'target'},
    vector={'d': [float(i), 1.0], 's': models.SparseVector(indices=t, values=[1.0, 1.0])})
    for i, t in TOKENS.items()]
selector = models.Filter(must=[models.FieldCondition(key='owner', match=models.MatchValue(value='target'))])
keys = {CollectionPersistence.encode_key(i): i for i in TOKENS}
reader = "import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1],uri=True);k=json.loads(sys.argv[2]);print(json.dumps(sorted(k[x[0]] for x in c.execute('SELECT id FROM points'))));c.close()"
def disk(path):
    p = subprocess.run([sys.executable, '-I', '-S', '-c', reader,
                        path.resolve().as_uri() + '?mode=ro', json.dumps(keys)],
                       capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)
async def call(c, method, *a, **kw):
    r = getattr(c, method)(*a, **kw)
    return await r if inspect.isawaitable(r) else r
async def visible(c):
    rows, _ = await call(c, 'scroll', 'case', limit=100)
    return sorted(p.id for p in rows)
async def one(frontend, mode):
    directory = args.out / (frontend + '-' + mode)
    directory.mkdir()
    cls = QdrantClient if frontend == 'sync' else AsyncQdrantClient
    c = cls(path=str(directory / 'store'))
    checks = {}
    record = {'frontend': frontend, 'injection': mode}
    original = CollectionPersistence.delete
    fired = []
    try:
        await call(c, 'create_collection', 'case',
                   vectors_config={'d': models.VectorParams(size=2, distance=models.Distance.COSINE)},
                   sparse_vectors_config={'s': models.SparseVectorParams(modifier=models.Modifier.IDF)})
        await call(c, 'upsert', 'case', points=points)
        storage = c._client.collections['case'].storage
        def fault(self, point_id):
            if self is not storage or point_id != 2 or fired or mode == 'normal':
                return original(self, point_id)
            fired.append(point_id)
            if mode == 'after-commit':
                original(self, point_id)
            raise sqlite3.OperationalError('SYNTHETIC_' + mode)
        error = None
        with patch.object(CollectionPersistence, 'delete', new=fault):
            try:
                await call(c, 'delete', 'case', points_selector=selector)
            except sqlite3.OperationalError as exc:
                error = str(exc)
        record['first_error'] = error
        record['disk_after_error'] = disk(storage.location)
        record['visible_after_error'] = await visible(c)
        checks['expected_signal'] = (error is None) == (mode == 'normal')
        checks['fault_exercised'] = bool(fired) == (mode != 'normal')
        checks['unrelated_preserved'] = 9 in record['disk_after_error']
        checks['unreached_still_visible'] = mode == 'normal' or 3 in record['visible_after_error']
        await call(c, 'delete', 'case', points_selector=selector)
        record['disk_after_retry'] = disk(storage.location)
        record['visible_after_retry'] = await visible(c)
        checks['retry_removes_targets'] = record['disk_after_retry'] == [9]
        checks['live_matches_retry'] = record['visible_after_retry'] == record['disk_after_retry']
        for name, query in [('d', [1.0, 0.0]), ('s', models.SparseVector(indices=[1, 4], values=[1.0, 1.0]))]:
            response = await call(c, 'query_points', 'case', using=name, query=query, limit=100)
            checks[name + '_query_after_retry'] = sorted(x.id for x in response.points) == [9]
    finally:
        await call(c, 'close')
    reopened = cls(path=str(directory / 'store'))
    try:
        record['visible_after_reopen'] = await visible(reopened)
        checks['reopen_stays_deleted'] = record['visible_after_reopen'] == [9]
    finally:
        await call(reopened, 'close')
    record['checks'] = checks
    record['passed'] = all(checks.values())
    return record
async def main():
    # The Windows event loop creates a local socket pair before test execution.
    # Install the no-connect guard after that bootstrap, before any case.
    sys.addaudithook(audit)
    results = []
    for frontend in ('sync', 'async'):
        for mode in ('normal', 'before-delete', 'after-commit'):
            results.append(await one(frontend, mode))
    assert not network, network
    report = {'scope': 'six sequential local SQLite scenarios; async client front end, not concurrent persistence',
              'version': metadata.version('qdrant-client'), 'python': platform.python_version(),
              'os': platform.system(), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'dependencies': {n: metadata.version(n) for n in ['numpy', 'pydantic', 'portalocker', 'grpcio']},
              'cases': results, 'passed': sum(r['passed'] for r in results),
              'failed': sum(not r['passed'] for r in results), 'network_attempts': network}
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    return 1 if report['failed'] else 0
if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
