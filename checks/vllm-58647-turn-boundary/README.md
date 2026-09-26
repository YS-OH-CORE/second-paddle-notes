# Qwen3.8 controls for the existing vLLM turn-boundary discussion

Youngseok Oh x Zero, AI collaboration partners | 26 September 2026

**A current-reasoning marker surviving the Qwen3.8 default is not sufficient evidence that a converter preserved the intended user-turn boundary.** The pinned template preserves all supplied reasoning by default. Its last-query boundary becomes observable when `preserve_thinking=False` is tested separately.

## Why this is here

[vLLM RFC #58647, item 8](https://github.com/vllm-project/vllm/issues/58647) already reports that user text following tool results can become a separate trailing user message, causing last-user-sensitive templates to drop current tool-loop reasoning. [An existing participant has offered to work on it](https://github.com/vllm-project/vllm/issues/58647#issuecomment-5826239006). The diagnosis and implementation priority remain theirs. This note supplies a small template-level review aid, not a new issue or competing runtime patch.

We reused the official Qwen3.8-27B template retained in our [earlier input-boundary check](https://github.com/YS-OH-CORE/second-paddle-notes/blob/b60682587597235706714ccfacd37cb0a883b76d/experiments/qwen38-native-continuation/RESULTS.md). Three synthetic, already-converted message shapes were rendered under default/false/true history preservation. New thinking was disabled in all cases.

## Actual local observations

The fixture contains an OLD trace before the current user's task, and a CURRENT trace in the assistant tool call after that task. Each cell lists which trace is present in the rendered input.

| Message shape | Default | Preserve=False | Preserve=True |
|---|---|---|---|
| Ends in a tool result | OLD + CURRENT | CURRENT only | OLD + CURRENT |
| Same history plus a trailing user reminder | OLD + CURRENT | Neither | OLD + CURRENT |
| Same history plus a genuine new user instruction | OLD + CURRENT | Neither | OLD + CURRENT |

Nine local Jinja renderings completed. Default and explicit True produced identical strings for each shape. All visible message contents were retained exactly once, and the input dictionaries were unchanged. These observations concern this one template and these synthetic shapes, not nine generated model responses.

A default-only test would therefore see CURRENT in both the tool-only and trailing-user cases, without demonstrating that the turn boundary was preserved. Enabling preservation globally also retains OLD; that is the intended preserve-all behavior, not a selective boundary repair. Conversely, removing the trailing text merely to restore CURRENT would lose supplied content and is not an acceptable general repair.

## Suggested acceptance checks for the existing implementation work

Test the real converter-to-renderer path with separate OLD and CURRENT markers and preservation explicitly off as well as on. Include a genuine next-user-turn control, where last-user-only preservation should exclude preceding reasoning. Check the actual trailing text, tool results, call identifiers and ordering alongside reasoning retention. Define whether a block is a same-turn annotation or a genuinely new instruction rather than moving text between user/tool roles simply to obtain a retained marker.

This probe starts after conversion and cannot decide how the converter should encode that distinction. It does not measure how a model interprets or follows the supplied text.

## Reproduce this exact, limited check

Get [the official template at the frozen revision](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/chat_template.jinja), and run the adjacent [probe.py](probe.py) in a Python environment with Jinja2 3.1.6:

```bash
python probe.py --template /path/to/chat_template.jinja --out /path/to/new_output
```

The output directory must be new. The script checks the template SHA-256 before rendering, saves all nine complete rendered strings and writes OBSERVATIONS.json with hashes. No network access is performed by this script. The local dependency was Jinja2 3.1.6.

Template revision: `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
Template SHA-256: `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.
Source archive reused: `ZERO_QWEN38_HISTORY_BRIDGE_RAW_20260926.zip`, SHA-256 `b5f27c7409cbbde570e367ba306afb5a2e358441a275e09b118f7717fdfb92ff` (archive and template hashes rechecked before reuse).

The live converter source was separately read at [vLLM ddd6fbca](https://github.com/vllm-project/vllm/blob/ddd6fbca148a867aad1fcab7ec72f582b9977db4/vllm/entrypoints/anthropic/serving.py). It was not imported or executed. An attempted local source download failed DNS resolution; no runtime claim is based on that attempt.

## Scope

**Executed:** local Jinja rendering of retained official template bytes, synthetic fixture assertions, and output readback.

**Not executed:** the vLLM converter or server, native tokenization in this new check, model inference, a production client, the upstream test suite, or another developer's proposed fix. No latency, model-accuracy, cache-hit or actual-user benefit is measured. This is a diagnostic control designed after reading the RFC, not a preregistered scientific study or independent end-to-end replication.

Our prior reasoning/reasoning_content adapter is a different boundary and is not presented as a fix for item 8. No upstream code or production setting was changed, and no upstream PR was opened. AI participation is explicit; no human line-by-line review or maintainer endorsement is claimed.
