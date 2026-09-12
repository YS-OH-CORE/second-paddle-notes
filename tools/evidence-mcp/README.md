# Two small checks an MCP client can discover and call

This stdio entry exposes the existing approval-trace checker and structured-result
fallback as **two read-only tools**. A compatible host can list their schemas and
invoke them instead of generating integration code. It starts only when launched;
there is no HTTP endpoint, scheduler, account, provider key, or model call.

| Tool | Input | Output |
|---|---|---|
| `check_approval_trace` | Original trace JSON as a string | Request/execution findings, or an explicit unassessed error |
| `project_tool_result` | Original MCP result JSON as a string | An independent consumer view retaining structure and errors |

The first tool reuses `../approval-trace-check/audit.js` v0.1.1. The second reuses
`../mcp-result-text/result_text.py`. Neither implementation is copied or changed.
Startup checks their precise Git blob identities; after an intentional helper
update, review and test the bridge before changing those pins.

## Start from a repository checkout

Requirements: Python 3.10+ and Node.js (tested version will be in the run evidence).
Create a disposable environment or use your application's managed environment:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r tools/evidence-mcp/requirements.txt
.venv/bin/python tools/evidence-mcp/server.py
```

On Windows, the interpreter is `.venv\Scripts\python.exe`. Running this in a terminal
waits for protocol input. It is not an interactive chat. Configure a host that
supports launching stdio MCP servers with the absolute interpreter path as its
command and the absolute `server.py` path as its only argument. Host configuration
formats differ; no host application has been silently configured by this project.
Keep the two sibling utility folders in the checkout. Node must be on PATH.

## Data and error contract

Inputs are original JSON **strings**, so duplicate object members are not lost in
a caller-side parse/reserialize. Each string is limited to 1 MiB UTF-8. The server
runs a fixed Node shim over stdin with a three-second limit, never a caller-supplied
command, file path, or shell expression. The JSON result path uses duplicate-aware
parsing and SDK validation before producing a view.

A detected approval mismatch is successful *analysis*: `isError=false` with
`status=violations_observed`. An unreadable or ambiguous trace is `isError=true`
and `status=not_assessed`, with no invented success counters. No execution in the
trace is separately reported as `no_execution_observed`. Diagnostics use fixed
codes and numeric positions rather than echoing invalid supplied values.

For `project_tool_result`, an original `isError=true` stays true inside the returned
view **and on the outer tool result**. Existing text or media blocks are retained;
missing structured data remains absent. The original response should remain in the
caller's own records. The view is a presentation change, not a newly signed source.

Descriptions and data may contain instruction-like text; nothing here evaluates it
or turns it into a command. The consuming host remains responsible for treating
all returned content as tool data. This does not authenticate consent, authorize
action, prove a log complete, prevent prompt injection in a consuming model, or
establish that a missing search hit does not exist. Request IDs/scopes and projected
payloads are returned to the caller; the host's normal data handling still applies.

The tool bodies do not write caller files or initiate network requests. Normal
interpreter/SDK startup can create caches; this is not an operating-system sandbox.
Installing requirements needs package downloads. Nothing attaches itself to this
ChatGPT conversation or another agent without a configured tool-host connection.

## Verification

```sh
cd tools/evidence-mcp
python -m unittest -v test_service
python test_stdio.py --out /path/to/new-evidence-directory
```

The local tests exercise the original helper code and invalid-input controls.
The integration script starts this actual server through the installed MCP SDK,
lists tools twice, then sends twelve synthetic requests in each of auto and legacy
modes. It records tool schemas, both text/structured responses, protocol error
flags, and the two server launches. A malformed call must not poison the following
valid call. The client blocks external socket connections during the test.

At initial publication, local tests passed and hosted integration is pending.
The introducing pull request records actual outcomes. An MCP client executes the
checks; no claim is made that a language model selected these tools or that any
external developer adopted them. AI-assisted by Zero (ChatGPT) for Youngseok Oh.

Sources: [MCP tools/list and tools/call](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
[SDK server entry at v2.2.0](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/mcpserver/server.py),
[approval checker](../approval-trace-check/README.md), and
[result fallback with original issue attribution](../mcp-result-text/README.md).

## 한국어

기존 두 도구를 다른 프로그램이 **목록 조회 → 사용법 확인 → 호출**할 수 있는
MCP 연결부입니다. 검사 결과가 잘못된 실행을 가리키는 경우와, 입력을 읽지 못해
판정하지 않은 경우를 구분해 반환합니다. 받은 응답의 오류 표시도 유지합니다.
기존 검사 코드를 다시 작성하지 않고 그대로 불러 사용합니다.

현재는 연결을 원하는 앱이 실행해 쓰는 표준입출력 서버입니다. 별도 웹사이트나
상시 에이전트가 아니며, 사용자 PC나 다른 앱에 자동 설치하지 않습니다.
