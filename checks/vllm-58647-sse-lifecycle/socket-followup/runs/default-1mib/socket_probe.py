"""Real loopback disconnect probe. No inference or non-loopback connection.

A small socket-buffer setting deliberately creates a slow-reader condition.
ASGI send/receive are observed without fabricating events or delaying them.
Zero x Youngseok Oh.
"""
import asyncio
import contextlib
import hashlib
import importlib.metadata
import inspect
import json
import os
import platform
import socket
import sys
from pathlib import Path

import uvicorn
from starlette.responses import StreamingResponse
from sse_keep_alive import with_sse_keep_alive


async def one_case(pressure, owner_closes, repeat):
    opened = asyncio.Event()
    closed = asyncio.Event()
    app_done = asyncio.Event()
    release = asyncio.Event()
    state = {"pressure": pressure, "owner_closes": owner_closes, "repeat": repeat,
             "body_entered": [], "body_completed": [], "real_disconnect_received": False,
             "source_finalized_on_response_return": None, "asgi_spec": None}
    references = {}
    initial_tasks = set(asyncio.all_tasks())

    async def source():
        opened.set()
        try:
            if pressure:
                yield "data: " + "x" * (1024 * 1024) + "\n\n"
            await release.wait()
            yield "data: released-only-during-teardown\n\n"
        finally:
            closed.set()

    async def app(scope, receive, send):
        assert scope["type"] == "http"
        state["asgi_spec"] = scope.get("asgi", {}).get("spec_version")
        upstream = source()
        stream = with_sse_keep_alive(upstream, 0.01)
        response = StreamingResponse(stream, media_type="text/event-stream")
        references.update(source=upstream, stream=stream, response=response)

        async def receive_tap():
            message = await receive()
            if message["type"] == "http.disconnect":
                state["real_disconnect_received"] = True
            return message

        async def send_tap(message):
            kind = None
            if message["type"] == "http.response.body" and message.get("body"):
                kind = "data" if len(message["body"]) > 100 else "heartbeat"
                state["body_entered"].append(kind)
            await send(message)
            if kind:
                state["body_completed"].append(kind)
        try:
            if owner_closes:
                async with contextlib.aclosing(stream):
                    await response(scope, receive_tap, send_tap)
            else:
                await response(scope, receive_tap, send_tap)
            state["app_outcome"] = "returned"
        except BaseException as exc:
            state["app_outcome"] = type(exc).__name__
            raise
        finally:
            state["source_finalized_on_response_return"] = closed.is_set()
            app_done.set()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16384)
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    listener.setblocking(False)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                     http="h11", loop="asyncio", lifespan="off", access_log=False,
                     log_level="error", timeout_graceful_shutdown=2))
    server_task = asyncio.create_task(server.serve(sockets=[listener]))
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
    client.setblocking(False)
    writer = None
    try:
        async with asyncio.timeout(10):
            while not server.started:
                if server_task.done():
                    server_task.result()
                await asyncio.sleep(0.005)
            await asyncio.get_running_loop().sock_connect(client, ("127.0.0.1", port))
            reader, writer = await asyncio.open_connection(sock=client, limit=1024)
            writer.write(b"GET /synthetic HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            await writer.drain()
            headers = await reader.readuntil(b"\r\n\r\n")
            state["http_status"] = headers.split(b"\r\n", 1)[0].decode()
            await opened.wait()
            if pressure:
                deadline = asyncio.get_running_loop().time() + 3
                while True:
                    pending_send = len(state["body_entered"]) > len(state["body_completed"])
                    if pending_send and state["body_entered"][-1] == "heartbeat":
                        await asyncio.sleep(0.025)
                        if len(state["body_entered"]) > len(state["body_completed"]):
                            break
                    if asyncio.get_running_loop().time() > deadline:
                        raise TimeoutError("No sustained body-send backpressure observed")
                    await asyncio.sleep(0.005)
            else:
                while "heartbeat" not in state["body_completed"]:
                    await asyncio.sleep(0.005)
            state["body_send_pending_at_client_abort"] = len(state["body_entered"]) > len(state["body_completed"])
            # Abort only this fixture's loopback client; no ASGI event is injected.
            writer.transport.abort()
            await writer.wait_closed()
            await app_done.wait()
            await asyncio.sleep(0)
            state["upstream_advance_pending_before_fixture_teardown"] = sum(
                1 for task in asyncio.all_tasks() - initial_tasks
                if not task.done() and type(task.get_coro()).__name__ == "async_generator_asend")
    except Exception as exc:
        state["probe_error"] = str(exc)
    finally:
        if writer is not None:
            writer.transport.abort()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
        else:
            client.close()
        if "stream" in references:
            try:
                async with asyncio.timeout(2):
                    await references["stream"].aclose()
                    await references["source"].aclose()
            except RuntimeError:
                release.set()
                await asyncio.sleep(0.025)
                await references["stream"].aclose()
                await references["source"].aclose()
        server.should_exit = True
        try:
            await asyncio.wait_for(server_task, 3)
        finally:
            listener.close()
        await asyncio.sleep(0)
        remaining = [t for t in asyncio.all_tasks() - initial_tasks if not t.done()]
        state["fixture_teardown_clean"] = not remaining and (closed.is_set() or not opened.is_set())
        for task in remaining:
            task.cancel()
        if remaining:
            await asyncio.gather(*remaining, return_exceptions=True)
    return state


async def main():
    rows = []
    for pressure in [False, True]:
        for repeat in range(3):
            for closes in [False, True]:
                row = await one_case(pressure, closes, repeat)
                rows.append(row)
                print(json.dumps(row), flush=True)
    report = {"python": platform.python_version(), "os": platform.system(),
              "versions": {n: importlib.metadata.version(n) for n in ["starlette", "anyio", "uvicorn", "h11"]},
              "helper_sha256": hashlib.sha256(Path(__file__).with_name("sse_keep_alive.py").read_bytes()).hexdigest(),
              "response_source_sha256": hashlib.sha256(Path(inspect.getfile(StreamingResponse)).read_bytes()).hexdigest(),
              "controlled_socket_buffers": {"server_send_requested":16384, "client_receive_requested":4096},
              "pressure_data_bytes":1024*1024+8,"listener":"127.0.0.1 only; OS-selected ephemeral port",
              "synthetic_asgi_events":False, "full_vllm_engine_run":False,
              "results": rows}
    Path(__file__).with_name("observations.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    assert all(r["fixture_teardown_clean"] for r in rows), "A fixture did not clean up"
    return 1 if any("probe_error" in r for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
