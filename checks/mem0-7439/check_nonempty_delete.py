"""Mem0 #7439: an unsupported listing must not masquerade as an empty store.

Real Memory constructor/get/get_all/delete_all/delete and LangChain FAISS.
The model factories return unused sentinels, embeddings are deterministic test
vectors, and product-notice callbacks are disabled. No credentials or model API.
The fallback and fail-explicit variants are reviewer experiments, not upstream
patches. The coordinator edits only a disposable checkout and restores its bytes.
Zero, AI collaborator with Youngseok Oh (@YS-OH-CORE).
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REF = '989c7da0fc8e4df6342dbb8c448af9816d60d24c'
REL = 'mem0/vector_stores/langchain.py'
BLOB = 'e616a45b18f5bb872981c44336d1ffee3b1e9c13'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def child(repo: Path, out: Path, mode: str) -> dict:
    import socket
    from unittest.mock import patch
    def deny_network(*args, **kwargs):
        raise RuntimeError('Network is outside the synthetic deletion fixture')
    socket.socket.connect = socket.socket.connect_ex = deny_network
    sys.path.insert(0, str(repo))
    from langchain_core.embeddings import Embeddings
    from langchain_community.vectorstores import FAISS
    from mem0 import Memory
    import mem0.memory.main as memory_main
    import mem0.vector_stores.langchain as adapter_module
    assert Path(inspect.getfile(adapter_module)).resolve() == repo / REL
    assert Path(inspect.getfile(Memory)).resolve() == repo / 'mem0/memory/main.py'
    assert memory_main.MEM0_TELEMETRY is False

    class FixtureEmbeddings(Embeddings):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0] + [0.0] * 7 for _ in texts]
        def embed_query(self, text: str) -> list[float]:
            return [1.0] + [0.0] * 7

    class UnusedInference:
        def __getattr__(self, name):
            raise AssertionError('Unexpected inference use: ' + name)

    def outcome(call):
        try:
            return {'returned': call()}
        except Exception as exc:
            return {'error_type': type(exc).__name__, 'error': str(exc)}

    report = {'source_commit': REF, 'mode': mode, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': sha((repo / REL).read_bytes()), 'python': sys.version,
              'versions': {n: importlib.metadata.version(n) for n in
                           ['mem0ai', 'langchain-community', 'langchain-core', 'faiss-cpu']},
              'model_provider_requests': 0, 'fixtures': [], 'success': False}
    with ExitStack() as stack:
        embed_factory = stack.enter_context(patch.object(memory_main.EmbedderFactory, 'create', return_value=UnusedInference()))
        llm_factory = stack.enter_context(patch.object(memory_main.LlmFactory, 'create', return_value=UnusedInference()))
        for name in ['display_first_run_notice', 'display_decay_usage_notice',
                     'detect_decay_usage_from_delete', 'detect_decay_usage_from_delete_all']:
            stack.enter_context(patch.object(memory_main, name, return_value=None))
        for nonempty in (True, False):
            ids = [f'00000000-0000-4000-8000-{i:012d}' for i in range(1, 8)]
            metadata = [{'user_id': 'fixture-alice' if i < 6 else 'fixture-bob',
                         'data': f'synthetic memory {i}', 'fixture': True} for i in range(7)]
            store = FAISS.from_texts([m['data'] for m in metadata], FixtureEmbeddings(),
                                     metadatas=metadata, ids=ids)
            if not nonempty:
                store.delete(ids=ids)
            folder = Path(tempfile.mkdtemp(prefix='nonempty-' if nonempty else 'empty-', dir=out))
            memory = Memory.from_config({'vector_store': {'provider': 'langchain',
                                        'config': {'client': store, 'collection_name': 'synthetic'}},
                                         'history_db_path': str(folder / 'history.sqlite')})
            try:
                assert memory.vector_store.client is store, 'Not observing the configured backing store'
                def docs():
                    return sorted([{'id': d.id, 'content': d.page_content, 'metadata': d.metadata}
                                   for d in store.get_by_ids(ids)], key=lambda d: d['id'])
                before = docs()
                known_alice = [d['id'] for d in before if d['metadata']['user_id'] == 'fixture-alice']
                assert len(known_alice) == (6 if nonempty else 0)
                assert len(before) == (7 if nonempty else 0)
                raw = outcome(lambda: memory.vector_store.list(filters={'user_id': 'fixture-alice'}))
                listed = outcome(lambda: memory.get_all(filters={'user_id': 'fixture-alice'}, show_expired=True))
                deleted = outcome(lambda: memory.delete_all(user_id='fixture-alice'))
                after = docs()
                assert before == after, 'Unexpected mutation during the list/delete_all comparison'
                row = {'nonempty': nonempty, 'alice_records_before': len(known_alice),
                       'all_records_before': len(before), 'list': raw, 'get_all': listed, 'delete_all': deleted,
                       'all_records_after': len(after), 'alice_records_after': len(known_alice),
                       'backing_documents_unchanged': True,
                       'documents_sha256': sha(json.dumps(before, sort_keys=True).encode())}
                if mode == 'base':
                    assert raw == {'returned': None}
                    assert listed.get('error_type') == deleted.get('error_type') == 'TypeError'
                elif mode == 'empty_fallback':
                    assert raw == {'returned': [[]]}
                    assert listed == {'returned': {'results': []}}
                    assert deleted == {'returned': {'message': 'Memories deleted successfully!'}}
                else:
                    assert all(x.get('error_type') == 'NotImplementedError' for x in [raw, listed, deleted])
                if nonempty:
                    # Get by known ID is independent of unsupported enumeration.
                    assert memory.get(ids[0])['memory'] == metadata[0]['data']
                    ranked = store.similarity_search('', filter={'user_id': 'fixture-alice'})
                    row['empty_query_similarity_hits'] = len(ranked)
                    row['default_similarity_k'] = inspect.signature(store.similarity_search).parameters['k'].default
                    assert len(ranked) == 4 < len(known_alice)
                    # Positive control: real targeted deletion does remove exactly one fixture.
                    row['delete_by_id_control'] = memory.delete(ids[0])
                    remaining = docs()
                    assert len(remaining) == 6 and {d['id'] for d in remaining} == set(ids[1:])
                    assert memory.get(ids[0]) is None and memory.get(ids[-1]) is not None
                    row['records_after_targeted_delete'] = len(remaining)
                report['fixtures'].append(row)
            finally:
                memory.close()
        assert embed_factory.call_count == llm_factory.call_count == 2
    report['success'] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['base', 'empty_fallback', 'explicit_error'])
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    if args.mode:
        data = child(repo, out, args.mode)
        (out / (args.mode + '.json')).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print('NONEMPTY_RESULT ' + json.dumps(data), flush=True)
        return 0
    out.mkdir(parents=True, exist_ok=False)
    source = repo / REL
    original = source.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(original)).encode() + b'\0' + original).hexdigest() == BLOB
    text = original.decode()
    fallback_anchor = '                return []\n        except Exception as e:\n            logger.error(f"Error listing vectors from Chroma: {e}")'
    method_anchor = '    def list(self, filters=None, top_k=None):\n        """\n        List all vectors in a collection.\n        """\n'
    assert text.count(fallback_anchor) == text.count(method_anchor) == 1
    variants = {
        'base': text,
        'empty_fallback': text.replace(fallback_anchor, fallback_anchor.replace('        except', '            return [[]]\n        except'), 1),
        'explicit_error': text.replace(method_anchor, method_anchor +
            '        if not (hasattr(self.client, "_collection") and hasattr(self.client._collection, "get")):\n'
            '            raise NotImplementedError("Listing is not implemented for this LangChain client")\n', 1),
    }
    summary = {'source_commit': REF, 'success': False, 'phases': {},
               'scope': 'Real Memory public consumers + real FAISS; fake unused inference factories and notice callbacks',
               'candidate_origin': 'Review of proposed empty fallback; explicit-error is a design control, not an upstream fix'}
    try:
        for mode, variant in variants.items():
            (out / (mode + '.patch')).write_text(''.join(difflib.unified_diff(text.splitlines(True), variant.splitlines(True),
                fromfile='a/' + REL, tofile='b/' + REL)), encoding='utf-8')
            source.write_text(variant, encoding='utf-8')
            home = out / (mode + '-home'); home.mkdir()
            env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'MEM0_DIR': str(home / 'mem0'),
                   'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'MEM0_TELEMETRY': 'False',
                   'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false', 'OMP_NUM_THREADS': '1'}
            p = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--repo', str(repo),
                '--out', str(out), '--mode', mode], cwd=home, env=env, capture_output=True, text=True, timeout=60)
            (out / (mode + '.stdout.txt')).write_text(p.stdout, encoding='utf-8')
            (out / (mode + '.stderr.txt')).write_text(p.stderr, encoding='utf-8')
            print(p.stdout[-24000:] + p.stderr[-6000:], flush=True)
            summary['phases'][mode] = {'exit': p.returncode}
            p.check_returncode()
        summary['success'] = True
    except Exception as exc:
        summary['error'] = {'type': type(exc).__name__, 'message': str(exc)[:500]}
    finally:
        source.write_bytes(original)
        summary['source_restored'] = source.read_bytes() == original
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        print('NONEMPTY_SUMMARY ' + json.dumps(summary), flush=True)
    return 0 if summary['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
