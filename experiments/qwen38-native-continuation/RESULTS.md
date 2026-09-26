# Qwen3.8: a blocked generation route and a verified response-to-template boundary

Youngseok Oh x Zero, AI collaboration partners | 26 September 2026

**Actual model generation remains unmeasured. A separate, completed input-construction test shows that directly handing a response-shaped `reasoning` field to the pinned official Qwen3.8 HF template omits that text, including when historical reasoning preservation is enabled. An explicit adapter restores the expected template input.** This is a client-interface compatibility result, not an observed failure of model reasoning or the vLLM server.

## 1. Native-history generation pilot: stopped before any completion

The planned experiment would generate two initial model answers with native reasoning, reuse each unchanged, and test PUBLIC-to-PRIVATE and PRIVATE-to-PUBLIC user corrections under four thinking/preservation combinations. Code and the eight-continuation schedule were committed before contacting the endpoint. A strict parser distinguishes final JSON from reasoning-only text, truncation and malformed responses; its five synthetic checks passed.

The community endpoint advertised on [its operator's page](https://victor-qwen3-8-27b-free-endpoint.static.hf.space/index.html) did not serve the initial model-discovery request. Actual `GET /v1/models` returned HTTP 400:

```json
{"error":"Bad Request: The endpoint is paused, ask a maintainer to restart it","code":"BAD_REQUEST"}
```

The operator's page also now displays a retirement notice. The original search-visible free-service instructions did not establish continued availability. We stopped after that one request, without retrying generation or requesting that the deployment be restarted.

[Run 36207317632](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36207317632): one HTTP request, **zero completion requests, zero generated seeds, zero continuation observations**. This is unavailable infrastructure, not an incorrect answer from Qwen. The native-history procedure in [probe.py](probe.py) and [PROTOCOL.md](PROTOCOL.md) is prepared but not empirically completed. No paid fallback, account credential or private conversation was used.

## 2. Why inspect the reasoning-field boundary?

The current [vLLM reasoning-output documentation](https://docs.vllm.ai/en/latest/features/reasoning_outputs/) calls the response field `reasoning`, replacing the older `reasoning_content` name, and warns clients to update their reading logic. The pinned official Qwen3.8-27B Hugging Face chat template reads `message.reasoning_content`.

Those are different interface contracts. A custom application that stores a modern response-shaped dictionary and later passes it directly to `AutoTokenizer.apply_chat_template` must translate the field name at that boundary. This test does not exercise vLLM's internal request normalization or establish that its server loses reasoning. A server or framework may already perform the translation.

We used handwritten synthetic markers, not actual model-generated reasoning. One fixture places old assistant reasoning before the user's explicit withdrawal. A second adds current-turn reasoning with a synthetic read-only tool call and result. No tool executes.

## 3. Actual official-tokenizer comparison

Checkpoint tokenizer revision: `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
Template SHA-256: `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`, matching the previous official-template preflight.

For both fixtures, cross `preserve_thinking=False/True` with three representations: the direct modern field, the template's expected legacy field, and the modern field after our adapter. `enable_thinking=False` is fixed. This gives **12 rendered inputs**, not 12 generated answers.

| Input passed directly to the HF template | Old reasoning, preservation on | Current tool-turn reasoning | Latest user withdrawal |
|---|---|---|---|
| `reasoning` without conversion | Omitted | Omitted | Retained |
| `reasoning_content` | Retained | Retained | Retained |
| `reasoning` converted by the adapter | Retained | Retained | Retained |

With preservation off, the expected old reasoning is omitted, while the current tool-turn reasoning remains for the legacy/adapted inputs. This reproduces the documented scope of the template control rather than overriding it.

The legacy and adapted versions produced exactly the same rendered text **and token IDs in all four fixture/setting combinations**. For the old-history-only fixture with preservation on, the direct modern input contained 66 tokens, versus 79 after conversion. For the tool-turn fixture with preservation on, the corresponding counts were 102 and 129. These counts describe these particular marker strings, not general savings or performance.

Every input retained exactly one copy of the latest user withdrawal, all visible content, and the original message order. Each native tokenizer result matched separately encoding the rendered string without additional special tokens. Network calls were disabled during rendering; no attempts were recorded.

[Completed run 36207942892](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36207942892) used Transformers 5.17.0, tokenizers 0.23.2, huggingface-hub 1.33.0 and Jinja2 3.1.6. Only tokenizer/config/template/license assets were downloaded. No PyTorch model or weights were loaded.

## 4. Reusable adapter and tests

[history_bridge.py](history_bridge.py) is a small adapter only for the HF-template boundary. It deep-copies messages, preserves visible content and tool calls, converts textual reasoning aliases, rejects contradictory nonempty aliases, and refuses to flatten structured reasoning objects without a provider-specific adapter. Non-assistant messages are unchanged.

It must not be applied indiscriminately to every provider's API request. Its destination contract is specifically the pinned HF template above.

[bridge_probe.py](bridge_probe.py) contains nine adapter unit tests plus the native-tokenizer comparison. All nine tests passed in Actions and in a local replay. A conflicting pair of aliases is an expected error, not a silently chosen history. These are test-code results, not model-accuracy measurements.

From this directory, run the adapter tests without loading any model:

```bash
python -m unittest bridge_probe.AdapterTests -v
```

For the complete tokenizer comparison, install the recorded tokenizer dependencies and use a new directory:

```bash
python bridge_probe.py --out fresh_bridge_results
```

For a client calling the pinned HF template, adapt only the template-bound messages:

```python
from history_bridge import to_hf_template_message

hf_messages = [to_hf_template_message(m) for m in stored_messages]
encoded = tokenizer.apply_chat_template(
    hf_messages,
    tokenize=True,
    return_dict=True,
    add_generation_prompt=True,
    enable_thinking=False,
    preserve_thinking=True,
)
input_ids = encoded["input_ids"]
```

## 5. Evidence, provenance and audit

Adapter/probe commit before the tokenizer run: `539aa8d163b5f86db1b67f6f256754d6ec2a7388`. Workflow commit: `22e23c9a01c4373dc0510d2d92c20ab97ea1553f`.

Adapter SHA-256: `da57c8247c568827839c84b1f428f443a501c4cbde057a7f38a8e510a3db5e37`.
Probe SHA-256: `b11af51cc3c48de42d27e58ef1cdc3873c8f8e0da3561c489cf2a49576114d0f`.

[Successful input-test artifact 10894896911](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36207942892/artifacts/10894896911): 6,983,048 bytes; SHA-256 `b5f27c7409cbbde570e367ba306afb5a2e358441a275e09b118f7717fdfb92ff`.

[Blocked-route artifact 10894221341](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36207317632/artifacts/10894221341): 10,090 bytes; SHA-256 `63ccea3d33c337145f650d665b9b929bddfceda5939c9c34e8bbfd92f3c5c535`.

The successful artifact retains every input, rendered string and native token list, the seven official assets, scripts, tests, logs and environment. The failed-route artifact preserves the HTTP error and zero-completion status. Both are also included in the conversation evidence bundle. Actions retention is 30 days, not permanent storage.

[READBACK_AUDIT.json](READBACK_AUDIT.json) records checksum and source checks, exact schedule completeness, summary recomputation, all seven asset hashes, and twelve separate local Jinja text re-renders matching byte-for-byte. The local audit did not recompute native tokenizer IDs; that test ran in Actions. Missing-rendering and altered-text mutations were rejected. This is an internal readback and local replay, not independent external replication.

## Status and next decision

The free community route is retired/paused. Actual Qwen3.8 generated-answer behavior under native reasoning preservation is still unmeasured. The completed contribution is an executable input-boundary check and adapter that prevents a false comparison in which a supposedly preserved trace never reaches the template.

No third-party issue, PR or comment was posted. Results and reusable code are published in our own repository. No provider endorsement or adoption is claimed. Youngseok Oh supplied project direction; Zero designed, executed and audited the work as an AI collaboration partner. Official model assets and upstream interfaces remain their authors' work.
