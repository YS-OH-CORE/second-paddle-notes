"""Check the existing final-send candidate against actual MCP initialization.

The restart observation follows skulitom's probe in MCP python-sdk #3494.
Only the last response send is delayed (20 ms). Receives are forwarded unchanged:
no withheld request, invented event, repeated empty receive, or CPU-load claim.
All traffic is synthetic and restricted to a loopback listener.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import socket
from unittest.mock import patch

import anyio
import httpx
import uvicorn
import sse_starlette.sse as sse
from mcp.server.mcpserver import MCPServer
import mcp.server.mcpserver.server as mcp_server_module


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


async def attempt(label: str, servers: list, captures: list) -> dict:
    row = {'label': label, 'exit_before': bool(sse.AppStatus.should_exit),
           'events': [], 'final_entered': False, 'final_completed': False,
           'final_cancelled': False, 'response_complete': False}
    application = MCPServer('synthetic-boundary-probe').streamable_http_app(json_response=False)
    ready = asyncio.Event()

    def note(kind: str, **fields) -> None:
        row['events'].append({'order': len(row['events']) + 1, 'kind': kind, **fields})

    async def observed(scope, receive, send):
        if scope['type'] != 'http':
            return await application(scope, receive, send)

        async def observed_receive():
            message = await receive()
            note('receive', event=message['type'], more_body=message.get('more_body'),
                 body_bytes=len(message.get('body', b'')),
                 after_final_started=row['final_entered'])
            return message

        async def observed_send(message):
            final = message['type'] == 'http.response.body' and not message.get('more_body', False)
            note('send_enter', event=message['type'], more_body=message.get('more_body'),
                 body_bytes=len(message.get('body', b'')), status=message.get('status'))
            if final:
                row['final_entered'] = True
                try:
                    await asyncio.sleep(0.02)
                    await send(message)
                except asyncio.CancelledError:
                    row['final_cancelled'] = True
                    note('final_cancelled')
                    raise
                row['final_completed'] = True
                note('final_completed')
            else:
                await send(message)
        try:
            await application(scope, observed_receive, observed_send)
        finally:
            note('application_returning')

    class ReadyServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()

    server = ReadyServer(uvicorn.Config(observed, host='127.0.0.1', port=0,
        lifespan='on', http='h11', interface='asgi3', log_level='error',
        timeout_graceful_shutdown=2))
    servers.append(server)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(32)
        port = listener.getsockname()[1]
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            await asyncio.wait_for(ready.wait(), timeout=5)
            assert server.started, 'Server startup failed'
            async with httpx.AsyncClient(trust_env=False, timeout=4) as client:
                try:
                    response = await client.post(f'http://127.0.0.1:{port}/mcp',
                        headers={'Accept': 'application/json, text/event-stream'},
                        json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                              'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                              'clientInfo': {'name': 'synthetic-boundary-probe', 'version': '1'}}})
                    row.update(response_complete=True, http_status=response.status_code,
                               content_type=response.headers.get('content-type'), body=response.text)
                    response.raise_for_status()
                    messages = [json.loads(line[6:]) for line in response.text.splitlines()
                                if line.startswith('data: ')]
                    reply = next((m for m in messages if m.get('id') == 1 and 'result' in m), None)
                    row['initialize_succeeded'] = bool(reply and reply['result'].get('protocolVersion') == '2025-06-18')
                    if reply:
                        row['protocol_version'] = reply['result'].get('protocolVersion')
                except httpx.HTTPError as exc:
                    row.update(initialize_succeeded=False, error_type=type(exc).__name__, error=str(exc))
            row['exit_before_requested_shutdown'] = bool(sse.AppStatus.should_exit)
            # Make sure the real watcher had time to capture the first server.
            if label == 'first':
                with anyio.fail_after(3):
                    while not captures:
                        await anyio.sleep(0.01)
                row['watcher_captured_this_server'] = captures[0] is server
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=6)
    return row


async def run(mode: str) -> dict:
    assert not sse.AppStatus.should_exit, 'Start each scenario in a new process'
    captures, servers = [], []
    original = sse._get_uvicorn_server

    def observed_lookup():
        value = original()
        captures.append(value)
        return value

    result = {'mode': mode, 'pid': os.getpid(), 'attempts': [],
              'receive_intervention': 'none; forward real server messages unchanged',
              'final_send_delay_seconds': 0.02, 'diagnostic_global_reset': False}
    with patch.object(sse, '_get_uvicorn_server', observed_lookup):
        first = await attempt('first', servers, captures)
        result['attempts'].append(first)
        assert first.get('initialize_succeeded'), 'First initialization control failed'
        assert first['watcher_captured_this_server'], 'Watcher did not capture the first server'
        if mode != 'fresh':
            with anyio.fail_after(3):
                await sse.EventSourceResponse._listen_for_exit_signal()
            result['exit_after_first_watcher_signal'] = bool(sse.AppStatus.should_exit)
            assert sse.AppStatus.should_exit
            if mode == 'restart_reset':
                # Diagnostic only, intentionally NOT packaged as a production fix.
                sse.AppStatus.should_exit = False
                result['diagnostic_global_reset'] = True
            second = await attempt('second', servers, captures)
            result['attempts'].append(second)
    result['watcher_captures'] = [next((i + 1 for i, server in enumerate(servers) if value is server), None)
                                 for value in captures]
    result['status'] = 'observed'
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['fresh', 'restart', 'restart_reset'])
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source = Path(sse.__file__).resolve()
    result = {'status': 'setup_or_probe_failed', 'mode': args.mode, 'pid': os.getpid()}
    try:
        result.update(asyncio.run(run(args.mode)))
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        result.update(sse_source=str(source), sse_source_blob=blob(source.read_bytes()),
            mcp_server_blob=blob(Path(mcp_server_module.__file__).read_bytes()),
            packages={name: version(name) for name in ['mcp', 'sse-starlette', 'uvicorn', 'httpx', 'anyio', 'starlette', 'h11']})
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
