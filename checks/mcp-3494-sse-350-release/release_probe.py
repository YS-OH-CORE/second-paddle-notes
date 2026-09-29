"""Compare published SSE releases across real MCP restarts, without global resets.

All listeners are loopback-only. No model, credentials, or production server.
Zero x Youngseok Oh. Original restart diagnosis/fix belong to their authors.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import inspect
import ipaddress
import json
import os
import platform
import socket
import sys
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import anyio
import httpx2
import uvicorn
from mcp.server.mcpserver import MCPServer
from sse_starlette import sse
from starlette.requests import Request
from starlette.routing import Route

PROTOCOL = "2025-06-18"
SENTINEL = "synthetic-echo-3494"
NETWORK: list[dict[str, Any]] = []


def audit(event: str, args: tuple[Any, ...]) -> None:
    if event not in {"socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname"}:
        return
    address = args[1] if event in {"socket.connect", "socket.bind"} else args[0]
    host = address[0] if isinstance(address, tuple) else address
    allowed = host == "localhost"
    if isinstance(host, str) and not allowed:
        with contextlib.suppress(ValueError):
            allowed = ipaddress.ip_address(host).is_loopback
    NETWORK.append({"event": event, "loopback": allowed})
    if not allowed:
        raise RuntimeError("Non-loopback socket operation is outside this probe")


class ReadyServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config) -> None:
        super().__init__(config)
        self.ready = anyio.Event()
        self.finished = anyio.Event()

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets)
        self.ready.set()


@contextlib.asynccontextmanager
async def running_server(app: Any) -> AsyncIterator[tuple[ReadyServer, str]]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = ReadyServer(uvicorn.Config(app, host="127.0.0.1", port=port,
                             http="h11", log_level="error", access_log=False,
                             lifespan="on", timeout_graceful_shutdown=4))
        async def serve() -> None:
            try:
                await server.serve(sockets=[listener])
            finally:
                server.finished.set()
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(serve)
            try:
                with anyio.fail_after(5):
                    await server.ready.wait()
                yield server, f"http://127.0.0.1:{port}"
            finally:
                server.should_exit = True
                with anyio.fail_after(6):
                    await server.finished.wait()


def make_app() -> tuple[Any, dict[str, Any]]:
    server = MCPServer("synthetic-release-probe", log_level="ERROR")
    state: dict[str, Any] = {"drain_opened": False, "drain_finalized": False,
                            "shutdown_event_observed": False, "echo_calls": []}
    @server.tool()
    async def echo(value: str) -> str:
        """Echo synthetic text after one watcher poll interval."""
        state["echo_calls"].append(value)
        await anyio.sleep(0.6)
        return value
    app = server.streamable_http_app()
    async def drain_endpoint(request: Request) -> sse.EventSourceResponse:
        shutdown = anyio.Event()
        async def events() -> AsyncIterator[dict[str, str]]:
            state["drain_opened"] = True
            try:
                yield {"data": "ready"}
                await shutdown.wait()
                state["shutdown_event_observed"] = True
            finally:
                state["drain_finalized"] = True
        return sse.EventSourceResponse(events(), ping=0, shutdown_event=shutdown,
                                       shutdown_grace_period=1)
    app.router.routes.append(Route("/synthetic-drain", drain_endpoint))
    return app, state


def decode_rpc(response: httpx2.Response, request_id: int) -> dict[str, Any]:
    response.raise_for_status()
    if "text/event-stream" in response.headers.get("content-type", ""):
        messages = [json.loads(line[6:]) for line in response.text.splitlines()
                    if line.startswith("data: ")]
        matching = [message for message in messages if message.get("id") == request_id]
        assert len(matching) == 1, messages
        data = matching[0]
    else:
        data = response.json()
    assert data["id"] == request_id and "error" not in data, data
    return data["result"]


async def exercise_mcp(client: httpx2.AsyncClient, url: str) -> dict[str, Any]:
    observation: dict[str, Any] = {"initialize": False, "tools_list": False,
                                   "echo": False, "failure": None}
    headers = {"Accept": "application/json, text/event-stream"}
    try:
        response = await client.post(url + "/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": PROTOCOL, "capabilities": {},
                "clientInfo": {"name": "synthetic-probe", "version": "1"}}})
        result = decode_rpc(response, 1)
        assert result["protocolVersion"] == PROTOCOL
        observation["initialize"] = True
        session = response.headers.get("mcp-session-id")
        assert session, "No session ID returned"
        headers.update({"Mcp-Session-Id": session, "MCP-Protocol-Version": PROTOCOL})
        response = await client.post(url + "/mcp", headers=headers, json={
            "jsonrpc": "2.0", "method": "notifications/initialized"})
        assert response.status_code == 202
        response = await client.post(url + "/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        result = decode_rpc(response, 2)
        assert [tool["name"] for tool in result["tools"]] == ["echo"]
        observation["tools_list"] = True
        response = await client.post(url + "/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "echo", "arguments": {"value": SENTINEL}}})
        result = decode_rpc(response, 3)
        assert not result.get("isError", False)
        assert any(item.get("text") == SENTINEL for item in result["content"])
        observation["echo"] = True
    except httpx2.HTTPError as exc:
        observation["failure"] = {"type": type(exc).__name__, "message": str(exc)}
    return observation


async def main(scenario: str, output: Path) -> int:
    sys.addaudithook(audit)
    assert sse.AppStatus.should_exit is False
    assert sse.AppStatus.enable_automatic_graceful_drain is True
    report: dict[str, Any] = {"scenario": scenario, "pid": os.getpid(),
        "python": platform.python_version(), "os": platform.system(),
        "versions": {name: importlib.metadata.version(name) for name in
           ("mcp", "mcp-types", "sse-starlette", "starlette", "uvicorn", "anyio", "httpx2", "httpcore2")},
        "source_sha256": hashlib.sha256(Path(inspect.getfile(sse)).read_bytes()).hexdigest(),
        "automatic_drain_enabled": True, "global_state_manually_reset": False,
        "requests": [], "drain": None, "completed": False}
    try:
        async with httpx2.AsyncClient(trust_env=False, timeout=5) as client:
            app, first_state = make_app()
            async with running_server(app) as (server, url):
                first = await exercise_mcp(client, url)
                report["requests"].append({"server": 1, **first})
                assert first["echo"], first
                report["watcher_detected_live_server"] = sse._get_uvicorn_server() is server
                assert report["watcher_detected_live_server"]
                if scenario == "graceful-restart":
                    ready = anyio.Event()
                    finished = anyio.Event()
                    drain: dict[str, Any] = {"clean_http_eof": False}
                    async def consume() -> None:
                        try:
                            async with client.stream("GET", url + "/synthetic-drain") as response:
                                response.raise_for_status()
                                async for line in response.aiter_lines():
                                    if line == "data: ready":
                                        ready.set()
                            drain["clean_http_eof"] = True
                        finally:
                            finished.set()
                    async with anyio.create_task_group() as tasks:
                        tasks.start_soon(consume)
                        with anyio.fail_after(5):
                            await ready.wait()
                        start = time.monotonic()
                        server.should_exit = True
                        with anyio.fail_after(5):
                            await finished.wait()
                            await server.finished.wait()
                        drain.update({"seconds": round(time.monotonic() - start, 3),
                                      "finalized": first_state["drain_finalized"],
                                      "shutdown_event_observed": first_state["shutdown_event_observed"]})
                        report["drain"] = drain
                        assert drain["clean_http_eof"] and drain["finalized"] and drain["shutdown_event_observed"]
            # The release concerns a 0.5 s shutdown poll; allow it to observe the stopped server.
            await anyio.sleep(0.7)
            report["process_exit_flag_after_server1"] = sse.AppStatus.should_exit
            app, second_state = make_app()
            async with running_server(app) as (_server, url):
                second = await exercise_mcp(client, url)
                report["requests"].append({"server": 2, **second})
            report["echo_invocations"] = [first_state["echo_calls"], second_state["echo_calls"]]
            report["completed"] = True
    except Exception as exc:
        # Top-level test reporting retains unexpected harness failures as failures.
        report["harness_error"] = {"type": type(exc).__name__, "message": str(exc)}
    report["network_events"] = NETWORK
    report["external_socket_attempts"] = sum(not event["loopback"] for event in NETWORK)
    report["exit_code"] = 0 if report["completed"] and all(x["echo"] for x in report["requests"]) else 1
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return report["exit_code"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("plain-restart", "graceful-restart"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(anyio.run(main, args.scenario, args.out))
