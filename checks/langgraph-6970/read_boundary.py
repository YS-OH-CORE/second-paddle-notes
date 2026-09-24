"""Synthetic read-boundary check for langgraph #6970; no graph/model calls.

Uses the real JsonPlusSerializer and SqliteSaver. Four fresh reader processes
open an existing scratch database in SQLite mode=ro. Only a trusted fixture
module is temporarily unavailable. No serializer internals are patched.

The required-field guard is application code for this known schema, not a
universal None detector, deserialization hook, or atomic production admission
protocol. Original missing-module report: yangbaechu; existing patches retain
their authorship. Fixture and analysis: Zero (AI assistant), for Youngseok Oh.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys

REV = '7daa3ab49d678a5da75edb08baa87db4a2be52c3'
MODULE = 'zero_checkpoint_fixture'
MODEL_SOURCE = 'from dataclasses import dataclass\n@dataclass\nclass SavedObject:\n    value: int\n'


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def storage_fingerprint(db: Path) -> str:
    def encode(value):
        if isinstance(value, bytes):
            return {'bytes_hex': value.hex()}
        raise TypeError(type(value).__name__)
    with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as conn:
        rows = {
            'checkpoints': conn.execute('SELECT * FROM checkpoints ORDER BY thread_id,checkpoint_ns,checkpoint_id').fetchall(),
            'writes': conn.execute('SELECT * FROM writes ORDER BY thread_id,checkpoint_ns,checkpoint_id,task_id,idx').fetchall(),
        }
    return digest(json.dumps(rows, default=encode, sort_keys=True, separators=(',', ':')).encode())


def describe(value):
    if value is None:
        return None
    return {'module': type(value).__module__, 'class': type(value).__name__, 'value': value.value}


def required_records(values: dict) -> None:
    # These two positions are explicitly non-null in this fictional application.
    # Optional fields are allowed to remain None. This is not a recursive ban.
    for field, value in [('state', values.get('state')), ('nested.record', values.get('nested', {}).get('record'))]:
        if value is None:
            raise RuntimeError('Required checkpoint record unavailable: ' + field)


def child(root: Path, mode: str) -> dict:
    sys.path.insert(0, str(root))
    from langgraph.checkpoint.base import empty_checkpoint
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    from langgraph.checkpoint.sqlite import SqliteSaver

    def blocked(*args, **kwargs):
        raise RuntimeError('No network belongs in the checkpoint fixture')
    socket.socket.connect = socket.socket.connect_ex = blocked
    serde = JsonPlusSerializer(allowed_msgpack_modules=((MODULE, 'SavedObject'),))
    db = root / 'synthetic.sqlite'
    if mode == 'write':
        from zero_checkpoint_fixture import SavedObject
        checkpoint = empty_checkpoint()
        checkpoint['channel_values'] = {'state': SavedObject(123), 'optional': None,
            'nested': {'record': SavedObject(456), 'optional': None}}
        checkpoint['channel_versions'] = {'state': 1, 'optional': 1, 'nested': 1}
        with closing(sqlite3.connect(db, check_same_thread=False)) as conn:
            saver = SqliteSaver(conn, serde=serde)
            config = saver.put({'configurable': {'thread_id': 'synthetic', 'checkpoint_ns': ''}},
                checkpoint, {'source': 'input', 'step': -1}, checkpoint['channel_versions'])
        (root / 'config.json').write_text(json.dumps(config), encoding='utf-8')
        return {'mode': mode, 'checkpoint_config': config, 'storage_sha256': storage_fingerprint(db)}

    present = importlib.util.find_spec(MODULE) is not None
    assert present == (mode in ('available', 'restored'))
    config = json.loads((root / 'config.json').read_text(encoding='utf-8'))
    before = storage_fingerprint(db)
    with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, check_same_thread=False)) as conn:
        saver = SqliteSaver(conn, serde=serde)
        restored = saver.get_tuple(config)
        assert restored is not None
        assert restored.config == config
        values = restored.checkpoint['channel_values']
        row = {'mode': mode, 'module_available': present,
            'state': describe(values['state']), 'nested_record': describe(values['nested']['record']),
            'optional': values['optional'], 'nested_optional': values['nested']['optional'],
            'sqlite_mode': 'ro', 'application_guard': 'not requested'}
        if mode in ('guarded_missing', 'restored'):
            try:
                required_records(values)
            except RuntimeError as exc:
                row['application_guard'] = {'blocked': True, 'error': str(exc)}
            else:
                row['application_guard'] = {'blocked': False}
    after = storage_fingerprint(db)
    row.update(storage_before=before, storage_after=after, logical_rows_unchanged=before == after)
    assert before == after
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--mode', choices=['write', 'available', 'missing', 'guarded_missing', 'restored'])
    args = parser.parse_args()
    root = args.root.resolve()
    if args.mode:
        print(json.dumps(child(root, args.mode), ensure_ascii=False), flush=True)
        return 0
    assert args.repo is not None
    repo = args.repo.resolve()
    root.mkdir(parents=True, exist_ok=False)
    import langgraph.checkpoint.serde.jsonplus as jsonplus
    import langgraph.checkpoint.sqlite as sqlite_saver
    source_matches = {}
    for module, rel in [(jsonplus, 'libs/checkpoint/langgraph/checkpoint/serde/jsonplus.py'),
                        (sqlite_saver, 'libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/__init__.py')]:
        installed = Path(inspect.getfile(module)).read_bytes()
        assert installed == (repo / rel).read_bytes(), 'Installed source differs from pinned checkout'
        source_matches[rel] = digest(installed)
    report = {'source_revision': REV, 'source_matches': source_matches,
        'versions': {n: importlib.metadata.version(n) for n in ['langgraph-checkpoint', 'langgraph-checkpoint-sqlite', 'langchain-core', 'ormsgpack']},
        'scope': 'Real saver and serializer, synthetic records, one writer and four fresh readers; no graph resume or production database',
        'model_calls': 0, 'observations': [], 'success': False}
    fixture = root / (MODULE + '.py')
    hidden = root / (MODULE + '.disabled')
    fixture.write_text(MODEL_SOURCE, encoding='utf-8')
    clean_env = {'PATH': os.environ['PATH'], 'HOME': str(root), 'LANG': 'C.UTF-8',
        'PYTHONDONTWRITEBYTECODE': '1', 'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'}
    try:
        for mode in ['write', 'available', 'missing', 'guarded_missing', 'restored']:
            if mode == 'missing':
                fixture.rename(hidden)
            if mode == 'restored':
                hidden.rename(fixture)
            completed = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()),
                '--root', str(root), '--mode', mode], env=clean_env, cwd=root,
                text=True, capture_output=True, timeout=20)
            (root / (mode + '.stdout.txt')).write_text(completed.stdout, encoding='utf-8')
            (root / (mode + '.stderr.txt')).write_text(completed.stderr, encoding='utf-8')
            completed.check_returncode()
            observation = json.loads(completed.stdout)
            report['observations'].append(observation)
            print('CHECKPOINT_READ_ROW ' + json.dumps(observation), flush=True)
        writer, available, missing, guarded, restored = report['observations']
        for good in [available, restored]:
            assert good['state']['value'] == 123 and good['nested_record']['value'] == 456
            assert good['optional'] is None and good['nested_optional'] is None
        for bad in [missing, guarded]:
            assert bad['state'] is None and bad['nested_record'] is None
        assert guarded['application_guard']['blocked'] is True
        assert restored['application_guard']['blocked'] is False
        assert all(r['storage_before'] == writer['storage_sha256'] for r in report['observations'][1:])
        report['success'] = True
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if hidden.exists():
            hidden.rename(fixture)
        report['fixture_source_restored'] = fixture.read_text(encoding='utf-8') == MODEL_SOURCE
        (root / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('CHECKPOINT_READ_REPORT ' + json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
