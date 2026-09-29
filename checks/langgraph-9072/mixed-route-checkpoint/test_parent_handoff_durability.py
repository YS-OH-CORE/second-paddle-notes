"""Real parent-graph route-shape and durable checkpoint regressions for #9072.

Zero x Youngseok Oh. No model, provider, network fixture, or graph mock.
"""

import asyncio
import json
import operator
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, Send, interrupt
from typing_extensions import TypedDict

from langgraph.prebuilt import ToolNode


def keep_longest(current, update):
    return update if len(update) > len(current) else current


class State(TypedDict):
    messages: Annotated[list, add_messages]
    total: Annotated[int, operator.add]
    best: Annotated[list[str], keep_longest]
    visited: Annotated[list[str], operator.add]
    approvals: Annotated[list[str], operator.add]


def make_tool(name, route, journal=None, root_update=False):
    @tool(name, description="Return a synthetic parent handoff.")
    def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        if journal is not None:
            with open(journal, "a", encoding="utf-8") as handle:
                handle.write(name + "\n")
        amount, batch = (2, ["a"]) if name == "alpha" else (3, ["b", "c"])
        update = (
            amount
            if root_update
            else {
                "messages": [
                    ToolMessage(
                        "handoff " + name, tool_call_id=tool_call_id, id="msg-" + name
                    )
                ],
                "total": amount,
                "best": batch,
            }
        )
        send = Send("worker_" + name, {"job": name})
        goto = {
            "list": [send],
            "single": send,
            "tuple": (send,),
            "string": "worker_" + name,
            "empty": [],
        }[route]
        return Command(graph=Command.PARENT, goto=goto, update=update)

    return handoff


def initial(names):
    return {
        "messages": [
            AIMessage(
                "",
                id="request",
                tool_calls=[
                    {"name": n, "args": {}, "id": "call-" + n, "type": "tool_call"}
                    for n in names
                ],
            )
        ],
        "total": 0,
        "best": [],
        "visited": [],
        "approvals": [],
    }


def make_graph(routes, reverse=False, saver=None, gate=False, journal=None):
    names = ("beta", "alpha") if reverse else ("alpha", "beta")
    tools = [make_tool(n, r, journal) for n, r in zip(names, routes)]
    child = StateGraph(State)
    child.add_node("tools", ToolNode(tools, handle_tool_errors=False))
    child.add_edge(START, "tools")
    child.add_edge("tools", END)
    parent = StateGraph(State)
    parent.add_node(
        "child", child.compile(), destinations=("worker_alpha", "worker_beta")
    )

    def worker(name):
        def run(state):
            if "job" in state:
                assert state["job"] == name
            return {"visited": [name]}

        return run

    for name in ("alpha", "beta"):
        parent.add_node("worker_" + name, worker(name))
        parent.add_edge("worker_" + name, "approve" if gate else END)
    if gate:

        def approve(state):
            answer = interrupt(
                {"total": state["total"], "visited": sorted(state["visited"])}
            )
            return {"approvals": [answer]}

        parent.add_node("approve", approve)
        parent.add_edge("approve", END)
    parent.add_edge(START, "child")
    return parent.compile(checkpointer=saver), names


def inspect_result(result):
    return {
        "total": result["total"],
        "best": result["best"],
        "tool_ids": [
            m.tool_call_id for m in result["messages"] if isinstance(m, ToolMessage)
        ],
        "visited": sorted(result["visited"]),
        "approvals": result["approvals"],
    }


ROUTES = [
    ("list", "list"),
    ("list", "single"),
    ("single", "list"),
    ("list", "tuple"),
    ("tuple", "list"),
    ("list", "string"),
    ("string", "list"),
    ("tuple", "single"),
    ("list", "empty"),
]


@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
@pytest.mark.parametrize("routes", ROUTES, ids=lambda x: "-".join(x))
def test_mixed_parent_routes(routes, reverse, use_async):
    graph, names = make_graph(routes, reverse)
    config = {"recursion_limit": 12, "max_concurrency": 2}
    result = (
        asyncio.run(graph.ainvoke(initial(names), config))
        if use_async
        else graph.invoke(initial(names), config)
    )
    actual = inspect_result(result)
    assert actual == {
        "total": 5,
        "best": ["b", "c"],
        "tool_ids": ["call-" + n for n in names],
        "visited": sorted(n for n, r in zip(names, routes) if r != "empty"),
        "approvals": [],
    }


