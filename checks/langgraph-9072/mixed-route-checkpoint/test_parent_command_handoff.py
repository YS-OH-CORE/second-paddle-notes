"""Parent handoffs must preserve updates, reducers, and dispatched workers."""

import asyncio
import operator
from dataclasses import dataclass
from typing import Annotated, Any

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.errors import InvalidUpdateError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, Send
from pydantic import BaseModel
from typing_extensions import TypedDict


def keep_longest(current: list[str], update: list[str]) -> list[str]:
    return update if len(update) > len(current) else current


class HandoffState(TypedDict):
    messages: Annotated[list, add_messages]
    total: Annotated[int, operator.add]
    best: Annotated[list[str], keep_longest]
    visited: Annotated[list[str], operator.add]
    exclusive: int


@dataclass
class DataclassUpdate:
    messages: list
    total: int
    best: list[str]


class PydanticUpdate(BaseModel):
    messages: list
    total: int
    best: list[str]


VALUES = {"alpha": (2, ["a"]), "beta": (3, ["b", "c"])}
CASES = [
    pytest.param(("alpha",), ("dict",), "sends", False, id="single-send"),
    pytest.param(("alpha", "beta"), ("dict", "dict"), "sends", False, id="siblings"),
    pytest.param(("beta", "alpha"), ("dict", "dict"), "sends", False, id="reversed"),
    pytest.param(("alpha",), ("dict",), "string", False, id="string-control"),
    pytest.param(("alpha", "beta"), ("dict", "tuple"), "sends", False, id="dict-tuple"),
    pytest.param(("alpha", "beta"), ("tuple", "dict"), "sends", False, id="tuple-dict"),
    pytest.param(("alpha", "beta"), ("tuple", "tuple"), "sends", False, id="tuple-tuple"),
    pytest.param(("alpha", "beta"), ("dataclass", "tuple"), "sends", False, id="dataclass-tuple"),
    pytest.param(("alpha", "beta"), ("tuple", "pydantic"), "sends", False, id="tuple-pydantic"),
    pytest.param(("alpha", "beta"), ("none", "tuple"), "sends", False, id="none-tuple"),
    pytest.param(("alpha", "beta"), ("tuple", "none"), "sends", False, id="tuple-none"),
    pytest.param(("alpha", "beta"), ("dict", "dict"), "sends", True, id="unreduced-conflict"),
]


def make_handoff(name: str, shape: str, route: str, conflict: bool):
    @tool(name, description="Return a deterministic parent handoff.")
    def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        amount, batch = VALUES[name]
        values: dict[str, Any] = {
            "messages": [ToolMessage(content="handoff " + name, name=name,
                                     tool_call_id=tool_call_id, id="msg-" + name)],
            "total": amount,
            "best": list(batch),
        }
        if conflict:
            values["exclusive"] = amount
        if shape == "tuple":
            update = tuple(values.items())
        elif shape == "dataclass":
            update = DataclassUpdate(**values)
        elif shape == "pydantic":
            update = PydanticUpdate(**values)
        elif shape == "none":
            update = None
        else:
            assert shape == "dict"
            update = values
        return Command(
            graph=Command.PARENT,
            goto="worker" if route == "string" else [Send("worker", {"job": name})],
            update=update,
        )
    return handoff


@pytest.mark.parametrize("use_async", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("names,shapes,route,conflict", CASES)
def test_parent_handoff_contract(names, shapes, route, conflict, use_async):
    tools = [make_handoff(n, s, route, conflict) for n, s in zip(names, shapes)]
    child = StateGraph(HandoffState)
    child.add_node("tools", ToolNode(tools, handle_tool_errors=False))
    child.add_edge(START, "tools")
    child.add_edge("tools", END)
    parent = StateGraph(HandoffState)
    parent.add_node("child", child.compile(), destinations=("worker",))
    parent.add_node("worker", lambda state: {"visited": [state.get("job", "string")]})
    parent.add_edge(START, "child")
    parent.add_edge("worker", END)
    graph = parent.compile()
    initial = {
        "messages": [AIMessage(content="", id="request", tool_calls=[
            {"name": n, "args": {}, "id": "call-" + n, "type": "tool_call"}
            for n in names])],
        "total": 0, "best": [], "visited": [], "exclusive": 0,
    }
    config = {"recursion_limit": 12, "max_concurrency": 2}

    def invoke():
        return asyncio.run(graph.ainvoke(initial, config)) if use_async else graph.invoke(initial, config)

    if conflict:
        with pytest.raises(InvalidUpdateError, match="exclusive"):
            invoke()
        return

    result = invoke()
    live = [n for n, s in zip(names, shapes) if s != "none"]
    assert result["total"] == sum(VALUES[n][0] for n in live)
    assert result["best"] == max((VALUES[n][1] for n in live), key=len, default=[])
    assert [m.tool_call_id for m in result["messages"] if isinstance(m, ToolMessage)] == ["call-" + n for n in live]
    assert sorted(result["visited"]) == (sorted(names) if route == "sends" else ["string"])
    assert result["exclusive"] == 0
