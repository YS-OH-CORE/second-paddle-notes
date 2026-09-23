"""Observation-only follow-up to OpenAI Agents SDK issue #5072.

No SDK patch is applied. A successful script means the stated observations
were reproduced, NOT that the SDK defect is fixed. Scripted model events are
synthetic; RealtimeSession and its public async event iterator are real.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

TARGET = "32edd3c3ecde37a7fb6bf4b082f35f1d8f7f086b"
VECTOR_REF = "98a1189b2bc299f72eefc05997907dfc27491216"
VECTOR_BLOB = "46ab9d5350635735b45827be312c3b0161ddcfca"
VECTOR_PATH = "conformance/vectors/delegation-001-003.json"
VECTOR_URL = f"https://raw.githubusercontent.com/roy-tong/AgentMeasure/{VECTOR_REF}/{VECTOR_PATH}"


def inspect_vectors() -> dict:
    with urllib.request.urlopen(VECTOR_URL, timeout=20) as response:
        raw = response.read(50001)
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    assert blob == VECTOR_BLOB, "Pinned vector bytes changed"
    family = next(v for v in json.loads(raw)["vectors"] if v["id"] == "DELEGATION-003")
    return {
        "source_ref": VECTOR_REF,
        "blob": blob,
        "vector_ids": [v["id"] for v in family["vectors"]],
        "input_top_level_keys": {v["id"]: sorted(v["input"]) for v in family["vectors"]},
        "scope": "Inspection of the linked JSON examples only; AgentMeasure checker NOT executed",
    }


async def observe(label: str, *, handoff: bool, same_name: bool) -> dict:
    from agents.realtime.agent import RealtimeAgent
    from agents.realtime.model_events import (
        RealtimeModelEndOfStreamEvent,
        RealtimeModelToolCallEvent,
        RealtimeModelTurnEndedEvent,
        RealtimeModelTurnStartedEvent,
    )
    from agents.realtime.session import RealtimeSession
    from agents.realtime.testing import ScriptedRealtimeModel

    b = RealtimeAgent(name="worker" if same_name else "b")
    a = RealtimeAgent(name="worker" if same_name else "a", handoffs=[b] if handoff else [])
    assert a is not b

    def identity(agent) -> str:
        if agent is a:
            return "A"
        if agent is b:
            return "B"
        raise AssertionError("Unexpected agent object")

    model = ScriptedRealtimeModel(strict=False)
    events = []
    async with RealtimeSession(model, a, None, run_config={"async_tool_calls": False}) as session:
        await model.emit(RealtimeModelTurnStartedEvent(response_id="r1"))
        if handoff:
            await model.emit(RealtimeModelToolCallEvent(
                name=f"transfer_to_{b.name}", call_id="handoff_1", arguments="{}",
            ))
        await model.emit(RealtimeModelTurnEndedEvent(response_id="r1"))
        await model.emit(RealtimeModelTurnStartedEvent(response_id="r2"))
        await model.emit(RealtimeModelTurnEndedEvent(response_id="r2"))
        await model.emit(RealtimeModelEndOfStreamEvent())
        async for event in session:
            if event.type == "error":
                raise AssertionError(f"Session error: {event.error!r}")
            if event.type in {"agent_start", "agent_end", "handoff"}:
                events.append(event)
        model.assert_complete()
    assert model.closed and not model.listeners, "Model lifecycle not closed"

    starts = [e.agent for e in events if e.type == "agent_start"]
    ends = [e.agent for e in events if e.type == "agent_end"]
    transfers = [e for e in events if e.type == "handoff"]
    assert len(starts) == len(ends) == 2
    assert starts[0] is a and starts[1] is (b if handoff else a)
    assert len(transfers) == int(handoff)
    if handoff:
        assert transfers[0].from_agent is a and transfers[0].to_agent is b
    object_matches = [start is end for start, end in zip(starts, ends)]
    name_matches = [start.name == end.name for start, end in zip(starts, ends)]
    expected_objects = [False, True] if handoff else [True, True]
    assert object_matches == expected_objects, "Observed behavior changed; do not reuse old conclusions"
    assert name_matches == ([False, True] if handoff and not same_name else [True, True])
    trace = []
    for event in events:
        if event.type == "handoff":
            trace.append({"type": event.type, "from": identity(event.from_agent), "to": identity(event.to_agent)})
        else:
            trace.append({"type": event.type, "agent_object_label": identity(event.agent), "display_name": event.agent.name})
    return {
        "scenario": label, "trace": trace,
        "object_owner_matches_per_turn": object_matches,
        "name_only_matches_per_turn": name_matches,
        "model_closed": model.closed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    assert head == TARGET
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
    vector_inspection = inspect_vectors()
    from agents import set_tracing_disabled
    from agents.realtime.session import RealtimeSession
    set_tracing_disabled(True)
    module_path = Path(inspect.getfile(RealtimeSession)).resolve()
    assert module_path == (repo / "src/agents/realtime/session.py").resolve()
    source_sha = hashlib.sha256(module_path.read_bytes()).hexdigest()
    saved_connect, saved_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def blocked_connect(*args, **kwargs):
        raise RuntimeError("OFFLINE_FIXTURE: runtime network connections are not part of this check")

    socket.socket.connect = socket.socket.connect_ex = blocked_connect
    report = {
        "sdk_ref": TARGET,
        "version": importlib.metadata.version("openai-agents"),
        "python": sys.version,
        "session_sha256": source_sha,
        "scope": "Unmodified RealtimeSession, synthetic sequential model events, public async iterator; no WebSocket/audio/provider/usage billing test",
        "vector_inspection": vector_inspection,
        "author": "Zero (ChatGPT), for Youngseok Oh / YS-OH-CORE",
        "observations": [],
        "observations_confirmed": False,
        "sdk_fixed": False,
    }
    try:
        for label, do_handoff, names_equal in [
            ("no_handoff_control", False, False),
            ("handoff_distinct_names", True, False),
            ("handoff_same_display_name", True, True),
        ]:
            row = asyncio.run(asyncio.wait_for(observe(label, handoff=do_handoff, same_name=names_equal), timeout=10))
            report["observations"].append(row)
        report["observations_confirmed"] = True
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        socket.socket.connect, socket.socket.connect_ex = saved_connect, saved_connect_ex
        report["source_unchanged"] = hashlib.sha256(module_path.read_bytes()).hexdigest() == source_sha
        report["checkout_clean"] = not subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
        print("ZERO_TURN_IDENTITY_RESULT " + json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["observations_confirmed"] and report["source_unchanged"] and report["checkout_clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
