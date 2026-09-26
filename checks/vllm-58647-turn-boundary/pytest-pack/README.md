# Portable history-boundary review tests

Youngseok Oh × Zero | 26 September 2026

**Run the earlier nine input cases in ordinary pytest, and verify that the checker rejects five deliberately bad changes.** This is reusable review material for [the existing vLLM discussion](https://github.com/vllm-project/vllm/issues/58647), not a new model benchmark, converter repair or upstream-approved patch.

## Run

Keep `test_history_contract.py`, `fixtures.json` and `expected.json` together. Obtain `chat_template.jinja` from [the exact official Qwen3.8-27B revision](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/chat_template.jinja), retain its [license](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/LICENSE), and place the template beside the test file. The test refuses any other template SHA-256.

With pytest and Jinja2 available in your chosen environment:

```sh
python -m pytest -q -p no:cacheprovider test_history_contract.py
```

Tested environment: Python 3.13.5, pytest 9.0.2 and Jinja2 3.1.6. Only these two Python dependencies are needed. A fresh dependency installation may require a download; the tests block Python socket connections and DNS. No model weights, hosted server or API credential are used. The conversation runtime ZIP additionally includes the exact template, upstream license, byte manifest and an offline `VERIFY.py`.

## What was verified

The earlier [three-shape, three-setting probe](../README.md) is reused without changing its input content or expected output hashes. Nine pytest cases check the same rendered bytes, visible text once and in order, unchanged template-bound message roles, and the tool-call/result association.

Five further tests inject bad changes into **our own wrapper** and require their detection:

| Deliberately bad change | What must reject it |
|---|---|
| Delete the latest user text | Content-preservation check |
| Relabel the latest user instruction as a tool result | Input-role/structure check |
| Move the latest user instruction earlier | Visible order and structure checks |
| Change only the tool-result call ID | Call/result binding before rendering |
| Ignore `preserve_thinking=False` | Requested reasoning-retention check |

Four of these damaged cases still pass a weaker check that looks only for the OLD and CURRENT reasoning markers. The changed-call-ID case even produces **byte-identical rendered text**, because this template does not serialize that ID. This is not a new template bug; it shows why a text comparison cannot substitute for checking the association of a structured tool result.

**Actual result: 14/14 selected tests passed**, comprising nine known-baseline cases and five correct rejections. The runtime ZIP was extracted into a new directory; its byte manifest passed, and the same fourteen cases passed again with identical per-case observations. This is a same-environment packaging replay, not an independent external replication. [Result and scope record](SUMMARY.json).

## Boundaries

This is a direct, already-converted message-to-template check. A real Anthropic converter may intentionally transform roles or content; integration tests must explicitly define that permitted transformation. This pack does not decide how that converter should implement item 8, and running it alone does not validate the converter.

The five bad changes are synthetic detector controls, not five defects discovered in vLLM. There is no server, native tokenizer or model execution here. One template, textual synthetic content and one tool call are covered. No inference about multimodal histories, multiple calls, model accuracy, latency or production safety follows.

No third-party issue, PR, reminder or review request was posted for this packaging step. The existing contributor's diagnosis and implementation priority remain theirs. No recipient use, endorsement or revenue is claimed. New wrapper and tests were developed and executed by Zero following Youngseok Oh's direction. The plain Zero byline is used; the collaboration's authorship context remains disclosed in the repository. New code is offered under Apache-2.0; the unchanged template remains the Qwen authors' work.

## Provenance

Template SHA-256: `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.
Test file SHA-256: `9d6fd6f39d11ba2b82ddbf75fe60ad5b08bd8ef73017e2f3dde18265fff25f2e`.
The public JSON files use compact whitespace; their parsed fixtures and expectations equal the runtime bundle's values.
Runtime ZIP: `ZERO_HISTORY_REVIEW_RUNTIME_20260926.zip`, 15,355 bytes, SHA-256 `0d8262029a8d91536eb2b616f0acd7464db9e661c5204fa85b105c7a2a4562ff`. Its execution logs, JUnit records and packaging readback are also preserved in the separate conversation evidence archive. These conversation files are not GitHub release assets.

## 한국어

이미 보낸 검사를 개발자가 pytest로 바로 실행할 수 있게 정리했다. 기록 표식이 남아 있어도 사용자 문장이 삭제되거나 역할·순서가 바뀌었을 수 있다. 도구 결과의 식별자만 바꾸면 완성 문자열까지 같을 수 있으므로, 문자열 이전의 연결 정보도 확인한다. 기존 9개 조건과 고의 오처리 5개를 실행했고 모두 기대대로 동작했다. 실제 제품의 새 오류 다섯 개나 모델 답변 열네 개를 확인했다는 뜻은 아니다.
