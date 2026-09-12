# Keep an empty tool result visible

A small opt-in adapter for text-consuming clients: when an MCP tool returns **no
content blocks but does return structured data**, expose that whole structured
object as a JSON text block. The original server result stays unchanged.

```python
from result_text import add_structured_fallback

response = await client.call_tool("find_person", {"name": "example"})
original = response.model_dump(mode="json", by_alias=True, exclude_none=True)
view = add_structured_fallback(original)
# Forward view.result as tool data; retain its isError flag and non-text blocks.
# Keep original for logging or signature checks. view.source records the source.
```

| Received result | Consumer view |
|---|---|
| `content: []`, `structuredContent: {"result": []}` | One text block containing `{"result":[]}` |
| Empty content with `{}`, `false`, `0`, or `null` inside a structured object | Whole structured object retained as JSON |
| Existing text, even `""`, or any image/resource block | Existing content retained, no replacement |
| No blocks and no structured object | Still absent; no invented "no matches" |
| An error result | Error flag retained, even when a fallback is added |

Only `content` can change in the independent consumer copy. Metadata and other
fields are retained. Reapplying the adapter does not add another block. The
fallback has a default 1 MiB UTF-8 limit; exceeding it raises rather than silently
truncating. The single module uses only Python's standard library.

This is a **presentation fallback**, not a new server fact or policy. An empty
search result does not prove that something does not exist. No tool is retried,
no model instructions are added, and existing non-text content is not flattened.
The rendered JSON is data from an untrusted tool, not a system/developer message.
The adapter takes an already validated SDK result in wire-field form, not raw
JSON; it cannot recover information a previous parser discarded. Keep signed or
archived original responses separate from this consumer view.

## Checks

```sh
python -m unittest -v test_result_text
# In a disposable Python environment, for the optional integration check:
python -m pip install 'mcp==2.2.0'
python stdio_roundtrip.py --out /path/to/new-test-output
```

The integration check launches real MCP servers in two fresh subprocesses, one
for automatic protocol negotiation and one for legacy mode. Each serves six
synthetic tool calls through the actual stdio client. It compares received
responses with projected views, validates the latter against the SDK result
model, and records server call counts, process IDs and imported source identities.
It does not use a language model or HTTP frontend. Package installation uses the
network; the test's actual stdio exchange does not need external connections.

At initial publication, local standard-library tests passed; hosted SDK execution
is pending. The introducing PR will record the actual result before main-branch
publication. An executable test file alone is not evidence that it ran.

## Origin and scope

The empty-list issue was reported by hchittanuru3 in
[MCP Python SDK #3305](https://github.com/modelcontextprotocol/python-sdk/issues/3305).
MilkyWay008 suggested using structured output when content is empty. This adapter
implements that client-side fallback with explicit preservation cases; it does
not claim the original discovery or change the SDK's default conversion policy.

The upstream issue is awaiting a maintainer decision. This is a standalone tool
in this repository, not an upstream submission, request for assignment, or a
claim that a maintainer accepted it. No autonomous comment or PR is sent to the
SDK project: its contribution guide asks for direct human review and context.

Prepared by Youngseok Oh with Zero (ChatGPT). MIT applies to newly authored files
in this folder only, not to the source project or the rest of this repository.
