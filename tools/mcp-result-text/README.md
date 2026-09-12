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

### Observed on 2026-09-13 (Korea time)

[Run 34706775987](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34706775987)
completed with all 16 unit tests passing and 12 actual tool calls: six cases in
each of two fresh stdio server processes on the unmodified published MCP 2.2.0
SDK. Empty-list results gained the exact text `{"result":[]}`. Two-hit results,
empty text and empty-object text stayed unchanged; absent structured output
stayed absent; the explicit-error response kept `isError: true`.

Each test server logged one invocation per tool. Every original response was
unchanged, every generated view passed the SDK result model, and the receiving
client's recorded external connection attempts were empty. The experiment
compares consumer views, not the number of retries chosen by a language model.
Image/resource preservation, false/zero/null, deep-copy isolation and size limits
are unit checks rather than additional live-server cases.

The original artifact is 4,515 bytes, SHA-256
`4f0dcbc37e4d9b033c9a7fbfd6311b23334da3341d919e8ce16c9c2a2af7da7f`.
The downloaded per-mode observations, actual server invocation logs, source
identities and unit output were cross-checked; each recorded view was recomputed
with the published module. This inspection is not a second SDK experiment.

The first hosted run, 34706694768, passed the unit tests but failed before tool
execution because our test server could not resolve a postponed local class
annotation. The next commit corrected that test fixture without changing the
adapter or relaxing any assertion. That failed run remains in
[PR #25](https://github.com/YS-OH-CORE/second-paddle-notes/pull/25).
Local package resolution did not provide MCP 2.2.0; SDK integration evidence is
from the hosted run, while the standard-library unit tests also ran locally.

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

## 한국어

검색 도구가 빈 목록을 돌려줬는데 본문만 읽는 쪽에는 아무 글자도 안 보이는
상황을 위한 작은 연결부입니다. 별도 구조화 결과가 실제로 들어 있을 때만
그 전체 내용을 JSON 문자열로 보여 줍니다. 예를 들어 `{"result":[]}`를
그대로 넘기며, 정보 자체가 없을 때 "검색 결과 없음"이라고 지어내지 않습니다.

원래 응답은 보존하고 다음 단계가 사용할 사본만 만듭니다. 기존 글·이미지·자료
블록, 오류 표시와 부가 정보도 유지합니다. SDK를 고치거나 서버를 재설치하지
않고, 응답을 넘기는 지점에서 `result_text.py`의 함수를 가져다 쓸 수 있습니다.
검사 자료는 합성 데이터이며 실제 언어 모델의 재시도 감소는 측정하지 않았습니다.
