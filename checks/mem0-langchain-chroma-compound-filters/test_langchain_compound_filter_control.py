"""Grammar-boundary regression for the limited Langchain.list equality control.

The populated real-backend integration harness establishes selection and deletion
semantics. These tests only establish that list() reaches a Chroma-valid request
without changing existing one-field predicates.
"""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from chromadb.api.types import validate_where

from mem0.vector_stores.langchain import Langchain


def validating_chroma_boundary():
    observed_where = []

    def get(*, where, limit):
        observed_where.append(where)
        # Exercise the real external SDK grammar, before returning an empty result.
        if where is not None:
            validate_where(where)
        return {"ids": [], "metadatas": []}

    client = SimpleNamespace(_collection=SimpleNamespace(get=get))
    return Langchain(client=client), observed_where


@pytest.mark.parametrize(
    "filters",
    [
        {"user_id": "alice", "agent_id": "agent-a"},
        {"user_id": "alice", "agent_id": "agent-a", "run_id": "run-a"},
    ],
    ids=["user-agent", "user-agent-run"],
)
def test_compound_equalities_reach_valid_chroma_request(filters):
    original = deepcopy(filters)
    store, observed_where = validating_chroma_boundary()

    # On unchanged main Chroma's validator rejects the request, list() catches
    # that exception, and the result is [] instead of the successful empty [[]].
    assert store.list(filters=filters, top_k=10) == [[]]
    assert len(observed_where) == 1
    assert filters == original


@pytest.mark.parametrize(
    "filters",
    [
        {"user_id": "alice"},
        {"$and": [{"user_id": "alice"}, {"agent_id": "agent-a"}]},
    ],
    ids=["single-equality", "existing-and"],
)
def test_existing_single_field_predicate_is_preserved(filters):
    original = deepcopy(filters)
    store, observed_where = validating_chroma_boundary()

    assert store.list(filters=filters, top_k=10) == [[]]
    assert len(observed_where) == 1
    assert observed_where[0] is filters
    assert filters == original

