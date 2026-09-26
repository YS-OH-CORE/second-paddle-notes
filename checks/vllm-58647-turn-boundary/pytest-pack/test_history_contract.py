# SPDX-License-Identifier: Apache-2.0
"""Pinned Qwen template controls, not a converter fix or model benchmark.

Youngseok Oh × Zero. Synthetic fixtures only. No network or model calls.
Run: python -m pytest -q test_history_contract.py
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
from typing import Any

from jinja2 import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment
import pytest

ROOT = Path(__file__).resolve().parent
TEMPLATE_SHA256 = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"
OLD = "OLD_TRACE_SENTINEL: A previous task used its own plan."
CURRENT = "CURRENT_TRACE_SENTINEL: The current task needs this tool result."
FIXTURES = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((ROOT / "expected.json").read_text(encoding="utf-8"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def refuse(message: str) -> None:
    raise TemplateError(message)


@pytest.fixture(scope="module")
def template():
    raw = (ROOT / "chat_template.jinja").read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError("Template identity changed; inspect it, do not bless new snapshots automatically")
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    env.globals["raise_exception"] = refuse
    return env.from_string(raw.decode("utf-8"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("Network is not part of this template-only check")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def render(template, messages: list[dict[str, Any]], preserve: bool | None) -> str:
    kwargs = dict(messages=messages, add_generation_prompt=True, enable_thinking=False)
    if preserve is not None:
        kwargs["preserve_thinking"] = preserve
    return template.render(**kwargs)


def expected_for(shape: str, preserve: bool | None) -> dict[str, Any]:
    return next(r for r in EXPECTED if r["shape"] == shape and r["preserve_thinking"] is preserve)


def diagnose(expected_messages, actual_messages, text, expected) -> list[str]:
    """Direct template-boundary checks, not a universal converter-normalization policy.

    The reference messages are independent of the tested renderer's mutable copy.
    vLLM call IDs are checked before rendering; this template need not emit them.
    """
    problems: list[str] = []
    if actual_messages != expected_messages:
        problems.append("template_input_changed")
    visible = [m["content"] for m in expected_messages if m.get("content")]
    if any(text.count(value) != 1 for value in visible):
        problems.append("visible_text_missing_or_duplicated")
    elif [text.index(v) for v in visible] != sorted(text.index(v) for v in visible):
        problems.append("visible_text_order_changed")
    calls = [tc["id"] for m in actual_messages for tc in m.get("tool_calls", [])]
    results = [m.get("tool_call_id") for m in actual_messages if m["role"] == "tool"]
    if calls != results:
        problems.append("tool_result_binding_changed")
    if (OLD in text) != expected["old_trace_retained"] or (CURRENT in text) != expected["current_trace_retained"]:
        problems.append("reasoning_retention_changed")
    if sha(text) != expected["render_sha256"]:
        problems.append("pinned_render_changed")
    return problems


def emit(kind: str, case: str, text: str, **fields) -> None:
    print("CASE " + json.dumps(dict(kind=kind, case=case, render_sha256=sha(text),
          old_retained=OLD in text, current_retained=CURRENT in text, **fields), sort_keys=True))


@pytest.mark.parametrize("expected", EXPECTED, ids=[
    f"{r['shape']}-preserve-{r['preserve_thinking']}" for r in EXPECTED
])
def test_pinned_template_contract(template, expected):
    before = deepcopy(FIXTURES[expected["shape"]])
    actual = deepcopy(before)
    text = render(template, actual, expected["preserve_thinking"])
    problems = diagnose(before, actual, text, expected)
    emit("baseline", f"{expected['shape']}/{expected['preserve_thinking']}", text, problems=problems)
    assert not problems, problems


# These are deliberately bad changes in OUR wrapper, not alleged upstream bugs.
# The first four run with preservation on. Both OLD and CURRENT still survive,
# so a marker-only check would accept them despite the damaged conversation.
MUTATIONS = (
    ("delete_latest_user", "trailing_user_reminder", True, "visible_text_missing_or_duplicated"),
    ("relabel_latest_user_as_tool", "genuine_new_user_turn", True, "template_input_changed"),
    ("reorder_latest_user", "genuine_new_user_turn", True, "visible_text_order_changed"),
    ("break_tool_result_id", "tool_result_only", True, "tool_result_binding_changed"),
    ("ignore_preserve_false", "tool_result_only", False, "reasoning_retention_changed"),
)


@pytest.mark.parametrize("mutation,shape,preserve,required_error", MUTATIONS,
                         ids=[r[0] for r in MUTATIONS])
def test_checker_rejects_bad_change(template, mutation, shape, preserve, required_error):
    before = deepcopy(FIXTURES[shape])
    changed = deepcopy(before)
    used_preserve = preserve
    if mutation == "delete_latest_user":
        changed.pop()
    elif mutation == "relabel_latest_user_as_tool":
        changed[-1]["role"] = "tool"
        changed[-1]["tool_call_id"] = "call_status"
    elif mutation == "reorder_latest_user":
        changed.insert(3, changed.pop())
    elif mutation == "break_tool_result_id":
        changed[-1]["tool_call_id"] = "a_different_call"
    elif mutation == "ignore_preserve_false":
        used_preserve = True
    else:
        raise AssertionError("Unknown mutation")
    text = render(template, changed, used_preserve)
    expected = expected_for(shape, preserve)
    problems = diagnose(before, changed, text, expected)
    marker_only_accepts = ((OLD in text) == expected["old_trace_retained"] and
                           (CURRENT in text) == expected["current_trace_retained"])
    emit("deliberately_bad_wrapper", mutation, text, problems=problems,
         marker_only_accepts=marker_only_accepts,
         same_render_as_valid_case=(sha(text) == expected["render_sha256"]))
    assert required_error in problems, (required_error, problems)
    if preserve is True:
        assert marker_only_accepts, "Negative control no longer isolates marker-only blindness"
    if mutation == "break_tool_result_id":
        assert sha(text) == expected["render_sha256"], "This control should expose the pre-render ID boundary"
