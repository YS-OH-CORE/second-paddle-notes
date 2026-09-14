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

## Four comparisons to execute

| Case | Intended check, not a result until the probe actually runs |
| --- | --- |
| Both stores preserved | One initial request in A; one continuation in B; original draft-1 completes. |
| Server store lost | Client checkpoint is intact, but the new server has an empty store; UNKNOWN_ROUND and no label. |
| Initial request replayed | Deliberately naive application control asks again and uses the old answer with the stable key; draft-2 completes. This is not an assertion about the upstream adapter. |
| Original question declined | Reopen both stores, submit a programmed decline; no label. |

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

Use a new output directory and leave Python assertions enabled. Twelve fixture
store tests use only the standard library. They are not twelve MCP experiments.
The hosted workflow runs the installed SDK probe and retains only synthetic
JSON and logs for 14 days, excluding the checkpoint/server databases. The top-six
package versions match the previous experiment; full resolved dependencies are
recorded rather than claimed to be a fully locked environment.

At preparation, local store tests and syntax checks passed. Local DNS could not
reach the package/source host, so no local installed-SDK result is claimed. Read
the workflow result and the original retained records before treating the four
intended outcomes above as observed results.

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
