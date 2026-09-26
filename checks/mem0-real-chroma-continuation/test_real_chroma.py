# SPDX-License-Identifier: Apache-2.0
"""Real local Chroma controls for the existing Mem0 listing review.

Youngseok Oh x Zero. No network, hosted model, real account or user history.
Recipient factory/config/history fixtures remain mocks; storage is real.
"""
from __future__ import annotations
import importlib.util
import inspect
import json
import os
from pathlib import Path
import traceback
import uuid

import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
import pytest
from mem0.memory.main import Memory
from mem0.vector_stores.langchain import Langchain

REPO = Path(os.environ['ZERO_REPO']).resolve()
OUT = Path(os.environ['ZERO_OUTPUT']).resolve()
VARIANT = os.environ['ZERO_VARIANT']
spec = importlib.util.spec_from_file_location('recipient_test_helpers', REPO/'tests/memory/test_main.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
assert Path(inspect.getfile(Langchain)).resolve() == REPO/'mem0/vector_stores/langchain.py'

CASES = ('list_populated', 'get_known_id', 'delete_known_id', 'memory_get_empty',
         'memory_get_populated', 'memory_delete_empty', 'memory_delete_populated',
         'native_scoped_delete')
ALICE_IDS = ['alice-1', 'alice-2', 'alice-3']
ALL_IDS = ALICE_IDS + ['bob-1']


def snapshot(collection):
    data = collection.get(include=['documents', 'metadatas'])
    rows = [{'id': key, 'document': doc, 'metadata': meta} for key, doc, meta in
            zip(data['ids'], data['documents'], data['metadatas'])]
    return sorted(rows, key=lambda row: row['id'])


def jsonable(value):
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    if isinstance(value, (list, tuple)):
        return [jsonable(x) for x in value]
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    return value


@pytest.mark.parametrize('case', CASES)
def test_real_chroma_contract(case, mocker):
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    collection_name = 'zero-public-review-' + uuid.uuid4().hex
    store = Chroma(client=client, collection_name=collection_name, embedding_function=None)
    collection = store._collection
    empty = case.endswith('_empty')
    if not empty:
        collection.add(ids=ALL_IDS, embeddings=[[float(i), 0.0, 1.0] for i in range(4)],
            documents=['synthetic ' + key for key in ALL_IDS],
            metadatas=[{'user_id': 'alice', 'data': 'synthetic ' + key} for key in ALICE_IDS]
                      + [{'user_id': 'bob', 'data': 'synthetic bob-1'}])
    wrapper = Langchain(client=store, collection_name=collection_name)
    memory = helpers._build_memory_instance(mocker, Memory)
    memory.vector_store = wrapper
    mocker.patch('mem0.memory.main.capture_event')
    before = snapshot(collection)
    assert [x['id'] for x in before] == ([] if empty else ALL_IDS)
    row = {'variant': VARIANT, 'case': case, 'before': before,
           'store_class': f'{type(store).__module__}.{type(store).__qualname__}',
           'get_by_ids_owner': store.get_by_ids.__func__.__qualname__,
           'get_by_ids_source': inspect.getsource(store.get_by_ids.__func__),
           'expected_remaining': [x['id'] for x in before]}
    returned = None
    try:
        if case == 'list_populated':
            returned = wrapper.list(filters={'user_id': 'alice'}, top_k=100)
            actual_ids = sorted(x.id for x in returned[0])
            row['output_contract'] = actual_ids == ALICE_IDS
        elif case == 'get_known_id':
            returned = wrapper.get('alice-1')
            row['output_contract'] = returned is not None and returned.id == 'alice-1'
        elif case == 'delete_known_id':
            returned = wrapper.delete('alice-1')
            row['expected_remaining'] = ['alice-2', 'alice-3', 'bob-1']
            row['output_contract'] = True
        elif case.startswith('memory_get_'):
            returned = memory.get_all(filters={'user_id': 'alice'})
            row['output_contract'] = sorted(x['id'] for x in returned['results']) == ([] if empty else ALICE_IDS)
        elif case.startswith('memory_delete_'):
            row['expected_remaining'] = [] if empty else ['bob-1']
            returned = memory.delete_all(user_id='alice')
            row['output_contract'] = returned == {'message': 'Memories deleted successfully!'}
        elif case == 'native_scoped_delete':
            row['expected_remaining'] = ['bob-1']
            returned = collection.delete(where={'user_id': 'alice'})
            row['output_contract'] = True
        else:
            raise AssertionError('Unspecified case')
        row['returned'] = jsonable(returned)
    except Exception as exc:
        row.update(error=type(exc).__name__, error_message=str(exc),
                   traceback=traceback.format_exc(), output_contract=False)
    row['after'] = snapshot(collection)
    row['state_contract'] = [x['id'] for x in row['after']] == row['expected_remaining']
    row['contract_met'] = row['output_contract'] and row['state_contract']
    row['history_calls'] = memory.db.add_history.call_count
    # Store direct deletion is also checked by the retained state, not a success string.
    with (OUT/'observations.jsonl').open('a', encoding='utf-8') as log:
        log.write(json.dumps(row, sort_keys=True) + '\n')
    print('CASE ' + json.dumps(row, sort_keys=True), flush=True)
    assert row['contract_met'], {k: row.get(k) for k in ('case', 'error', 'error_message', 'state_contract')}
