"""Acceptance/compatibility probes for the unapproved reject-first policy.

Boundary tests use real Future objects populated by the test. Integration
cases execute compiled parent/child StateGraphs. No model or service is used.
"""
import asyncio
import concurrent.futures
import operator
import os
from typing import Annotated

import pytest
from typing_extensions import TypedDict

from langgraph.errors import InvalidUpdateError, ParentCommand
from langgraph.func import entrypoint, task
from langgraph.graph import END, START, StateGraph
from langgraph.pregel import _runner
from langgraph.types import Command

from candidate_boundary import reject_parent_batch


@pytest.fixture(autouse=True)
def variant(monkeypatch):
    mode = os.environ.get("BOUNDARY_VARIANT", "baseline")
    if mode in {"proposal", "skip_guard"}:
        if mode == "proposal":
            monkeypatch.setattr(_runner, "_panic_or_proceed", reject_parent_batch)
        else:
            def guarded(futs, **kwargs):
                # Remove only non-interrupt skip futures. Their exception already
                # propagates through the enclosing task's own Future.
                relevant = {
                    f for f in futs
                    if not (f.done() and not f.cancelled()
                            and isinstance(f.exception(), ParentCommand)
                            and f in _runner.SKIP_RERAISE_SET)
                }
                return reject_parent_batch(relevant, **kwargs)
            monkeypatch.setattr(_runner, "_panic_or_proceed", guarded)
    elif mode != "baseline":
        raise ValueError("Unknown comparison variant")


@pytest.fixture(params=["sync", "async"])
def future_factory(request):
    loop = asyncio.new_event_loop() if request.param == "async" else None
    made = []

    def make(exc=None, *, pending=False):
        future = loop.create_future() if loop else concurrent.futures.Future()
        if not pending:
            if exc is None:
                future.set_result(None)
            else:
                future.set_exception(exc)
        made.append(future)
        return future

    yield make
    for future in made:
        _runner.SKIP_RERAISE_SET.discard(future)
        if not future.done():
            future.cancel()
        elif not future.cancelled():
            future.exception()
    if loop:
        loop.close()


def parent(label="a"):
    return ParentCommand(Command(graph=Command.PARENT, goto="target", update={"events": [label]}))


def test_boundary_single_parent_keeps_identity(future_factory):
    exc = parent()
    with pytest.raises(ParentCommand) as caught:
        _runner._panic_or_proceed({future_factory(exc)})
    assert caught.value is exc


def test_boundary_two_independent_parents_are_explicit(future_factory):
    with pytest.raises(InvalidUpdateError, match="Multiple ParentCommand"):
        _runner._panic_or_proceed({future_factory(parent("a")), future_factory(parent("b"))})


def test_boundary_skipped_child_is_not_a_second_handoff(future_factory):
    exc = parent()
    child, enclosing = future_factory(exc), future_factory(exc)
    _runner.SKIP_RERAISE_SET.add(child)
    with pytest.raises(ParentCommand) as caught:
        _runner._panic_or_proceed({child, enclosing})
    assert caught.value is exc


def test_boundary_skipped_child_alone_is_not_raised(future_factory):
    child = future_factory(parent())
    _runner.SKIP_RERAISE_SET.add(child)
    _runner._panic_or_proceed({child})


def test_boundary_handled_future_is_not_second_handoff(future_factory):
    exc = parent()
    child, enclosing = future_factory(exc), future_factory(exc)
    with pytest.raises(ParentCommand) as caught:
        _runner._panic_or_proceed({child, enclosing}, handled_futures={child})
    assert caught.value is exc


def test_boundary_handled_exception_is_not_raised(future_factory):
    exc = parent()
    _runner._panic_or_proceed({future_factory(exc)}, handled_exception_ids={id(exc)})


def test_boundary_timeout_wins_over_completed_parent(future_factory):
    pending = future_factory(pending=True)
    with pytest.raises(TimeoutError):
        _runner._panic_or_proceed({future_factory(parent()), pending})
    assert pending.cancelled()


def test_boundary_panic_false_does_not_raise_parent(future_factory):
    _runner._panic_or_proceed({future_factory(parent())}, panic=False)


class State(TypedDict):
    events: Annotated[list[str], operator.add]


def build_graph(mode, asynchronous):
    visited = []
    child = StateGraph(State)
    if asynchronous:
        async def alpha(state):
            return Command(graph=Command.PARENT, goto="target", update={"events": ["a"]})

        async def beta(state):
            return Command(graph=Command.PARENT, goto="target", update={"events": ["b"]})
    else:
        def alpha(state):
            return Command(graph=Command.PARENT, goto="target", update={"events": ["a"]})

        def beta(state):
            return Command(graph=Command.PARENT, goto="target", update={"events": ["b"]})
    child.add_node("a", alpha)
    child.add_edge(START, "a")
    if mode == "two":
        child.add_node("b", beta)
        child.add_edge(START, "b")
    outer = StateGraph(State)
    outer.add_node("child", child.compile())
    outer.add_edge(START, "child")

    def target(state):
        visited.append("target")
        return {}
    outer.add_node("target", target)
    outer.add_edge("target", END)
    return outer.compile(), visited


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("mode", ["one", "two"])
def test_compiled_parent_routing(mode, asynchronous):
    graph, visited = build_graph(mode, asynchronous)
    def run():
        return asyncio.run(graph.ainvoke({"events": []})) if asynchronous else graph.invoke({"events": []})
    if mode == "two":
        with pytest.raises(InvalidUpdateError, match="Multiple ParentCommand"):
            run()
        assert visited == []
    else:
        result = run()
        assert result["events"] == ["a"]
        assert visited == ["target"]


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
def test_real_nested_task_preserves_one_public_handoff(asynchronous):
    # Public graph/Command/@task APIs generate the internal bubble naturally.
    # The child task's Future and its caller must not become two handoffs.
    visited, leaf_calls = [], []
    leaf = StateGraph(State)
    if asynchronous:
        async def route(state):
            leaf_calls.append("leaf")
            return Command(graph=Command.PARENT, goto="target", update={"events": ["a"]})
    else:
        def route(state):
            leaf_calls.append("leaf")
            return Command(graph=Command.PARENT, goto="target", update={"events": ["a"]})
    leaf.add_node("route", route)
    leaf.add_edge(START, "route")
    compiled_leaf = leaf.compile()
    if asynchronous:
        @task
        async def inner(state):
            return await compiled_leaf.ainvoke(state)

        async def caller(state):
            return await inner(state)
    else:
        @task
        def inner(state):
            return compiled_leaf.invoke(state)

        def caller(state):
            return inner(state).result()
    outer = StateGraph(State)
    outer.add_node("caller", caller)
    outer.add_edge(START, "caller")

    def target(state):
        visited.append("target")
        return {}
    outer.add_node("target", target)
    outer.add_edge("target", END)
    graph = outer.compile()
    if asynchronous:
        result = asyncio.run(graph.ainvoke({"events": []}))
    else:
        result = graph.invoke({"events": []})
    assert result["events"] == ["a"]
    assert leaf_calls == ["leaf"]
    assert visited == ["target"]
