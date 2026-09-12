"""Exercise the opt-in fallback on actual MCP stdio responses, without a model.

Runs published mcp==2.2.0 unchanged. Two fresh server processes negotiate auto
and legacy respectively. All tool responses are synthetic. No network needed.
"""
# Keep runtime annotations for locally imported protocol result classes.

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys

from result_text import add_structured_fallback

VERSION = '2.2.0'
TOOLS = ['empty_list', 'two_hits', 'empty_string', 'empty_object',
         'explicit_no_content', 'explicit_error']
NETWORK_ATTEMPTS: list[str] = []


def prevent_network() -> None:
    def audit(event, args):
        if event == 'socket.connect' and args[0].family in (socket.AF_INET, socket.AF_INET6):
            NETWORK_ATTEMPTS.append(str(args[1]))
            raise RuntimeError('External connections are disabled in this stdio test.')
    sys.addaudithook(audit)


def write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def server_main(log: Path) -> None:
    from mcp.server.mcpserver import MCPServer
    from mcp_types import CallToolResult
    prevent_network()
    server = MCPServer('structured-result-test')

    def observed(name):
        with log.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'tool': name, 'pid': os.getpid()})+'\n')

    @server.tool()
    def empty_list() -> list[dict[str, str]]:
        """Return an empty synthetic search result."""
        observed('empty_list')
        return []

    @server.tool()
    def two_hits() -> list[dict[str, str]]:
        """Return two synthetic search results."""
        observed('two_hits')
        return [{'name': '가'}, {'name': '나'}]

    @server.tool()
    def empty_string() -> str:
        """Return an explicitly empty text value."""
        observed('empty_string')
        return ''

    @server.tool()
    def empty_object() -> dict[str, str]:
        """Return an empty object rather than a list."""
        observed('empty_object')
        return {}

    @server.tool()
    def explicit_no_content() -> CallToolResult:
        """Return no content and no structured data, without implying no matches."""
        observed('explicit_no_content')
        return CallToolResult(content=[], is_error=False)

    @server.tool()
    def explicit_error() -> CallToolResult:
        """Return a synthetic error flag and structure with no text blocks."""
        observed('explicit_error')
        return CallToolResult(content=[], structured_content={'detail': 'synthetic failure', 'retryable': False}, is_error=True)

    server.run(transport='stdio')


async def exercise(root: Path, mode: str) -> dict:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    from mcp_types import CallToolResult

    log = root/(mode+'-server-calls.jsonl')
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).resolve()), '--server-log', str(log)],
        env={'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})
    rows = []
    async with Client(params, mode=mode, read_timeout_seconds=10, cache=None) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert set(TOOLS) <= names
        for name in TOOLS:
            received = await client.call_tool(name, {})
            wire = received.model_dump(mode='json', by_alias=True, exclude_none=True)
            before = deepcopy(wire)
            projected = add_structured_fallback(wire)
            # Validate the generated consumer view using the installed protocol model.
            CallToolResult.model_validate(projected.result)
            assert wire == before
            assert add_structured_fallback(projected.result).result == projected.result
            assert {k: v for k, v in wire.items() if k != 'content'} == {
                k: v for k, v in projected.result.items() if k != 'content'}
            if name == 'empty_list':
                assert wire['content'] == [] and wire['structuredContent'] == {'result': []}
                assert projected.source == 'structured_content'
                assert json.loads(projected.result['content'][0]['text']) == {'result': []}
            elif name == 'explicit_no_content':
                assert projected.source == 'absent' and projected.result == wire
            elif name == 'explicit_error':
                assert wire['isError'] is True and projected.result['isError'] is True
                assert projected.source == 'structured_content'
            else:
                assert projected.source == 'existing_content' and projected.result == wire
            rows.append({'tool': name, 'received': before, 'consumer_view': projected.result,
                         'source': projected.source, 'original_unchanged': wire == before})
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert Counter(c['tool'] for c in calls) == Counter(TOOLS)
    pids = {c['pid'] for c in calls}
    assert len(pids) == 1 and os.getpid() not in pids
    report = {'mode': mode, 'status': 'passed', 'client_pid': os.getpid(),
              'server_pid': next(iter(pids)), 'tool_calls': calls, 'cases': rows}
    write(root/(mode+'.json'), report)
    return report


def main(root: Path) -> None:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    assert importlib.metadata.version('mcp') == VERSION
    expected = {
        'mcp.client.client': 'f921c7e30be63a4a936aee76ecb6f8e14aba027a',
        'mcp.client.stdio': '3e03eef9efe45e3c7d9fa6e80fe9649a8c1a43c8',
    }
    identities = {}
    for name, wanted in expected.items():
        path = Path(importlib.import_module(name).__file__)
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        identities[name] = {'path': str(path), 'git_blob': blob, 'matches': blob == wanted}
    assert all(item['matches'] for item in identities.values()), identities
    prevent_network()
    reports = [asyncio.run(exercise(root, mode)) for mode in ('auto', 'legacy')]
    assert reports[0]['server_pid'] != reports[1]['server_pid']
    assert NETWORK_ATTEMPTS == []
    summary = {'status': 'passed', 'package_version': VERSION,
        'source_identities': identities, 'modes': reports, 'network_attempts': NETWORK_ATTEMPTS,
        'tool_calls_total': sum(len(r['tool_calls']) for r in reports),
        'scope': 'Unmodified installed SDK; actual stdio server processes and MCP client calls; synthetic tool output; no language model, HTTP frontend, retries or claims about search completeness.'}
    write(root/'summary.json', summary)
    print(json.dumps({'status': 'passed', 'modes': ['auto', 'legacy'], 'tool_calls_total': summary['tool_calls_total']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--out', type=Path)
    group.add_argument('--server-log', type=Path)
    args = parser.parse_args()
    if args.server_log:
        server_main(args.server_log)
    else:
        main(args.out)
