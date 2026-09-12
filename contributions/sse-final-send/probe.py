"""Deterministic final-send scheduling probe. Only synthetic loopback traffic.

Run each case in a fresh process with PYTHONPATH pointing at the exact source.
No production server, MCP client, or provider is contacted. The receive/final-send
barrier is deliberate scheduling instrumentation, not a measured production rate.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket

import anyio
import httpx
import uvicorn
import sse_starlette.sse as sse

PAYLOAD = "한글 완료 확인"


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


async def direct(mode: str) -> dict:
    entered = anyio.Event()
    row = {"case": mode, "final_entered": False, "final_completed": False,
           "final_cancelled": False, "receive_calls": 0, "disconnect_callbacks": 0}
    sent = []

    async def content():
        yield {"data": PAYLOAD}

    async def send(message):
        final = message["type"] == "http.response.body" and not message.get("more_body", False)
        if final:
            row["final_entered"] = True
            entered.set()
            try:
                if mode == "disconnect":
                    await anyio.sleep_forever()
                elif mode == "delayed":
                    await anyio.sleep(0.02)
            except anyio.get_cancelled_exc_class():
                row["final_cancelled"] = True
                raise
            row["final_completed"] = True
        sent.append({"type": message["type"], "more_body": message.get("more_body"),
                     "body": message.get("body", b"").decode("utf-8")})

    async def receive():
        row["receive_calls"] += 1
        await entered.wait()
        if mode == "disconnect":
            return {"type": "http.disconnect"}
        if row["receive_calls"] == 1:
            return {"type": "http.request", "body": b"", "more_body": False}
        await anyio.sleep_forever()

    async def closed(message):
        row["disconnect_callbacks"] += 1

    response = sse.EventSourceResponse(content(), ping=0, client_close_handler_callable=closed)
    with anyio.fail_after(3):
        await response({"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}}, receive, send)
    row.update(returned=True, active_after=response.active, messages=sent,
               app_exit_after=sse.AppStatus.should_exit)
    return row


async def wire() -> dict:
    entered = asyncio.Event()
    ready = asyncio.Event()
    row = {"case": "loopback", "final_entered": False, "final_completed": False,
           "final_cancelled": False, "receive_calls": 0}

    async def content():
        yield {"data": PAYLOAD}

    async def app(scope, receive, send):
        assert scope["type"] == "http"

        async def delayed_receive():
            row["receive_calls"] += 1
            await entered.wait()
            # Forward the real server event, not an invented disconnect or loop
            # of empty messages. Only the first delivery is delayed by the barrier.
            return await receive()

        async def delayed_send(message):
            final = message["type"] == "http.response.body" and not message.get("more_body", False)
            if final:
                row["final_entered"] = True
                entered.set()
                try:
                    await asyncio.sleep(0.02)
                    await send(message)
                except asyncio.CancelledError:
                    row["final_cancelled"] = True
                    raise
                row["final_completed"] = True
            else:
                await send(message)

        await sse.EventSourceResponse(content(), ping=0)(scope, delayed_receive, delayed_send)
        row["app_returned"] = True

    class ReadyServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()

    server = ReadyServer(uvicorn.Config(app, host="127.0.0.1", port=0,
        lifespan="off", http="h11", interface="asgi3", log_level="error",
        timeout_graceful_shutdown=1))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            await asyncio.wait_for(ready.wait(), timeout=3)
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                try:
                    response = await client.get(f"http://127.0.0.1:{port}/stream")
                    row.update(http_status=response.status_code, body=response.text,
                               complete_http=True, exact_payload=response.text == f"data: {PAYLOAD}\r\n\r\n")
                except httpx.HTTPError as error:
                    row.update(complete_http=False, error_type=type(error).__name__, error=str(error))
            row["app_exit_before_server_shutdown"] = sse.AppStatus.should_exit
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=4)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["normal", "delayed", "disconnect", "loopback"])
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    assert not sse.AppStatus.should_exit, "Each case must begin in a fresh process"
    source = Path(sse.__file__).resolve()
    row = asyncio.run(wire() if args.case == "loopback" else direct(args.case))
    row.update(pid=os.getpid(), source=str(source), source_blob=blob(source.read_bytes()),
               versions={n: importlib.metadata.version(n) for n in ["sse-starlette", "anyio", "starlette", "uvicorn", "httpx"]})
    args.out.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
