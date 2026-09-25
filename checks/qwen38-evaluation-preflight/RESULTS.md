# Moving the evaluation target to current Qwen models

Youngseok Oh x Zero, AI collaboration partners | 26 September 2026, Korea

**Current-model interface check completed: the official Qwen3.8-27B and Qwen3.8-Flash-Next templates independently control new thinking and retention of supplied historical reasoning. Disabling new thinking does not remove old reasoning from the input.** This is a tokenizer/template result, not a new model-performance result. There were zero model forward passes, generated answers, weight downloads or hosted completion calls.

## Target selection

The user's current direction is to prioritize recent models and work useful to developers now. Qwen2.5-0.5B remains an inexpensive legacy control, not the headline target. The official [Qwen3.8 repository](https://github.com/QwenLM/Qwen3.8) identifies the current family and dates the 27B release to 14 August 2026. [Qwen3.8-Flash-Next's model card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) describes default thinking and preserved thinking. These provider features motivate the next evaluation; provider benchmark claims are not our measurements.

The actual Hub revisions used here are:

| Target | Immutable revision |
|---|---|
| Qwen/Qwen3.8-27B | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| Qwen/Qwen3.8-Flash-Next | `de4b8e4d43b917e7706784d8bb445c9af86a3540` |
| Qwen/Qwen2.5-0.5B-Instruct, legacy control | `7ae557604adf67be50417f59c2c2f167def9a775` |

The two Qwen3.8 resolved templates are byte-identical, SHA-256 `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`. Thus agreement here is a shared-template result, not two independent model-behavior replications.

## Actual local input construction

Two synthetic histories are used: an older assistant reasoning field followed by the user's withdrawal of publication permission; and that same history followed by a current-turn read-only tool call and a stale synthetic status result. Both reasoning strings are hand-written markers, not actual model-generated reasoning or any private conversation.

For each tokenizer, cross thinking default/on/off and preserve_thinking default/on/off over the two histories. The 54 cases are 18 input-rendering cases per tokenizer, not 54 model responses.

Both current Qwen templates produced the following pattern:

| Explicit settings | New generation prefix | Reasoning supplied before latest user message | Reasoning supplied in the current tool turn |
|---|---|---|---|
| Defaults | Open `<think>` block | Retained | Retained |
| `enable_thinking=False` only | Empty, already closed thinking block | Retained | Retained |
| `preserve_thinking=False` only | Open `<think>` block | Removed | Retained |
| Both False | Empty, already closed thinking block | Removed | Retained |

The legacy Qwen2.5 template does not serialize either supplied reasoning_content field and does not open a thinking block in these cases. Passing the optional flags does not change that template's output. This is a compatibility observation, not a defect in a model that did not promise those features.

All 54 cases preserved the visible message contents and their order, including exactly one copy of the latest user's withdrawal. All 54 native tokenization results matched tokenizing the rendered text without extra special tokens. The presence of an old reasoning marker does not establish that a model will follow it, and preserved user text does not establish that a model will obey it.

An additional source-level distinction matters: with default thinking, these current templates insert the xhigh reasoning-effort instruction as well as opening the thinking prefix. Therefore switching thinking on/off changes more than a single output delimiter. No low/medium effort behavior was tested.

## Consequences for the next behavior experiment

Our previous small-model studies inspected immediate A/B/C next-token scores and verified that the unconstrained top token was a label. We must not transfer that procedure blindly to a prompt whose continuation is inside a thinking block. A probability at that position is not automatically a final-answer probability. Template inspection does not tell us which token the model would actually select.

The next comparison should keep these conditions explicit:

1. Named checkpoint or named hosted model, with its own version identity. Do not treat QwenCloud's hosted Flash as identical to the downloadable Flash-Next checkpoint.
2. Thinking on/off and supplied reasoning-history preservation on/off, varied separately. Preserve=False is not an instruction to erase all context or all current-turn reasoning.
3. Parse the final answer after reasoning; count truncation, missing final answers and tool-call-only responses separately instead of quietly forcing A/B/C.
4. Test whether a fresh user correction overrides an old plan with and without that old plan's supplied reasoning in context. This remains a question to measure, not a failure already found in Qwen3.8.

The official [QwenCloud thinking guide](https://docs.qwencloud.com/developer-guides/text-generation/thinking) and checkpoint card also distinguish cloud parameter placement from self-hosted chat_template_kwargs. No hosted endpoint or parameter-routing behavior was executed in this preflight.

## Execution, corrections and audit

[Completed run 36161047875](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36161047875) used Transformers 5.17.0, tokenizers 0.23.2, huggingface-hub 1.33.0 and Jinja2 3.1.6. The [5.17.0 release](https://github.com/huggingface/transformers/releases/tag/v5.17.0) was the latest stable GitHub release observed during planning. Only tokenizer/config/template/card/license files were downloaded. PyTorch and model weights were not installed. Network access was disabled after asset preparation; recorded socket/DNS attempts during rendering were zero.

Two earlier attempts are retained rather than presented as model failures. Run 36160518952 lacked the optional Jinja dependency and stopped before rendering. Run 36160691944 collected all three official asset snapshots but our logger assumed a list rather than the returned BatchEncoding object. The corrective [patch](tokenizer_return_contract.patch) requests return_dict=True, reads input_ids explicitly and pins the already collected current-model revisions. Neither the message fixtures nor the integrity criteria were relaxed.

The successful executed probe has SHA-256 `3166f2e28a0fd9e8b1b845d7a449ebe17e01e0d23eba3e1ba08ed0d11c6d8e3e`. The repository preserves the initial probe and explicit patch; the downloaded final artifact's probe.py is already patched. The complete dependency environment is retained.

A separate offline readback verified all render hashes, the exact fixture schedule, all 23 downloaded asset hashes and all message-order checks. It also re-rendered all 54 prompts with local Jinja2 and matched the recorded text byte-for-byte. Local readback did not rerun tokenizer IDs; that cross-check was performed in Actions. [READBACK_AUDIT.json](READBACK_AUDIT.json) records the distinction. Neither run is an external model replication.

Final [artifact 10875244572](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36161047875/artifacts/10875244572): 17,790,984 bytes, SHA-256 `5319a4ea587dad0dca8e2d53432622e22530803f7fe39709f0a0a0e864eab896`. It includes every rendered prompt, token IDs, official assets and their licenses, source, patch, protocol, versions and logs. Actions retention ends 25 October 2026. The conversation evidence bundle preserves the final ZIP and both preceding failure logs.

From the extracted final artifact, a standard-library audit does not need model weights:

```bash
python probe.py audit --out results
```

To rerun input construction, install the recorded tokenizer dependencies and use a new output path:

```bash
python probe.py run --out fresh_preflight
```

## Status

Current-model input compatibility is checked; current-model accuracy, tool behavior and neural interventions remain unmeasured. No third-party issue/PR/comment was posted, no paid inference was launched, and no user device was changed. The broader research target now prioritizes these current models and native reasoning/continuity features. Older small-model results remain diagnostic evidence, not evidence about this generation.

Youngseok Oh supplied project direction; Zero designed, executed and audited this preflight as an AI collaboration partner. Official assets remain the model authors' work. No maintainer endorsement, independent scientific replication or human code review by Youngseok is claimed.
