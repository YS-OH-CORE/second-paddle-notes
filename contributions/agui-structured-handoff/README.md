# Can the host keep structured tool data without calling the tool again?

A bounded interoperability example motivated by [AG-UI #1593](https://github.com/ag-ui-protocol/ag-ui/issues/1593), reported by wjshamblin. The author offered to test a proposed direction; the project asks for discussion before significant feature work. This is a small diagnostic/example in our repository, not an unsolicited protocol patch or request to close that issue.

Current AG-UI [metadata documentation](https://github.com/ag-ui-protocol/ag-ui/blob/747933694b05676203da7d5bb8d8e50432e59b75/docs/concepts/metadata.mdx) already describes an application-defined metadata channel that is merged into TOOL_CALL_RESULT's tool message. This tests that existing route, rather than assuming the protocol needs a new field or that our text-fallback product is the right remedy for a UI payload.

## Two routes, the same received result

The probe obtains four synthetic results once each through the unchanged MCP2.2.0 in-process client/server path. One tool implementation is called with four case names. Those original results are retained and reused in two transport mappings:

1. Put structuredContent on the event as an undeclared top-level extra.
2. Put a selected copy in metadata under an application-agreed example key.

The actual Python EventEncoder sends the result over loopback HTTP/SSE to the published TypeScript HttpAgent. The probe observes both onToolCallResultEvent and the assembled tool message. UI-shaped JSON, an empty object, a structured error and absent structure are covered. The original text is identical on both routes. The metadata route must retain the chosen data and error flag in the final tool message, not just in the callback. The undeclared-extra route's behavior is recorded rather than presumed.

The mapping is deliberately small:

```python
from ag_ui.core import ToolCallResultEvent
from bridge import result_metadata

# received is the result already returned by the tool; do not re-invoke it.
event = ToolCallResultEvent(
    message_id="result-1", tool_call_id="call-1", content=existing_text,
    metadata=result_metadata(received),
)
```

A cooperating host reads `message.metadata["example.mcp.result.v1"]`. This key is an example application contract, not a new standard or built-in MCP Apps behavior. The protocol-reserved `ag-ui` namespace is left alone. The application must use the packet's `isError` flag when deciding how to display a result; AG-UI does not automatically reinterpret that application field.

## Actual result, 2026-09-13 Korea time

[Run34716914077](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34716914077) completed on executable commit9032ae9b58f5a1099c90d597e2aff8f063826653. Installed versions: Python ag-ui-protocol0.1.22, MCP2.2.0, Pydantic2.13.5; Node22.23.2 with @ag-ui/client and @ag-ui/core0.0.59. No SDK source was patched.

| Where structured output was attached | Subscriber callback | Assembled tool message |
|---|---|---|
| Undeclared top-level structuredContent | Present in all three data-bearing cases | Absent in all three |
| Explicit application metadata | Present in all three data-bearing cases | Present in all three |
| No structured output in the source | No invented structured result | No invented structured result |

This distinction matters: an undeclared extra is not lost everywhere in these versions. A raw-event subscriber already receives it. The tested metadata route also retains it on the tool message produced by the official client, including after JSON serialization of that message.

One fixture function was invoked once for each of four cases. The same received results supplied both routes, so eight HTTP streams did not require eight MCP executions. Original text remained unchanged; nested Korean whitespace, empty arrays/objects, false, zero and null survived; the error flag survived inside the explicitly selected packet. The private-metadata canary was absent from every SSE body and final message. Eight helper tests passed both locally and in the hosted environment.

Original artifact10305150815:9,599bytes, SHA256 `d34fa7542c7eb2dac9063f065dd222ac97c8fe9d4822bcb92cd3cf3f334ed9f7`. The archive was downloaded and its CRC, four original results, eight actual SSE bodies/hashes, subscriber events, final messages, per-case invocation counts and unit output were cross-checked. This readback is not another SDK experiment. Source-file hashes and complete installed dependency listings are retained in the artifact.

## Privacy and scope

Metadata can be logged or sent back with message history. It is **not a confidential channel**. The example intentionally excludes MCP `_meta` and other undeclared fields; blindly copying a complete server result into metadata would be inappropriate. Only the host-approved structured output and its error flag are selected. Choose the namespace and renderer mapping with the host. Do not promote any returned string to instructions or execute a UI tree as arbitrary code.

This does not configure an existing application, render a real iframe, run a provider/LLM, or demonstrate that every AG-UI integration now works. Original MCP calls are in-process; the AG-UI HTTP/SSE transport is a real loopback connection. Synthetic call counters are not a measurement of production retry reduction. The sample uses ordinary JSON-sized integers and does not claim arbitrary-precision number preservation in JavaScript. Source records stay separate from the projected message.

## Reproduce

In a disposable environment, install `ag-ui-protocol==0.1.22` and `mcp==2.2.0`, plus npm `@ag-ui/client@0.0.59` and `@ag-ui/core@0.0.59` on the Node module search path. Then:

```sh
python -m unittest -v test_bridge
python probe.py --out /path/to/new-evidence-directory
```

The workflow records actual installed package versions, imported paths/hashes, dependency listings, the original four results, eight SSE bodies, callbacks, assembled messages and tool counts. Local work ran standard-library helper tests and syntax checks; package lookup failed DNS, so the installed-SDK evidence comes from the hosted run.

Prepared by Youngseok Oh with Zero (ChatGPT). Newly authored files in this folder may be used under the MIT terms at ../../tools/evidence-mcp/LICENSE; source projects retain their own licenses and credit.
