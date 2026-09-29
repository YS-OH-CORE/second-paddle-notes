"""Probe response-lifecycle cleanup; no vLLM server or inference is started."""
import asyncio
import contextlib
import importlib.metadata
import json
import platform
from dataclasses import dataclass
from pathlib import Path

from starlette.requests import ClientDisconnect
from starlette.responses import StreamingResponse

from sse_keep_alive import with_sse_keep_alive


@dataclass
class State:
    opened: bool = False
    closed: bool = False
    advances: int = 0


async def one_case(mode: str, use_keepalive: bool, owner_closes: bool):
    state = State()
    release = asyncio.Event()
    at_send = asyncio.Event()
    sent = []
    task_set = set(asyncio.all_tasks())

    async def upstream():
        state.opened = True
        try:
            state.advances += 1
            if mode.endswith("data"):
                yield "data: synthetic-first\n\n"
            await release.wait()
            state.advances += 1
            yield "data: synthetic-last\n\n"
        finally:
            state.closed = True

    source = upstream()
    stream = with_sse_keep_alive(source, 0.005 if use_keepalive else 0)
    response = StreamingResponse(stream, media_type="text/event-stream")
    scope = {"type": "http", "method": "GET", "path": "/synthetic",
             "headers": [], "asgi": {"version": "3.0", "spec_version": "2.4"}}

    async def receive():
        await at_send.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body" and message.get("body"):
            sent.append(message["body"].decode())
            at_send.set()
            if mode.startswith("send-error"):
                raise OSError("synthetic closed transport")
            if mode.startswith("disconnect"):
                await asyncio.Event().wait()

    if mode.startswith("disconnect"):
        scope["asgi"]["spec_version"] = "2.3"
    outcome = "returned"
    try:
        async with asyncio.timeout(2):
            if mode.startswith("direct"):
                sent.append(await anext(stream))
                await stream.aclose()
            elif owner_closes:
                async with contextlib.aclosing(stream):
                    await response(scope, receive, send)
            else:
                await response(scope, receive, send)
    except ClientDisconnect:
        outcome = "ClientDisconnect"
    await asyncio.sleep(0)
    pending = [t for t in asyncio.all_tasks() - task_set if not t.done()]
    observed = {"mode": mode, "keepalive": use_keepalive, "owner_closes": owner_closes,
                "opened": state.opened, "closed_on_return": state.closed,
                "pending_tasks_on_return": len(pending), "advance_count": state.advances,
                "frames": sent, "outcome": outcome}
    # Explicit fixture teardown follows observation, never used to claim timely cleanup.
    await stream.aclose()
    await source.aclose()
    await asyncio.sleep(0)
    assert state.closed
    assert not [t for t in asyncio.all_tasks() - task_set if not t.done()]
    observed["fixture_teardown_clean"] = True
    return observed


async def complete_case(raises: bool, owner_closes: bool):
    state = State()
    frames = []
    async def upstream():
        state.opened = True
        try:
            yield "data: first\n\n"
            if raises:
                raise ValueError("synthetic upstream failure")
            yield "data: second\n\n"
        finally:
            state.closed = True
    stream = with_sse_keep_alive(upstream(), 0.005)
    response = StreamingResponse(stream, media_type="text/event-stream")
    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}}
    async def receive():
        await asyncio.Event().wait()
    async def send(message):
        if message["type"] == "http.response.body" and message.get("body"):
            frames.append(message["body"].decode())
    outcome = "returned"
    try:
        if owner_closes:
            async with contextlib.aclosing(stream):
                await response(scope, receive, send)
        else:
            await response(scope, receive, send)
    except ValueError as exc:
        assert str(exc) == "synthetic upstream failure"
        outcome = "ValueError: synthetic upstream failure"
    assert state.closed
    assert frames == (["data: first\n\n"] if raises else ["data: first\n\n", "data: second\n\n"])
    assert outcome == ("ValueError: synthetic upstream failure" if raises else "returned")
    return {"mode": "upstream-error" if raises else "normal-end", "owner_closes": owner_closes,
            "closed_on_return": state.closed, "frames": frames, "outcome": outcome}


async def main():
    cases = [("direct-data", True, False), ("direct-idle", True, False),
             ("send-error-data", False, False), ("send-error-data", False, True)]
    for mode in ["send-error-data", "send-error-idle", "disconnect-data", "disconnect-idle"]:
        for closes in [False, True]:
            cases.append((mode, True, closes))
    results = [await one_case(*case) for case in cases]
    for result in results:
        timely_close = result["mode"].startswith("direct") or result["owner_closes"]
        assert result["closed_on_return"] == timely_close
        expected_pending = 1 if result["mode"].endswith("idle") and not timely_close else 0
        assert result["pending_tasks_on_return"] == expected_pending
    for raises in [False, True]:
        for owner_closes in [False, True]:
            results.append(await complete_case(raises, owner_closes))
    report = {"python": platform.python_version(), "os": platform.system(),
              "versions": {x: importlib.metadata.version(x) for x in ["starlette", "anyio"]},
              "scope": "Real Starlette response and whole unmodified vLLM keepalive module; synthetic ASGI callbacks; no HTTP listener or model", "results": results}
    Path(__file__).with_name("observations.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
