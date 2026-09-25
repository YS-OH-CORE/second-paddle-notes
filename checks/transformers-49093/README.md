# Transformers #49093: isolated and combined regression checks

**Result:** on the pinned Transformers package below, the original implementation passed 5 of 10 selected checks, each candidate fix alone passed 7, and both fixes passed all 10. These are targeted regression cases, not a model accuracy benchmark.

The issue reporter **lucaluo925** supplied both diagnoses and both candidate changes in [Transformers #49093](https://github.com/huggingface/transformers/issues/49093). Zero, an AI assistant collaborating with Youngseok Oh, added and executed the supplemental checks. No upstream fix authorship is claimed.

## What ran

- Upstream source: [`89b6b17574892ec0770551537a3fe69d6886703e`](https://github.com/huggingface/transformers/commit/89b6b17574892ec0770551537a3fe69d6886703e), reported package version `5.18.0.dev0`.
- Execution: Python 3.12.3, PyTorch 2.6.0+cpu, CPU float32, synthetic score tensors. The complete installed package and complete `logits_process.py` variants were imported; no selected-function substitutes were used.
- [Successful GitHub Actions run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36093567053), run ID `36093567053`, 2026-09-25 04:13–04:14 UTC.
- [Checker source](check_sequence_bias.py), [all observations](report.json), [run metadata](run_metadata.json), and [installed versions](environment.txt).
- The exact source file was checked against Git blob `7ff6a32c026efb139cc89996e07181f141cce971` before applying either edit.

Fix A changes the list-format token-ID predicate from `> 0` to `>= 0`. Fix B changes the context guard from full-sequence length to prefix length: `len(sequence_ids) - 1 > input_ids.shape[1]`. The checker requires exactly one occurrence of each original condition.

## Observed matrix

| Case | Original | A only | B only | A + B |
|---|---:|---:|---:|---:|
| Token 0, dict/list parity with empty context | Fail | Pass | Fail | Pass |
| Token 0 after `GenerationConfig` JSON save/load | Fail | Pass | Fail | Pass |
| Full-context prefix with overlapping additive biases | Fail | Fail | Pass | Pass |
| Full-context prefix in `NoBadWords`, with singleton EOS exemption | Fail | Fail | Pass | Pass |
| Token-0 prefix after JSON save/load, requiring both fixes | Fail | Fail | Fail | Pass |
| Genuinely insufficient prefix; empty context plus unigram | Pass | Pass | Pass | Pass |
| Longer matching context and a nonmatching batch row | Pass | Pass | Pass | Pass |
| Negative token ID still rejected | Pass | Pass | Pass | Pass |
| Out-of-vocabulary token ID still rejected | Pass | Pass | Pass | Pass |
| Nonzero unigram biases still applied | Pass | Pass | Pass | Pass |
| **Passed cases** | **5/10** | **7/10** | **7/10** | **10/10** |

All 40 observed outcomes matched the predicted matrix. Scores started nonzero, and comparisons covered the entire output tensor, including unaffected tokens and other batch rows. Passing tensor comparisons also checked that input IDs and input scores remained unchanged.

### Why the combined case matters

The checker saves `GenerationConfig(sequence_bias=[[[0, 4], -2.5]])`, reads the resulting JSON back through `GenerationConfig.from_pretrained`, then applies the restored rules to contexts `[[0], [3]]`.

The original and B-only implementations reject token 0 in list format. A alone accepts the configuration but leaves the matching row's token-4 score at `1.0`; it should be `-1.5`. Both fixes apply the missing `-2.5` contribution, while the nonmatching row stays unchanged.

The additive check similarly isolates the missing boundary contribution. Rules `(1, 3, 4): -2.0`, `(3, 4): +0.5`, and `(4,): +0.25` should add together on context `[1, 3]`. The original and A-only implementations produce `1.75` at token 4 instead of `-0.25`, exactly omitting the `-2.0` term. The shorter-prefix and singleton contributions remain present.

In the bad-word boundary check, the same variants leave the matching score at `1.0` instead of `-inf`. B corrects that coordinate while preserving the single-token EOS exemption and the nonmatching batch row.

## Reproduce

Create a Python environment with the pinned package and CPU PyTorch, then run:

```bash
python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install https://github.com/huggingface/transformers/archive/89b6b17574892ec0770551537a3fe69d6886703e.zip
python check_sequence_bias.py --out ./sequence-bias-results
```

Use a fresh output directory. The script preserves complete source variants and per-case expected/actual scores. The workflow additionally preserves the environment and execution log. See `environment.txt` for all dependency versions used in the recorded run.

## Scope and verification

This checks logits processors and actual configuration serialization. It does not run `generate()`, load model weights, test GPU execution, or run the full upstream test suite. It is not an independent external replication.

The checker records any exception as a failed case, so the retained failures were inspected before reporting: every A-related rejection is the specific token-0 validator `ValueError`; every tensor failure has only the intended missing score contribution. The saved log's 40 rows exactly match `report.json`, and the preserved checker matches the executed checksum.

The original run artifact is `zero-transformers-49093-20260925`, ID `10846617066`, SHA-256 `4003558c37e374bfe1e5a4a93c8bf6bf99b056995a22f65fb32312d564f5bd07`. GitHub Actions retention is 30 days; the report, checker, metadata, and environment are committed here.

During the final overlap check, [PR #49099](https://github.com/huggingface/transformers/pull/49099) by **aniketkrs** appeared, based on the same upstream commit. Its diff implements the same two intended corrections, assigning `prefix_length` before the guard. This run tested the reporter's candidate edits on the pinned base; it did not execute PR head `e435677fb9981b3f2bfc7abeaabcb394e47c29e2`. These results are offered as supplemental regression evidence for the existing discussion.
