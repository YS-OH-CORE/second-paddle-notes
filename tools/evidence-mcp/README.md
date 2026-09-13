# Two small checks an MCP client can discover and call

This stdio entry exposes the existing approval-trace checker and structured-result
fallback as **two read-only tools**. A compatible host can list their schemas and
invoke them instead of generating integration code. It starts only when launched;
there is no HTTP endpoint, scheduler, account, provider key, or model call.

**Use the corrected [0.1.0a2 installation](../../packages/evidence-mcp/README.md).**
The earlier 0.1.0a1 wrapper could serialize protocol metadata or other unselected
fields into ordinary model-facing output. This is a correction in our wrapper,
not an upstream MCP repair. Old source and artifacts are retained with warnings.

| Tool | Input | Output |
|---|---|---|
| `check_approval_trace` | Original trace JSON as a string | Request/execution findings, or an explicit unassessed error |
| `project_tool_result` | Selected model-view result JSON as a string | An independent view of allowed content/structure and errors; mixed envelopes are rejected |

The first tool reuses `../approval-trace-check/audit.js` v0.1.1. The second reuses
`../mcp-result-text/result_text.py`. Those two helper implementations are unchanged.
The wrapper adds a model-view input boundary before using the second helper.
Startup checks precise helper Git blob identities; after an intentional helper
update, review and test the bridge before changing those pins.

## Start from a repository checkout

Tested environment: Python 3.12 and Node.js 22.23.2 on Linux.
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

Both tools accept JSON **strings** and reject duplicate object members. Pass the
original approval trace, not a parse/reserialized copy that hides duplicates. For
result projection, select a model-visible view in the trusted caller first,
retaining its source separately and checking ambiguity before discarding fields.
Each string is limited to 1 MiB UTF-8. The trace checker runs a fixed Node shim over
stdin with a three-second limit, never a caller-supplied command, path or shell
expression. Result projection uses duplicate-aware parsing and SDK validation.

A detected approval mismatch is successful *analysis*: `isError=false` with
`status=violations_observed`. An unreadable or ambiguous trace is `isError=true`
and `status=not_assessed`, with no invented success counters. No execution in the
trace is separately reported as `no_execution_observed`. Diagnostics use fixed
codes and numeric positions rather than echoing invalid supplied values.

### Model-view projection only

`project_tool_result` accepts `content`, `structuredContent` and `isError` at the
result's top level. It rejects protocol-position `_meta` in the envelope, content
blocks and embedded resource; unselected fields; and a declared content audience
that does not include `assistant`. Diagnostic codes include
`HOST_METADATA_NOT_PROJECTABLE`, `NON_CONTENT_FIELDS` and `NON_MODEL_AUDIENCE`.
Rejected values are not quoted in the error. The caller's original is not silently
redacted or modified.

Keys spelled `_meta` inside already-selected `structuredContent` or quoted text
remain ordinary data. Allowed text/media blocks and an original `isError=true`
are preserved, with the latter true both inside the view and on the outer result.
Missing structured data stays absent. The view is not a newly signed source.

**Select data before supplying the argument.** Rejection at the output cannot
undo disclosure in a model prompt, tool argument or log. This is not a classifier
for secrets in ordinary text, nor a universal claim that every MCP `_meta` field
is confidential. The lower-level local-copy helper deliberately preserves source
fields for a trusted application; it is not a model-view sanitizer. Do not send a
whole host-only response to a model just to ask this tool to clean it.

Descriptions and data may contain instruction-like text; nothing here evaluates it
or turns it into a command. The consuming host remains responsible for treating
all returned content as tool data. This does not authenticate consent, authorize
action, prove a log complete, prevent prompt injection in a consuming model, or
establish that a missing search hit does not exist. Request IDs/scopes and selected
payloads are returned to the caller; the host's normal data handling still applies.

The tool bodies do not write caller files or initiate network requests. Normal
interpreter/SDK startup can create caches; this is not an operating-system sandbox.
Installing requirements needs package downloads. Nothing attaches itself to this
ChatGPT conversation or another agent without a configured tool-host connection.

## Verification

```sh
cd tools/evidence-mcp
python -m unittest -v test_service test_visibility
python test_stdio.py --out /path/to/new-evidence-directory
```

