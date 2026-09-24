"""Check a forward-migration fix separately from recovery after a skipped migration.

Runs the actual before/after persistence modules with synthetic dbm.dumb files.
Only the persistence layer is exercised, not a historical-client upgrade or a
Qdrant server. The two modules use the same installed model definitions.
No source is patched; no external database, private file, or model is used.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import dbm
import dbm.dumb
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
from pathlib import Path
import pickle
import socket
import sqlite3
import sys

TARGET = 'd54a7f279872a6e65dc5954bbfdb4fd3705ae321'

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Cannot load reviewed source')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def legacy_hashes(root: Path) -> dict[str, str]:
    return {p.name: sha(p.read_bytes()) for p in sorted(root.glob('storage.dbm*')) if p.is_file()}

def sqlite_rows(root: Path) -> list[dict]:
    # Existing scratch DB only; cannot create a database through this URI.
    path = (root / 'storage.sqlite').resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as conn:
        rows = conn.execute('SELECT id, point FROM points ORDER BY id').fetchall()
    return [{'encoded_id': key, 'point_sha256': sha(blob)} for key, blob in rows]

def seed(root: Path, models):
    root.mkdir()
    points = [models.PointStruct(id=1, vector=[1.0, 2.0], payload={'era': 'legacy'}),
              models.PointStruct(id=2, vector=[3.0, 4.0], payload={'era': 'legacy'})]
    with dbm.dumb.open(str(root / 'storage.dbm'), 'n') as store:
        for point in points:
            store[pickle.dumps(point.id)] = pickle.dumps(point)
    assert not (root / 'storage.dbm').exists()
    assert dbm.whichdb(str(root / 'storage.dbm')) == 'dbm.dumb'
    return points

def snapshot(module, root: Path) -> list[dict]:
    store = module.CollectionPersistence(str(root))
    try:
        points = list(store.load())
        return [p.model_dump(mode='json') for p in sorted(points, key=lambda p: p.id)]
    finally:
        store.close()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    from qdrant_client.http import models
    import qdrant_client.local.persistence as installed
    assert Path(inspect.getfile(installed)).read_bytes() == args.candidate.read_bytes()
    base = load_module(args.base, 'zero_review_base_persistence')
    candidate = load_module(args.candidate, 'zero_review_candidate_persistence')
    old_connect = socket.socket.connect
    old_connect_ex = socket.socket.connect_ex
    def blocked(*_args, **_kwargs):
        raise RuntimeError('Network is outside this synthetic migration check')
    socket.socket.connect = socket.socket.connect_ex = blocked
    report = {
        'candidate_commit': TARGET,
        'scope': 'actual source-loaded persistence layer; synthetic dbm.dumb; no full historical upgrade/server',
        'versions': {p: importlib.metadata.version(p) for p in ['qdrant-client', 'pydantic']},
        'python': sys.version,
        'source_sha256': {'base': sha(args.base.read_bytes()), 'candidate': sha(args.candidate.read_bytes())},
        'observations': [], 'success': False, 'new_model_calls': 0,
    }
    try:
        fresh = args.out / 'fresh_legacy'
        points = seed(fresh, models)
        before_legacy = legacy_hashes(fresh)
        result = snapshot(candidate, fresh)
        expected = [p.model_dump(mode='json') for p in points]
        assert result == expected
        assert legacy_hashes(fresh) == {}
        report['observations'].append({'case': 'fresh_legacy_opened_by_candidate',
            'loaded': result, 'legacy_before': before_legacy, 'legacy_after': {},
            'verdict': 'forward migration succeeds'})

        prior = args.out / 'previously_opened_empty_sqlite'
        seed(prior, models)
        before_legacy = legacy_hashes(prior)
        original_read = snapshot(base, prior)
        assert original_read == []
        assert (prior / 'storage.sqlite').exists()
        assert legacy_hashes(prior) == before_legacy
        before_sqlite = sqlite_rows(prior)
        assert before_sqlite == []
        result = snapshot(candidate, prior)
        assert result == []
        assert sqlite_rows(prior) == before_sqlite
        assert legacy_hashes(prior) == before_legacy
        report['observations'].append({'case': 'base_created_empty_sqlite_then_candidate',
            'base_read': original_read, 'candidate_read': result,
            'sqlite_rows_before': before_sqlite, 'sqlite_rows_after': sqlite_rows(prior),
            'legacy_before': before_legacy, 'legacy_after': legacy_hashes(prior),
            'verdict': 'existing SQLite still bypasses migration; legacy bytes retained'})

        newer = args.out / 'previously_opened_with_new_writes'
        seed(newer, models)
        before_legacy = legacy_hashes(newer)
        assert snapshot(base, newer) == []
        store = base.CollectionPersistence(str(newer))
        latest = [models.PointStruct(id=1, vector=[5.0, 6.0], payload={'era': 'newer replacement'}),
                  models.PointStruct(id=3, vector=[7.0, 8.0], payload={'era': 'new-only'})]
        try:
            for point in latest:
                store.persist(point)
        finally:
            store.close()
        before_sqlite = sqlite_rows(newer)
        result = snapshot(candidate, newer)
        assert result == [p.model_dump(mode='json') for p in latest]
        assert sqlite_rows(newer) == before_sqlite
        assert legacy_hashes(newer) == before_legacy
        # Read only trusted fixture bytes; this is not a reader for user DBM files.
        with dbm.open(str(newer / 'storage.dbm'), 'r') as source:
            legacy_ids = sorted(pickle.loads(key) for key in source.keys())
        assert legacy_ids == [1, 2]
        report['observations'].append({'case': 'base_created_sqlite_then_newer_writes_then_candidate',
            'candidate_read': result, 'legacy_ids': legacy_ids, 'sqlite_ids': [p['id'] for p in result],
            'sqlite_rows_before': before_sqlite, 'sqlite_rows_after': sqlite_rows(newer),
            'legacy_before': before_legacy, 'legacy_after': legacy_hashes(newer),
            'verdict': 'newer SQLite records preserved; blind replacement would lose or overwrite them'})
        report['success'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        socket.socket.connect = old_connect
        socket.socket.connect_ex = old_connect_ex
        (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('QDRANT_MIGRATION_BOUNDARY_RESULT ' + json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['success'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
