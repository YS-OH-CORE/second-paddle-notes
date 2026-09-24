"""LangGraph #9074: query-only Unicode recovery on pre-existing checkpoints.

Uses real sync/async saver imports and SQLite files. The one-line candidate is
samintisar's published proposal, not a new repair claimed by this reviewer.
One unmodified writer process, then fresh base/candidate reader processes.
Use only a disposable checkout: the coordinator temporarily edits one source
file and restores it. No model, live service, or user database is involved.
Zero, AI collaborator with Youngseok Oh (@YS-OH-CORE).
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

REF = '7daa3ab49d678a5da75edb08baa87db4a2be52c3'
UTILS_REL = 'libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/utils.py'
UTILS_BLOB = '7c7e0600053ebb73eafa36d2e617c76eab547475'
OLD = 'json.dumps(query_value, separators=(",", ":"))'
NEW = 'json.dumps(query_value, separators=(",", ":"), ensure_ascii=False)'
# name, stored v, queried v, base hit count, candidate hit count, memory hit count
CASES = [
    ('nested_accent', {'name': 'Jos\u00e9'}, {'name': 'Jos\u00e9'}, 0, 1, 1),
    ('nested_hangul', {'name': '\ubbfc\uc9c0'}, {'name': '\ubbfc\uc9c0'}, 0, 1, 1),
    ('list_accent', ['caf\u00e9'], ['caf\u00e9'], 0, 1, 1),
    ('nested_nonbmp', {'icon': '\U0001f331'}, {'icon': '\U0001f331'}, 0, 1, 1),
    ('nested_unicode_key', {'\uc774\ub984': '\ubbfc\uc9c0'}, {'\uc774\ub984': '\ubbfc\uc9c0'}, 0, 1, 1),
    ('mixed_deep', {'items': [{'label': 'na\u00efve'}], 'count': 2}, {'items': [{'label': 'na\u00efve'}], 'count': 2}, 0, 1, 1),
    ('nested_ascii', {'name': 'Jose'}, {'name': 'Jose'}, 1, 1, 1),
    ('flat_hangul', '\ubbfc\uc9c0', '\ubbfc\uc9c0', 1, 1, 1),
    ('escaped_controls', {'text': 'quote " slash \\ newline\n'}, {'text': 'quote " slash \\ newline\n'}, 1, 1, 1),
    ('literal_escape', {'text': r'\u00e9'}, {'text': r'\u00e9'}, 1, 1, 1),
    ('scalar_bool', True, True, 1, 1, 1),
    ('scalar_null', None, None, 1, 1, 1),
    ('dict_order_residual', {'a': 1, 'b': 2}, {'b': 2, 'a': 1}, 0, 0, 1),
    ('literal_is_not_codepoint', {'text': r'\u00e9'}, {'text': '\u00e9'}, 0, 0, 0),
    ('list_order_distinct', ['caf\u00e9', 'tea'], ['tea', 'caf\u00e9'], 0, 0, 0),
]


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rows_fingerprint(db: Path) -> str:
    def encode(value):
        if isinstance(value, bytes):
            return {'blob_hex': value.hex()}
        raise TypeError(type(value).__name__)
    with closing(sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)) as conn:
        rows = {
            'checkpoints': conn.execute('SELECT * FROM checkpoints ORDER BY thread_id,checkpoint_ns,checkpoint_id').fetchall(),
            'writes': conn.execute('SELECT * FROM writes ORDER BY thread_id,checkpoint_ns,checkpoint_id,task_id,idx').fetchall(),
        }
    return digest(json.dumps(rows, default=encode, sort_keys=True, separators=(',', ':')).encode())


def config(name: str) -> dict:
    return {'configurable': {'thread_id': name, 'checkpoint_ns': ''}}


def fixture_metadata(case):
    yield {'v': deepcopy(case[1]), 'fixture': 'target'}
    yield {'v': '__synthetic_unrelated_record__', 'fixture': 'decoy'}


def execute_child(repo: Path, out: Path, mode: str) -> dict:
    sys.path[:0] = [str(repo / 'libs/checkpoint-sqlite'), str(repo / 'libs/checkpoint')]
    import aiosqlite
    from langgraph.checkpoint.base import empty_checkpoint
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    import langgraph.checkpoint.sqlite.utils as utils
    if Path(inspect.getfile(utils)).resolve() != repo / UTILS_REL:
        raise RuntimeError('Wrong source tree imported')
    # No network is needed after imports. This is not an OS sandbox.
    import socket
    def deny_network(*args, **kwargs):
        raise RuntimeError('Network is outside the metadata fixture')
    socket.socket.connect = socket.socket.connect_ex = deny_network
    report = {'mode': mode, 'source_commit': REF, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'sqlite': sqlite3.sqlite_version,
              'query_source_sha256': digest((repo / UTILS_REL).read_bytes()),
              'versions': {p: importlib.metadata.version(p) for p in
                  ['langgraph-checkpoint', 'langgraph-checkpoint-sqlite', 'langchain-core', 'aiosqlite']},
              'model_calls': 0, 'rows': [], 'success': False}
    sync_db, async_db = out / 'sync.sqlite', out / 'async.sqlite'
    if mode == 'write':
        if sync_db.exists() or async_db.exists():
            raise RuntimeError('Refusing existing fixture paths')
        with SqliteSaver.from_conn_string(str(sync_db)) as saver:
            for case in CASES:
                for metadata in fixture_metadata(case):
                    saver.put(config(case[0]), empty_checkpoint(), metadata, {})
        async def seed_async():
            async with AsyncSqliteSaver.from_conn_string(str(async_db)) as saver:
                for case in CASES:
                    for metadata in fixture_metadata(case):
                        await saver.aput(config(case[0]), empty_checkpoint(), metadata, {})
        asyncio.run(seed_async())
        report['checkpoints_per_database'] = len(CASES) * 2
    else:
        memory = InMemorySaver()
        for case in CASES:
            for metadata in fixture_metadata(case):
                memory.put(config(case[0]), empty_checkpoint(), metadata, {})
        before = {p.name: rows_fingerprint(p) for p in [sync_db, async_db]}
        expected_index = 3 if mode == 'base' else 4
        def inspect_hits(case, backend, hits, all_hits):
            expected = case[5] if backend == 'memory' else case[expected_index]
            row = {'case': case[0], 'backend': backend, 'hits': len(hits), 'expected': expected,
                   'unfiltered_hits': len(all_hits),
                   'target_only': all(x.metadata['fixture'] == 'target' for x in hits)}
            report['rows'].append(row)
            if len(hits) != expected or len(all_hits) != 2 or not row['target_only']:
                raise AssertionError(json.dumps(row))
        with closing(sqlite3.connect(sync_db.as_uri() + '?mode=ro', uri=True, check_same_thread=False)) as conn:
            saver = SqliteSaver(conn)
            for case in CASES:
                cfg, filt = config(case[0]), {'v': deepcopy(case[2])}
                inspect_hits(case, 'sync', list(saver.list(cfg, filter=filt)), list(saver.list(cfg)))
                inspect_hits(case, 'memory', list(memory.list(cfg, filter=filt)), list(memory.list(cfg)))
        async def read_async():
            async with aiosqlite.connect(async_db.as_uri() + '?mode=ro', uri=True) as conn:
                saver = AsyncSqliteSaver(conn)
                for case in CASES:
                    cfg, filt = config(case[0]), {'v': deepcopy(case[2])}
                    inspect_hits(case, 'async', [x async for x in saver.alist(cfg, filter=filt)],
                                 [x async for x in saver.alist(cfg)])
        asyncio.run(read_async())
        after = {p.name: rows_fingerprint(p) for p in [sync_db, async_db]}
        if before != after:
            raise AssertionError('Read changed persisted logical rows')
        report.update(sqlite_read_mode='ro', storage_before=before, storage_after=after, stored_rows_unchanged=True)
    report['storage_sha256'] = {p.name: rows_fingerprint(p) for p in [sync_db, async_db]}
    report['success'] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['write', 'base', 'candidate'])
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    if args.mode:
        result = execute_child(repo, out, args.mode)
        (out / (args.mode + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('UNICODE_METADATA_RESULT ' + json.dumps(result, ensure_ascii=True), flush=True)
        return 0
    out.mkdir(parents=True, exist_ok=False)
    source = repo / UTILS_REL
    original = source.read_bytes()
    actual_blob = hashlib.sha1(b'blob ' + str(len(original)).encode() + b'\0' + original).hexdigest()
    if actual_blob != UTILS_BLOB or original.decode().count(OLD) != 1:
        raise RuntimeError('Refusing an unreviewed or ambiguous source')
    candidate = original.decode().replace(OLD, NEW, 1).encode()
    import difflib
    (out / 'reporter-proposal.patch').write_text(''.join(difflib.unified_diff(
        original.decode().splitlines(keepends=True), candidate.decode().splitlines(keepends=True),
        fromfile='a/' + UTILS_REL, tofile='b/' + UTILS_REL)), encoding='utf-8')
    summary = {'source_commit': REF, 'proposal_by': 'samintisar',
               'issue': 'https://github.com/langchain-ai/langgraph/issues/9074',
               'source_sha256': {'base': digest(original), 'candidate': digest(candidate)},
               'success': False, 'phases': {}}
    try:
        for mode in ['write', 'base', 'candidate']:
            source.write_bytes(candidate if mode == 'candidate' else original)
            home = out / (mode + '-home'); home.mkdir()
            env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'LANG': 'C.UTF-8',
                   'PYTHONDONTWRITEBYTECODE': '1', 'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'}
            p = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--repo', str(repo),
                                '--out', str(out), '--mode', mode], env=env, cwd=home,
                               capture_output=True, text=True, timeout=35)
            (out / (mode + '.stdout.txt')).write_text(p.stdout, encoding='utf-8')
            (out / (mode + '.stderr.txt')).write_text(p.stderr, encoding='utf-8')
            print(p.stdout + p.stderr, flush=True)
            summary['phases'][mode] = {'exit': p.returncode}
            p.check_returncode()
            saved = json.loads((out / (mode + '.json')).read_text(encoding='utf-8'))
            if not saved['success']:
                raise AssertionError('Child report not successful')
            summary['phases'][mode]['storage_sha256'] = saved['storage_sha256']
        hashes = [p['storage_sha256'] for p in summary['phases'].values()]
        if not all(h == hashes[0] for h in hashes):
            raise AssertionError('Storage differs across writer/readers')
        summary.update(success=True, changed_unicode_cases_per_backend=6, scenarios_per_backend=15,
                       sqlite_backends=['sync', 'async'], writes_after_seeding=0,
                       claim='Tested pre-existing rows become queryable without rewriting them; not a universal migration or semantic-JSON fix')
    except Exception as exc:
        summary['error'] = {'type': type(exc).__name__, 'message': str(exc)[:500]}
    finally:
        source.write_bytes(original)
        summary['source_restored'] = source.read_bytes() == original
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        print('UNICODE_METADATA_SUMMARY ' + json.dumps(summary), flush=True)
    return 0 if summary['success'] and summary['source_restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
