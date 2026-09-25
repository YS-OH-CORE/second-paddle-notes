"""A single offline process in a disk-backed LangGraph pause/resume test.

Original report: elizandropacheco, LangGraph #9072.
Supplemental tests: Youngseok Oh and Zero, AI collaboration partners.
Only synthetic inputs, real ToolNode/StateGraph/SQLite, no language model.
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
import threading
import traceback
from typing import Annotated

NETWORK_ATTEMPTS: list[str] = []


def deny_network(*args, **kwargs):
    NETWORK_ATTEMPTS.append("blocked_socket_or_dns")
    raise RuntimeError("Network disabled inside the checkpoint experiment")


socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.getaddrinfo = deny_network
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, Send, interrupt
from typing_extensions import TypedDict


def keep_longest(current: list[str], incoming: list[str]) -> list[str]:
    return incoming if len(incoming) > len(current) else current


class HandoffState(TypedDict):
    messages: Annotated[list, add_messages]
    total: Annotated[int, operator.add]
    best: Annotated[list[str], keep_longest]
    visited: Annotated[list[str], operator.add]


VALUES = {"alpha": (2, ["a"]), "beta": (3, ["b", "c"])}
EVENTS: list[dict] = []
EVENT_LOCK = threading.Lock()


def record(kind: str, **values):
    with EVENT_LOCK:
        EVENTS.append({"kind": kind, **values})


def handoff_tool(name: str):
    @tool(name, description="Return a synthetic parent handoff for a restart test.")
    def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        record("tool", job=name, tool_call_id=tool_call_id)
        amount, batch = VALUES[name]
        return Command(
            graph=Command.PARENT,
            goto=[Send("worker", {"job": name})],
            update={
                "messages": [ToolMessage(content="handoff " + name, name=name,
                                         tool_call_id=tool_call_id, id="msg-" + name)],
                "total": amount,
                "best": list(batch),
            },
        )
    return handoff


def build_graph(saver, order: list[str], stage: str):
    child = StateGraph(HandoffState)
    child.add_node("tools", ToolNode([handoff_tool(n) for n in order], handle_tool_errors=False))
    child.add_edge(START, "tools")
    child.add_edge("tools", END)
    parent = StateGraph(HandoffState)
    parent.add_node("child", child.compile(), destinations=("worker",))

    def approval(state):
        record("approval_enter")
        answer = interrupt({"kind": "before_handoff", "expected": "approve:handoff"})
        if answer != "approve:handoff":
            raise ValueError("Wrong approval resume value")
        record("approval_complete")
        return {}

    def worker(state):
        name = state["job"]
        record("worker_enter", job=name)
        if stage == "after":
            answer = interrupt({"kind": "worker", "job": name, "expected": "approve:" + name})
            if answer != "approve:" + name:
                raise ValueError("Resume response was delivered to the wrong worker")
        record("worker_complete", job=name)
        return {"visited": [name]}

    parent.add_node("worker", worker)
    if stage == "before":
        parent.add_node("approval", approval)
        parent.add_edge(START, "approval")
        parent.add_edge("approval", "child")
    else:
        parent.add_edge(START, "child")
    parent.add_edge("worker", END)
    return parent.compile(checkpointer=saver)


def initial_input(order):
    return {
        "messages": [AIMessage(content="", id="request", tool_calls=[
            {"name": n, "args": {}, "id": "call-" + n, "type": "tool_call"} for n in order
        ])], "total": 0, "best": [], "visited": [],
    }


def snapshot_data(snap):
    values = snap.values or {}
    messages = values.get("messages", [])
    interrupts = [
        {"id": item.id, "value": item.value}
        for task in snap.tasks for item in task.interrupts
    ]
    return {
        "values": {
            "total": values.get("total", 0), "best": values.get("best", []),
            "visited": sorted(values.get("visited", [])),
            "tool_ids": [m.tool_call_id for m in messages if isinstance(m, ToolMessage)],
            "message_ids": [m.id for m in messages],
        },
        "next": list(snap.next),
        "interrupts": sorted(interrupts, key=lambda i: i["id"]),
        "checkpoint_id": (snap.config or {}).get("configurable", {}).get("checkpoint_id"),
    }


def resume_command(before):
    assert before["interrupts"], "No persisted interrupt to resume"
    return Command(resume={
        item["id"]: item["value"]["expected"] for item in before["interrupts"]
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--phase", choices=("seed", "resume", "inspect"), required=True)
    parser.add_argument("--stage", choices=("before", "after"), required=True)
    parser.add_argument("--api", choices=("sync", "async"), required=True)
    parser.add_argument("--order", choices=("alpha,beta", "beta,alpha"), required=True)
    parser.add_argument("--source-module", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = Path(inspect.getfile(ToolNode)).resolve()
    assert source == args.source_module.resolve(), (source, args.source_module)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_sha == args.source_sha256
    if args.phase == "seed":
        assert not args.db.exists(), "Seed must not reuse a database"
    else:
        assert args.db.is_file() and args.db.stat().st_size > 0
    order = args.order.split(",")
    config = {"configurable": {"thread_id": "synthetic-restart-case"},
              "recursion_limit": 12, "max_concurrency": 2}
    report = {"phase": args.phase, "stage": args.stage, "api": args.api,
              "order": order, "pid": os.getpid(), "python": sys.version,
              "source": str(source), "source_sha256": source_sha, "model_calls": 0}

    def drive_sync():
        with SqliteSaver.from_conn_string(str(args.db)) as saver:
            graph = build_graph(saver, order, args.stage)
            before = snapshot_data(graph.get_state(config))
            if args.phase != "inspect":
                data = initial_input(order) if args.phase == "seed" else resume_command(before)
                graph.invoke(data, config, durability="sync")
            after = snapshot_data(graph.get_state(config))
            return before, after

    async def drive_async():
        async with AsyncSqliteSaver.from_conn_string(str(args.db)) as saver:
            graph = build_graph(saver, order, args.stage)
            before = snapshot_data(await graph.aget_state(config))
            if args.phase != "inspect":
                data = initial_input(order) if args.phase == "seed" else resume_command(before)
                await graph.ainvoke(data, config, durability="sync")
            after = snapshot_data(await graph.aget_state(config))
            return before, after

    try:
        before, after = asyncio.run(drive_async()) if args.api == "async" else drive_sync()
        report.update(before=before, after=after, completed=True)
    except Exception as exc:
        report.update(completed=False, error={"type": type(exc).__name__, "message": str(exc)},
                      traceback=traceback.format_exc())
    report.update(events=EVENTS, network_attempts=NETWORK_ATTEMPTS)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)
    return 0 if report["completed"] and not NETWORK_ATTEMPTS else 1


if __name__ == "__main__":
    raise SystemExit(main())