The tests exercise the original helpers, invalid-input controls and the added
model-view boundary. The original integration script starts the actual server
through the installed MCP SDK, lists tools twice and sends twelve synthetic
requests in each of auto and legacy modes. It records schemas, text/structured
responses, protocol flags and launch records. This original script is not the
new installed a1/a2 comparison; those results are linked separately below.

### Corrected boundary: 0.1.0a2

[PR #31](https://github.com/YS-OH-CORE/second-paddle-notes/pull/31) and
[run 34748252871](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34748252871)
compare installed a1 and a2 over actual MCP stdio with the same twelve synthetic
inputs. Six restricted-input cases expose a marker through a1; a2 returns the
fixed errors without it. Six allowed-data cases retain the same data and error
status, including a normal `_meta` application key and quoted text. The 21-unit-test
run includes the original sixteen tests without modifying their assertions.

The original comparison ZIP is 26,193 bytes with SHA-256
`d76bb8798a3f74bf330c0e44692a040586c47527f337f52b9afd6f795002e19d`.
Its source and recorded responses were recovered and checked after the
conversation was interrupted. This is synthetic test evidence, not a real user's
private-data incident or a language-model experiment. See the
[installation record](../../packages/evidence-mcp/README.md) for Windows/Linux
consumer checks, the exact wheel and the completed public release.

### Historical service checks before the boundary correction

[PR26](https://github.com/YS-OH-CORE/second-paddle-notes/pull/26) and
[run34708053757](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34708053757)
record the earlier service result: 16 unit tests passed, and two real stdio server
launches each advertised both tools and completed 12 synthetic calls (24 total).
The client started the exact server script from a separate working directory.
Text and structured results agreed, errors remained errors, and a valid empty-result
projection succeeded after invalid calls. Both existing helper files were unchanged.
Those cases did not establish the model-view boundary later corrected in a2.

The returned artifact was downloaded and inspected: 10,870 bytes, SHA-256
`fd3584dfdfd713a2fd76343a6e469eddf442f9099586835cd0cbf471eb6dd55f`.
Per-mode files match the combined summary; all 24 responses, error flags, tool
schemas and the two launch records were checked. Client network attempts were empty.
This evidence inspection is not an additional independent execution.

The initial run34707943257 also passed. Before first publication, helper loading
was placed under a lock; the complete sequence ran again on executable
commit2bfc9a7f9b658d2134da0b7e7d8303cd90bd635f. These are the same selected cases,
not a doubled sample or a general concurrency certification. The complete former
usage document remains in its [pre-correction snapshot](https://github.com/YS-OH-CORE/second-paddle-notes/blob/e4fc1864d809c89f582a67298bf45bfc3c1eef6c/tools/evidence-mcp/README.md).

A programmed MCP client executes these checks; no claim is made that a language
model selected the tools, that a particular host app was configured, or that an
external developer adopted them. New files in this folder are MIT-licensed; this
does not relicense sibling tools or the SDK. AI-assisted by Zero (ChatGPT) for
Youngseok Oh.

Sources: [MCP tools/list and tools/call](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
[SDK server entry at v2.2.0](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/mcpserver/server.py),
[approval checker](../approval-trace-check/README.md), and
[result fallback with original issue attribution](../mcp-result-text/README.md).

## 한국어

기존 두 도구를 다른 프로그램이 **목록 조회 → 사용법 확인 → 호출**할 수 있는
MCP 연결부입니다. 검사로 문제를 발견한 경우와 입력을 읽지 못한 경우를 구분하며,
응답의 오류 표시도 유지합니다.

현재 수정본은 AI가 읽는 결과에 내부용 부가정보까지 복사하지 않도록 입력 범위를
명확하게 제한합니다. 원문은 별도로 보존하고, AI에게 보여 줄 자료를 먼저 골라
전달해야 합니다. 이미 AI에게 넣은 정보를 출력 오류가 되돌리지는 못합니다.
일반 자료 안의 정상적인 항목을 이름만 보고 지우는 방식은 사용하지 않습니다.

원하는 앱이 실행해 쓰는 표준입출력 서버이며, 사용자 PC나 다른 앱에 자동 설치하지
않습니다. 이전 설치가 자동으로 수정되는 것도 아닙니다.