@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
def test_root_reducer_receives_separate_updates(reverse, use_async):
    names = ("beta", "alpha") if reverse else ("alpha", "beta")
    child = StateGraph(State)
    child.add_node(
        "tools",
        ToolNode(
            [make_tool(n, "empty", root_update=True) for n in names],
            handle_tool_errors=False,
        ),
    )
    child.add_edge(START, "tools")
    child.add_edge("tools", END)
    nested = child.compile()
    parent = StateGraph(Annotated[int, operator.add])
    if use_async:

        async def call_child(value):
            return await nested.ainvoke(initial(names))
    else:

        def call_child(value):
            return nested.invoke(initial(names))

    parent.add_node("child", call_child)
    parent.add_edge(START, "child")
    parent.add_edge("child", END)
    graph = parent.compile()
    actual = asyncio.run(graph.ainvoke(0)) if use_async else graph.invoke(0)
    assert actual == 5


def checkpoint_phase(phase, db, report, journal, routes, use_async):
    config = {"configurable": {"thread_id": "synthetic-9072"}, "recursion_limit": 12}

    async def arun():
        async with AsyncSqliteSaver.from_conn_string(db) as saver:
            graph, names = make_graph(routes, saver=saver, gate=True, journal=journal)
            result = await graph.ainvoke(
                initial(names) if phase == "seed" else Command(resume="approved"),
                config,
            )
            state = await graph.aget_state(config)
            return result, state

    if use_async:
        result, state = asyncio.run(arun())
    else:
        with SqliteSaver.from_conn_string(db) as saver:
            graph, names = make_graph(routes, saver=saver, gate=True, journal=journal)
            result = graph.invoke(
                initial(names) if phase == "seed" else Command(resume="approved"),
                config,
            )
            state = graph.get_state(config)
    observation = inspect_result(state.values)
    observation.update(
        {
            "pid": os.getpid(),
            "phase": phase,
            "next": list(state.next),
            "interrupt_count": len(result.get("__interrupt__", ())),
        }
    )
    Path(report).write_text(json.dumps(observation, sort_keys=True), encoding="utf-8")


@pytest.mark.parametrize(
    "use_async", [False, True], ids=["sync-sqlite", "async-sqlite"]
)
@pytest.mark.parametrize(
    "routes",
    [("list", "list"), ("list", "single"), ("list", "string"), ("string", "list")],
    ids=lambda x: "-".join(x),
)
def test_checkpoint_resume_in_a_new_process(tmp_path, routes, use_async):
    db, journal = tmp_path / "checkpoint.db", tmp_path / "tool-calls.txt"
    observations = []
    for phase in ("seed", "resume"):
        report = tmp_path / (phase + ".json")
        run = subprocess.run(
            [
                sys.executable,
                __file__,
                phase,
                str(db),
                str(report),
                str(journal),
                routes[0],
                routes[1],
                "async" if use_async else "sync",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert run.returncode == 0, run.stderr
        observations.append(json.loads(report.read_text(encoding="utf-8")))
    before, after = observations
    assert before["pid"] != after["pid"]
    expected = {
        "total": 5,
        "best": ["b", "c"],
        "tool_ids": ["call-alpha", "call-beta"],
        "visited": ["alpha", "beta"],
    }
    for observation in observations:
        assert {k: observation[k] for k in expected} == expected
    assert before["next"] == ["approve"] and before["interrupt_count"] == 1
    assert before["approvals"] == []
    assert after["next"] == [] and after["approvals"] == ["approved"]
    assert after["interrupt_count"] == 0
    assert sorted(journal.read_text(encoding="utf-8").splitlines()) == ["alpha", "beta"]


if __name__ == "__main__":
    checkpoint_phase(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
        (sys.argv[5], sys.argv[6]),
        sys.argv[7] == "async",
    )
