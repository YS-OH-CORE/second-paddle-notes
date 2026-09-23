"""Offline application-level workaround checks for langgraph issue #5225.

This is not a framework fix or a decision on reducer-default semantics.
Initialize additive state explicitly only for a NEW graph/checkpoint thread.
Continuation calls must contain only their new updates, not another default seed.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import inspect
import json
import operator
import os
from pathlib import Path
import socket
import sys
from typing import Annotated, Any

from langgraph.channels.binop import BinaryOperatorAggregate
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class OverallState(BaseModel):
    variable: Annotated[list[str], operator.add] = Field(default_factory=lambda: ["default"])
    counter: Annotated[int, operator.add] = 10


def initial_input(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expand defaults once, before starting a new thread; preserve explicit []/0."""
    return OverallState.model_validate({} if overrides is None else overrides).model_dump()


def build(checkpointer=None):
    def append(state: OverallState):
        return {"variable": ["node"], "counter": 5}

    builder = StateGraph(OverallState)
    builder.add_node("append", append)
    builder.add_edge(START, "append")
    builder.add_edge("append", END)
    return builder.compile(checkpointer=checkpointer)


def blocked_connect(*args, **kwargs):
    raise RuntimeError("This synthetic check must not open network connections")


def main() -> int:
    report: dict[str, Any] = {
        "scope": "real compiled StateGraph, additive reducers, Pydantic input and InMemorySaver; no model or durable-storage test",
        "source_revision": "1211af45b18cab9c0a7efe366ba12f51ad2a9996",
        "python": sys.version,
        "versions": {name: importlib.metadata.version(name) for name in
                     ["langgraph", "langgraph-checkpoint", "langchain-core", "pydantic"]},
        "observations": {},
    }
    obs = report["observations"]
    old_connect, old_connect_ex = socket.socket.connect, socket.socket.connect_ex
    socket.socket.connect = socket.socket.connect_ex = blocked_connect
    try:
        installed = Path(inspect.getfile(BinaryOperatorAggregate)).read_bytes()
        source = Path(os.environ["ZERO_SOURCE_DIR"]) / "libs/langgraph/langgraph/channels/binop.py"
        assert installed == source.read_bytes(), "Installed channel source differs from the pinned checkout"
        report["binop_sha256"] = hashlib.sha256(installed).hexdigest()
        graph = build()
        obs["unseeded_dict"] = graph.invoke({})
        obs["default_model_instance"] = graph.invoke(OverallState())
        obs["exclude_unset_dict"] = graph.invoke(OverallState().model_dump(exclude_unset=True))
        assert obs["unseeded_dict"] == {"variable": ["node"], "counter": 5}
        assert obs["exclude_unset_dict"] == obs["unseeded_dict"]

        original_input = initial_input()
        input_snapshot = json.loads(json.dumps(original_input))
        obs["seeded_defaults"] = graph.invoke(original_input)
        assert original_input == input_snapshot, "Application seed mutated"
        assert obs["seeded_defaults"] == {"variable": ["default", "node"], "counter": 15}
        obs["explicit_nonempty"] = graph.invoke(initial_input({"variable": ["provided"], "counter": 100}))
        assert obs["explicit_nonempty"] == {"variable": ["provided", "node"], "counter": 105}
        obs["explicit_empty_zero"] = graph.invoke(initial_input({"variable": [], "counter": 0}))
        assert obs["explicit_empty_zero"] == {"variable": ["node"], "counter": 5}
        obs["second_fresh_run"] = graph.invoke(initial_input())
        assert obs["second_fresh_run"] == obs["seeded_defaults"]

        resumed = build(InMemorySaver())
        config = {"configurable": {"thread_id": "synthetic-continuation"}}
        obs["checkpoint_first"] = resumed.invoke(initial_input(), config)
        obs["checkpoint_continuation"] = resumed.invoke({"variable": ["next"], "counter": 2}, config)
        assert obs["checkpoint_continuation"] == {
            "variable": ["default", "node", "next", "node"], "counter": 22}
        obs["checkpoint_readback"] = resumed.get_state(config).values
        assert obs["checkpoint_readback"] == obs["checkpoint_continuation"]
        other = {"configurable": {"thread_id": "synthetic-other-thread"}}
        obs["separate_thread"] = resumed.invoke(initial_input(), other)
        assert obs["separate_thread"] == obs["seeded_defaults"]

        bad = {"configurable": {"thread_id": "synthetic-reseed-control"}}
        resumed.invoke(initial_input(), bad)
        obs["incorrect_reseed_control"] = resumed.invoke(initial_input(), bad)
        assert obs["incorrect_reseed_control"] == {
            "variable": ["default", "node", "default", "node"], "counter": 30}

        async def check_async():
            return await build().ainvoke(initial_input())
        obs["async_seeded"] = asyncio.run(check_async())
        assert obs["async_seeded"] == obs["seeded_defaults"]
        report["checks_completed"] = True
    except Exception as exc:
        report["checks_completed"] = False
        report["error"] = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        socket.socket.connect, socket.socket.connect_ex = old_connect, old_connect_ex
        print("ZERO_LANGGRAPH_DEFAULTS_RESULT " + json.dumps(report, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
