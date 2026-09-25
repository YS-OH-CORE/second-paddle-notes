"""Offline compiled-graph probes for LangGraph issue 9072.

Original report: elizandropacheco. Reducer-preservation discussion: breken-ai
and 84dnnvbdvp-debug. Supplemental probes: Youngseok Oh x Zero, AI partners.
These local experimental variants are not anyone else's unpublished patch.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import operator
import os
from pathlib import Path
import socket
import sys
import traceback
from typing import Annotated
from typing_extensions import TypedDict


def no_network(*args, **kwargs):
    raise RuntimeError("Network disabled inside offline graph probe")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.getaddrinfo = no_network
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, Send


def longest_batch(left: list[str], right: list[str]) -> list[str]:
    """A configured reducer, deliberately not concatenation."""
    return right if len(right) > len(left) else left


class State(TypedDict):
    messages: Annotated[list, add_messages]
    total: Annotated[int, operator.add]
    best: Annotated[list[str], longest_batch]
    visited: Annotated[list[str], operator.add]


VALUES = {"alpha": (2, ["a"]), "beta": (3, ["b", "c"])}


def command_for(name: str, tool_call_id: str, route: str) -> Command:
    amount, batch = VALUES[name]
    return Command(
        graph=Command.PARENT,
        goto="worker" if route == "string" else [Send("worker", {"job": name})],
        update={
            "messages": [ToolMessage(content="handoff " + name, name=name,
                                     tool_call_id=tool_call_id, id="msg-" + name)],
            "total": amount,
            "best": list(batch),
        },
    )


def make_tool(name: str, route: str):
    @tool(name, description="Deterministic offline handoff fixture")
    def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        return command_for(name, tool_call_id, route)
    return handoff


def snapshot_update(value):
    if isinstance(value, ToolMessage):
        return {"tool_call_id": value.tool_call_id, "id": value.id}
    if isinstance(value, dict):
        return {k: snapshot_update(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [snapshot_update(v) for v in value]
    return value


def run_case(names: list[str], route: str, asynchronous: bool) -> dict:
    name = route + "_" + "_".join(names) + ("_async" if asynchronous else "_sync")
    row = {"case": name, "names": names, "route": route, "async": asynchronous}
    node = ToolNode([make_tool(n, route) for n in names], handle_tool_errors=False)
    commands = [command_for(n, "call-" + n, route) for n in names]
    boundary = node._combine_tool_outputs(commands, "dict")
    row["boundary"] = [
        {"graph": c.graph, "update": snapshot_update(c.update),
         "goto_count": len(c.goto) if isinstance(c.goto, list) else 1}
        for c in boundary if isinstance(c, Command)
    ]
    child_builder = StateGraph(State)
    child_builder.add_node("tools", node)
    child_builder.add_edge(START, "tools")
    child_builder.add_edge("tools", END)
    child = child_builder.compile()
    parent_builder = StateGraph(State)
    parent_builder.add_node("child", child, destinations=("worker",))
    parent_builder.add_node("worker", lambda s: {"visited": [s.get("job", "string")]})
    parent_builder.add_edge(START, "child")
    parent_builder.add_edge("worker", END)
    parent = parent_builder.compile()
    initial = {
        "messages": [AIMessage(content="", id="request", tool_calls=[
            {"name": n, "args": {}, "id": "call-" + n, "type": "tool_call"}
            for n in names])],
        "total": 0, "best": [], "visited": [],
    }
    config = {"recursion_limit": 12, "max_concurrency": 2}
    try:
        result = asyncio.run(parent.ainvoke(initial, config)) if asynchronous else parent.invoke(initial, config)
        tool_ids = [m.tool_call_id for m in result["messages"] if isinstance(m, ToolMessage)]
        row.update(
            total=result["total"], best=result["best"],
            tool_call_ids=tool_ids, visited=sorted(result["visited"]),
            expected_total=sum(VALUES[n][0] for n in names),
            expected_best=max((VALUES[n][1] for n in names), key=len),
            expected_tool_call_ids=["call-" + n for n in names],
            expected_visited=sorted(names) if route == "sends" else ["string"],
        )
        row["preserved"] = all(row[k] == row["expected_" + k] for k in
                               ("total", "best", "tool_call_ids", "visited"))
    except Exception as exc:
        row.update(error=type(exc).__name__, message=str(exc), traceback=traceback.format_exc(), preserved=False)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True)
    parser.add_argument("--source-module", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    actual_source = Path(inspect.getfile(ToolNode)).resolve()
    assert actual_source == args.source_module.resolve(), (actual_source, args.source_module)
    cases = []
    for names, route in ((["alpha"], "sends"), (["alpha", "beta"], "sends"),
                         (["beta", "alpha"], "sends"), (["alpha"], "string")):
        for asynchronous in (False, True):
            row = run_case(names, route, asynchronous)
            cases.append(row)
            print(json.dumps({"variant": args.variant, **row}), flush=True)
    report = {
        "variant": args.variant, "python": sys.version,
        "source": str(actual_source),
        "source_sha256": hashlib.sha256(actual_source.read_bytes()).hexdigest(),
        "cases": cases, "count": len(cases),
        "preserved": sum(c["preserved"] for c in cases),
        "model_calls": 0,
        "scope": "real ToolNode tools and compiled child/parent StateGraphs; synchronous and asynchronous APIs; no mocks or model",
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # A failed preservation check is an observation, not a setup failure.
    assert len(cases) == 8 and len({c["case"] for c in cases}) == 8
    assert not any("error" in c for c in cases), "Unexpected graph runtime error; inspect retained report"
    assert all(c["preserved"] for c in cases if c["route"] == "string"), "String-route control changed"


if __name__ == "__main__":
    main()
