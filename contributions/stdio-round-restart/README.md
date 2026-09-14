# Reconnect actual MCP stdio after both processes restart

Prepared by Youngseok Oh with Zero (ChatGPT). This companion experiment extends
[the saved-round graph](../preserved-mcp-rounds/README.md) and the
[clean client-process test](../preserved-mcp-rounds/PROCESS_RESTART.md).
The earlier question-replay finding remains credited there to Totoro-qaq.

## What changes at this boundary

The earlier process probe used a deterministic session double. Here the official
MCP 2.1.1 `Client(StdioServerParameters(...))` launches an actual low-level MCP
server subprocess. The client uses real `session.call_tool` serialization and
stdio transport. It saves the original form using the unchanged LangGraph graph
and SQLite saver, closes the client context and exits. A new Python client starts
a new server process, negotiates the protocol and reopens the checkpoint.

The fixture server also stores its issued rounds in SQLite. This is explicit
application state, not persistence supplied magically by MCP. No FastMCP state
codec, production server configuration or third-party SDK is modified. The
client echoes the opaque token without interpreting it.

## Observed on 2026-09-14

[Run 34791675942](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34791675942)
completed at tested head `f795eeaad68895d4aacd1955ac137335e7898eac`.
Nineteen standard-library unit checks passed in that run: twelve fixture-store
checks and seven strict result-comparison checks. The four actual stdio cases
negotiated MCP `2026-07-28` and produced these records:

| Case | Returned observation | Tool calls |
| --- | --- | ---: |
| Both stores preserved | Original draft-1 completed after one original-state continuation. | 2 |
| Server store lost | Intact client checkpoint; empty server store; UNKNOWN_ROUND, isError=true, no label. | 2 |
| Initial request replayed | Programmed naive control completed draft-2 using the earlier draft-1 answer and the stable key. | 3 |
| Original question declined | Original-state continuation returned skipped:decline; no label. | 2 |

There were nine actual tools/call invocations across eight fresh client and eight
server processes, not nine deployments or independent human decisions. The replay
control is deliberately wrong application code, not a new test of MCPAdapter.

## Original evidence and one corrected comparison

The returned [artifact 10327972446](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34791675942/artifacts/10327972446)
was downloaded and inspected: 24,111 bytes, SHA-256
`cd9aec329504cd5168ba9793382e137877263d64cf17e171fe786d6b014a2151`.
All 32 members passed CRC. Separate client/server JSON and logs matched the four
summary rows and process-order files. The executing probe's recorded SHA-256
matched the locally prepared 17,491-byte source:
`4f0d7afc811c572cd1e24d52287fe15eeaf85c34271312129f34aa4db58be585`.
An offline inspector rechecked the returned files without running another SDK
experiment. Original archives and the inspector are also delivered in the
conversation bundle; Actions retention alone is not permanent storage.

[First run 34791471652](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34791471652)
had already returned previewed:draft-1 across real restarted processes, but the
end-of-case comparison failed before the other three cases. The handler logged
its result before the SDK added `_meta.io.modelcontextprotocol/serverInfo`;
the client naturally received that added stamp. Comparing those whole objects
as identical whole result objects was an error in this probe, not a persistence failure.

The correction explicitly requires the exact expected fixture name/version and
no other metadata, then compares every remaining result field. Both original
objects remain in the records. It does not broadly drop `_meta`, treat the stamp
as authenticated identity, patch an SDK, or change the fixture outcomes. Seven
comparison tests reject changed/missing identity, extra metadata/body fields,
changed state, or unexpected handler metadata. It also retains process ordering
before the final checker and verifies server A's exit before client B starts.
The original failed 6,887-byte ZIP remains distinct, SHA-256
`03afcabf31c2cf9051f13778dd0e712014a5a3309971623c754d02c327328107`.

Each case uses distinct A/B client and server processes. The parent waits for A
to exit before B starts. Only synthetic strings are written to disposable local
databases. Programmed accept/decline values are fixtures, not a person's consent.

The probe compares exact SDK client calls with the server's received parameters
and returned results, and checks saved/reopened frame identity, question text,
opaque state, answer, error flag, labels, process ordering, versions and source
hashes. `round_graph.py` must keep its inspected Git blob identity. IPv4/IPv6
connection attempts during each child exercise are blocked by a Python audit
hook; dependency downloads happen before the exercise. This is not an OS-level
network isolation certificate.

## Reproduce

From a repository checkout in a disposable environment:

```sh
python -m pip install -r contributions/preserved-mcp-rounds/requirements.txt
(cd contributions/stdio-round-restart && python -m unittest -v test_store)
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false \
  python contributions/stdio-round-restart/stdio_restart_probe.py --root /path/to/new-output
```

Use a new output directory and leave Python assertions enabled. Nineteen fixture-
store and result-comparison tests use only the standard library. They are not
nineteen MCP experiments.
The hosted workflow runs the installed SDK probe and retains only synthetic
JSON and logs for 14 days, excluding the checkpoint/server databases. The top-six
package versions match the previous experiment; full resolved dependencies are
recorded rather than claimed to be a fully locked environment.

Local store/comparison tests and syntax checks passed. Local DNS could not
reach the package/source host, so installed-SDK execution occurred in the hosted
workflow. The later local artifact inspection is a read-back of that execution,
not another installed-SDK trial.

## Limits

This is an executable diagnostic and application recipe, not an upstream fix,
new protocol, general-purpose recovery service or ready-to-deploy secure server.
No HTTP reconnect, machine reboot, forced crash, simultaneous replies, expiry,
authentication, genuine human approval or exactly-once remote effects are tested.
The fixture's SQLite transaction covers its own harmless label only. It cannot
make an arbitrary external side effect atomic with a client checkpoint.

Sources: [MCP multi-round rules](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr),
[SDK manual round handling](https://github.com/modelcontextprotocol/python-sdk/blob/v2.1.1/docs_src/mrtr/tutorial002.py),
[low-level server example](https://github.com/modelcontextprotocol/python-sdk/blob/v2.1.1/docs_src/mrtr/tutorial001.py),
and [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts).
New files use the repository's [existing MIT terms](../../tools/evidence-mcp/LICENSE).
