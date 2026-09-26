# Nine failing cases are not one streaming bug

Youngseok Oh × Zero | 26 September 2026

**We replayed all nine cases requested in [CanIToolCall issue #10](https://github.com/redd34/canitoolcall/issues/10) through the original vLLM 0.30.0 parser stack. The results reproduce the author's saved snapshot, but the cases need different explanations.** One rejects the malformed header identically in both modes; only one changes with streaming chunk boundaries. The attached patch changes triage descriptions only. All nine remain `fail` under the unchanged conformance checks.

## Actual execution, not constructed parser answers

CanIToolCall was pinned at `5670805d5b140230a323536c5de9a89091ad02d2`. The project's unchanged `scripts/engines/vllm.sh` installed its CPU-only parser environment and verified the original vLLM wheel. Our [replay.py](replay.py) calls the original adapter, worker and evaluator using the nine existing token sequences, without changing fixture expectations or engine code.

Each fixture was parsed once without streaming and with eight token-grouping strategies: `one`, `special`, `token`, and five seeded random groupings. The whole selection was repeated: **9 fixtures × 9 modes × 2 passes = 162 parser replay sessions**. A streamed session includes multiple parser-delta calls; this is not 162 model generations or 162 independent bugs.

The two passes produced identical observation dictionaries. All **81 first-pass parser results** also matched the author's committed 2026-09-25 snapshot. Model calls, real tool executions and measured-phase network attempts were zero. Tokenizer/configuration downloads and parser initialization occurred before blocking Python sockets/DNS. We did not run a live HTTP server or regenerate model output.

## Proposed triage, with unresolved decisions left visible

| Fixture or group | Actual observation | Proposed classification |
|---|---|---|
| `gpt-oss/vllm-malformed-headers` | Same recovered messages, but one-shot joins them with an internal newline and streaming concatenates them. All stream chunkings agree. | `intended_engine_behaviour`, subject to maintainer review |
| `mistral/v13think-stop-at-open-marker` | Output ends at the call opener. One-shot returns no call; all streams accumulate one empty-name, empty-argument call. | `truncation_policy`, subject to maintainer review |
| `gpt-oss/bug-garbled-channel-commentary-question` | Same `HarmonyError` in one-shot and every stream. The fixture's accepted error outcomes exclude exceptions. | Unresolved malformed-header recovery contract, not a cross-mode disagreement |
| `deepseek/vllm-v3-malformed-missing-brace` | One-shot and some streams return invalid argument fragments; `one`/`special` return no call. This alone is split-sensitive among these nine. | Unresolved malformed-call-fragment behavior |
| The other five cases, listed below | No calls or exceptions. Each individual error outcome is permitted, but recovered text differs between one-shot and streaming. All stream chunkings agree. | Unresolved text-recovery contract |

The five text-recovery cases are `deepseek/vllm-v3-malformed-missing-call-tokens`, `mistral/vllm-v3-malformed-not-json`, `qwen3-hermes/bug-sglang-30480-truncated-at-opener`, `qwen3-hermes/sglang-malformed-json-in-tags`, and `qwen3-hermes/truncated-after-open-tag`.

Thus the proposal assigns two cases to existing policy/intended categories and leaves **seven explicitly unresolved** in narrower groups. It does not declare nine problems fixed or introduce new confirmed engine-bug reports.

### Why the newline case is different

vLLM's original [non-streaming recovery test](https://github.com/vllm-project/vllm/blob/ced6857afa0ea7b2e3f0846a62e1394e90f15607/tests/parser/test_harmony.py#L443-L457) and [streaming recovery test](https://github.com/vllm-project/vllm/blob/ced6857afa0ea7b2e3f0846a62e1394e90f15607/tests/parser/test_harmony.py#L552-L577) explicitly assert their respective joining behavior. Those source tests include a terminal token that this corpus fixture removes; our actual replay confirms the same newline difference without it. This supports a triage explanation, not weakening the current stream-equality check.

For the Mistral malformed-JSON case, an [upstream test explicitly expects the one-shot text fallback](https://github.com/vllm-project/vllm/blob/ced6857afa0ea7b2e3f0846a62e1394e90f15607/tests/parser/mistral/test_tool_calls.py#L508-L517). That alone does not establish the intended streaming contract, so this case remains unresolved.

## Review-only patch

[triage.patch](triage.patch) updates only `results/2026-09-25/triage.py` and its generated `triage.jsonl`. It replaces the nine-case catchall entry with five named findings, each carrying fixture IDs, a summary, reproduction command and scope note. Fixture records, evaluator rules, parser code and all five archived engine-score files remain unchanged.

There is one necessary generator synchronization outside that catchall: the committed JSON already had the author's platform-dependent Ollama int64 wording, while the generator retained the older description. The patch copies that existing published wording back into the generator so regeneration does not revert it. This is not a newly measured Ollama result. Every unrelated published finding remains identical.

On a disposable checkout at the pinned commit, with the project's test dependencies available:

```sh
git apply --check /path/to/triage.patch
git apply /path/to/triage.patch
python results/2026-09-25/triage.py
python -m pytest -q tests/core/test_results_snapshot.py
```

The unchanged upstream snapshot-assignment test passed locally: **1 test passed, no errors or skips**. It checks that failing cases remain assigned exactly once. Regeneration was byte-identical on repetition; applying the patch to clean original files reproduced both candidate files exactly. These checks do not decide whether the proposed categories should be accepted.

## Failure retained, then corrected

[First run 36229144949](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36229144949) built the engine successfully but failed while our code serialized the first fixture's results: `dataclasses.asdict` retained a `frozenset` that JSON could not encode. Nine parser sessions ran before that recording failure. It did not complete the requested nine-case set.

We changed our recorder to use the upstream result object's `to_dict()` method. No fixture, parser or scoring rule changed. [Second run 36229333092](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36229333092) completed both passes. Its green workflow means successful reproduction and recording; all nine conformance outcomes are still failures.

## Evidence and limits

Corrected script commit: `ea8fb9f56701d107a9be4651f554b586aab46dc1`; SHA-256 `db225584f73b2025af4978e9b606b450cfddf8d9aea5e8af5fd0474765768464`. Workflow commit: `a91c1feed909488834ae0eaf27b688e389e64bcc`.

vLLM wheel SHA-256: `ef52ee58c410ead0b8afb190838fa4cbcb52075596f67862a03859d984966ac4`. The parser environment used Python 3.12.11, torch 2.14.0+cpu, transformers 5.17.0, tokenizers 0.23.2, openai-harmony 0.0.8 and mistral-common 1.12.0. The complete environment is retained in the artifact. No weights or GPU execution were used.

[Successful artifact 10902041320](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36229333092/artifacts/10902041320): 1,082,208 bytes; SHA-256 `0ec1966d49d9df99e7bcf32cf5f79aa078916f6f0c299539b71dd8be4b2171e0`.

[Failed-attempt artifact 10902421020](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36229144949/artifacts/10902421020): 1,067,059 bytes; SHA-256 `9533cb28b07a3294f2f2cc0d6b6d7b383d9e1155ee11da6fcbd7ce203fb70d0e`. Actions retention is 30 days. Both archives are preserved in the conversation evidence bundle, together with the patch, local checks and readback.

Patch SHA-256: `417f42ec0984299f45bb9919a26d20b58e0fdc6a28acbf2ab05c79a05b7e68dd` (20,478 bytes). [AUDIT.json](AUDIT.json) records exact replay/patch checks. Local readback recomputed all 18 case scores from the saved parser replies and checked logs, source hashes, snapshot equality and patch application; it did not rerun the engine locally.

This independently repeats the author's parser observations, not the generation of those inputs or the correctness of every ground-truth expectation. Two repeats in one environment do not establish behavior on every version or server. No runtime fix, upstream merge, maintainer acceptance or production-security claim is made. Original fixtures, evaluator and engine code remain their authors' work. Zero, working with Youngseok Oh, supplied the replay, analysis and review-only patch; AI participation is disclosed in the repository's authorship context. Any new upstream engine reports remain for the project maintainers after review.
