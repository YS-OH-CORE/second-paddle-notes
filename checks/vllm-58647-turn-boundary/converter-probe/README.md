# From native messages to the reasoning-retention boundary

Youngseok Oh × Zero | 26 September 2026

**The selected current vLLM message-conversion path retains both supplied reasoning markers. After an explicit local format projection, the pinned Qwen template excludes the current marker when trailing user text is present and `preserve_thinking=False`.** This adds source-method execution to the earlier template-only controls. It does not run the complete vLLM server or discover a new model defect.

This is supplemental work for [RFC 58647 item 8](https://github.com/vllm-project/vllm/issues/58647). That RFC already reports the converter/template interaction. Its author and existing implementation volunteers retain that credit. We supply a narrower, executable stage trace, not a competing patch.

## What was actually executed

The original `serving.py` and `protocol.py` were fetched at vLLM commit `ddd6fbca148a867aad1fcab7ec72f582b9977db4`, the observed main snapshot. Their Git blob identities were verified. The probe executes the unchanged ASTs of the upstream `AnthropicContentBlock` and `AnthropicMessage` Pydantic classes and eight conversion helpers, starting at `_convert_messages`.

The heavy server imports and class inheritance are not loaded. No helper body or branch is rewritten, no converted answer is mocked, and no replacement message-schema class is used. The extracted dependency closure and per-class/method AST hashes are recorded. The fixture validates through those actual extracted Pydantic classes; a deliberately invalid role is rejected. This is isolated source-method execution, **not a full installed-vLLM integration test**.

After conversion, our explicitly labeled local bridge maps `reasoning` to `reasoning_content`, decodes tool-argument JSON and fills absent content with an empty string. The bridge is not claimed to be the current `chat_utils` or renderer implementation. The resulting input is rendered with the already-retained official Qwen3.8-27B template.

## Fixed cases and observed stages

Two follow-up texts, one English and one Korean, request that a fictional report remain private. Cross one/two tool calls with four message structures:

1. Tool results only.
2. Tool results and follow-up text inside the same native user message.
3. Tool results followed by an adjacent native user message with the same text.
4. Tool results, an actual assistant completion, then a new user message.

That is **16 converter executions**, each followed by preservation-off/on rendering: **32 template renderings**. These are structured synthetic cases, not 16 independent conversations with a model or 32 generated answers.

| Checkpoint in this scoped path | Observed result |
|---|---|
| Native-message validation | All 16 fixtures validated; invalid-role control rejected |
| Immediately after conversion | OLD and CURRENT reasoning fields remained in all 16 |
| Tool-call/result association | The declared IDs and order matched in all 16 |
| Render with preservation enabled | OLD and CURRENT were retained in all 16 |
| Render with preservation disabled, tool-results-only shape | CURRENT remained; OLD was excluded in all 4 |
| Render with preservation disabled, any of the three follow-up shapes | Both markers were excluded in all 12 |
| Follow-up text in rendered input | Present exactly once in every applicable case, including Korean |

The user text was not deleted. The stage trace separates retention of a reasoning field in an intermediate dictionary from its inclusion in the model-bound string. A positive marker check on one side of this boundary cannot certify the other side.

## An important non-bug and a stronger control

The same-message and adjacent-user-message fixtures produced **identical converted dictionaries in all four matched groups**. This alone is not an API defect: the [Anthropic Messages API explicitly allows consecutive user or assistant messages to be combined into one turn](https://platform.claude.com/docs/en/api/python/messages/create).

Consequently, two adjacent user records should not automatically be labeled two semantically distinct conversational turns. That is a refinement of the earlier already-converted fixture labels, not a claim that normal API consolidation is broken. A real assistant completion between the tool result and the next user message remained distinguishable in all four controls.

For a proposed converter fix, define the intended turn and authority semantics first. Then check the input structure and template output under both preservation settings. Do not remove a user's correction or silently relabel it as tool output merely to keep a reasoning marker. This probe identifies the boundary to inspect; it does not establish that retaining prior reasoning is always the right policy.

## Reproduction

Place the following immutable files in one assets directory, keeping their upstream licenses:

- [vLLM serving.py](https://github.com/vllm-project/vllm/blob/ddd6fbca148a867aad1fcab7ec72f582b9977db4/vllm/entrypoints/anthropic/serving.py), Git blob `08f208f8249e2fb9d31d89bb7d7a2a0e7530514f`.
- [vLLM protocol.py](https://github.com/vllm-project/vllm/blob/ddd6fbca148a867aad1fcab7ec72f582b9977db4/vllm/entrypoints/anthropic/protocol.py), Git blob `48202831fe397a1ccea5a89c264a9da6e7ce032b`.
- [Qwen chat_template.jinja](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/chat_template.jinja), SHA-256 `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.

With Python 3.13.5, Pydantic 2.13.4 and Jinja2 3.1.6, use the adjacent [probe.py](probe.py):

```sh
python probe.py run --assets ./assets --out ./fresh_results
python probe.py audit --out ./fresh_results
```

Use a new output directory. Measurement runs without network access; source acquisition is separate. The output retains native messages, converted dictionaries, the explicit projected messages, complete rendered strings, hashes, source provenance and the summary. The auditor regenerates the fixtures, recomputes the projection and summary, and rejects deliberately altered rendered text. It does not claim independent scientific replication.

## Execution provenance and limits

[Actions run 36214945772](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36214945772) succeeded at **source acquisition only**. It did not run these conversions. Its artifact 10896614176 is 16,697 bytes, SHA-256 `9043fdcd689bce1c223058bb21605e422da7310b659eab4674ce2352d1958cb8`. Direct source download in the working container failed DNS resolution, so the original bytes were acquired through this bounded job, not guessed or reconstructed from excerpts.

The actual 16 conversions and 32 renderings, followed by the audit, succeeded locally in the working container. Script SHA-256: `fb88125bec59b3e422d85c5884729dcfbc1068275bfda41dd8c677d3b1e4c11f`. The conversation evidence bundle retains execution logs, all observations, original source files, the source acquisition ZIP and licenses. No source method or runtime fix was changed to obtain the result.

No model inference, full `to_chat_completion_request` call, native tokenizer, live HTTP server, production client, GPU, private user conversation or paid completion endpoint was used. Top-level request handling, real renderer normalization, multimodal data, provider behavior, output accuracy, and production security remain outside this result. There is no new external adoption or maintainer approval to report.

The next validation with a cooperating developer should execute the installed converter and renderer against that developer's candidate. Further synthetic packaging alone will not substitute for that. New test scaffolding and analysis: Zero, following Youngseok Oh's project direction. Original conversion code belongs to the vLLM contributors and the template to its authors.
