# Transformers #48282: composite models omitted from slow-job suggestions

## Observed result

On frozen PR head `f3e3ad778c38990d38100c44c74f2054b9b2aae6`, the actual `utils/get_pr_run_slow_jobs.py` command exits **0** but suggests only `clip` when a CLIP model, configuration, or model-test file changes. Its real reverse configuration map identifies eight dependent model modules, including LLaVA. Those eight are missing from the command output.

This is a focused, AI-assisted CPU diagnosis by **Zero × Youngseok Oh**, responding to [zucchini-nlp's request to review the CI mapping](https://github.com/huggingface/transformers/pull/48282#discussion_r4123602478). The original refactoring and mapping design belong to their authors. It is separate from our earlier Bark configuration diagnosis. No new upstream PR, issue, model inference, or upstream CI dispatch was needed for this experiment.

## Actual CLI comparison

The successful comparison is [run 36476082747](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36476082747), using [verifier commit 87393e1](https://github.com/YS-OH-CORE/second-paddle-notes/commit/87393e1aa28984101ae4e69a143080cd54c2f4fe). Each phase has the same **11 conditions: one real-registry assertion and ten actual CLI subprocess calls**. This is one completed comparison, not independent repeated replications.

| Source variant | Conditions passed | Conditions not met | Verifier exit |
| --- | ---: | ---: | ---: |
| Unchanged PR script | 7 | 4 | 1 |
| Only correct the lookup argument | 6 | 5 | 1 |
| Correct argument, normalize paths, filter against inventory | 11 | 0 | 0 |

**All ten CLI subprocesses in each installed-environment phase exited 0.** The verifier exits 1 when their output does not match the stated conditions. The workflow is green because it checks this exact positive/negative matrix, not because the original PR passed all conditions. [Complete results](receipts/attempt2/SUMMARY.json).

For a single modified `src/transformers/models/clip/modeling_clip.py`, with the full directory metadata derived from the frozen repository:

```text
Original:
clip

Normalized/filtered diagnostic variant:
clip, granite4_vision, llava, llava_next, llava_next_video, omdet_turbo, sam3, video_llava, vipllava
```

The actual mapping independently returns these eight parents: `granite4_vision`, `llava`, `llava_next`, `llava_next_video`, `omdet_turbo`, `sam3`, `video_llava`, and `vipllava`. All corresponding directories exist in the frozen full inventory. Nine total jobs are below the existing 16-job suggestion cap. The same omission occurs for a changed CLIP configuration file and model-test file.

## Mechanism and narrow intervention

The [original call site](https://github.com/huggingface/transformers/blob/f3e3ad778c38990d38100c44c74f2054b9b2aae6/utils/get_pr_run_slow_jobs.py#L67-L72) passes the function itself:

```python
if multimodal_parents := get_composite_files(get_composite_files):
    jobs_to_run.extend(multimodal_parents)
```

The map has string keys, while this argument is a hashable function object. The lookup returns an empty list without raising an exception. The diagnostic variant passes the backbone module name, retains the `models/` namespace used by the rest of the job list, and checks that each parent exists in the supplied repository inventory:

```python
if item.startswith("models/"):
    jobs_to_run.extend(
        f"models/{parent}"
        for parent in get_composite_files(item.removeprefix("models/"))
        if f"models/{parent}" in repo_content
    )
```

[Exact executed diagnostic diff](receipts/attempt2/normalized_filtered/diagnostic.patch). This changes one temporary script, not the workflow or upstream branch. Original source bytes were restored afterward, and the runner asserts a clean working tree.

### What the argument-only comparison does and does not show

Correcting only the argument **does restore all eight parents for the full inventory**. Its three full-inventory output checks fail only because the mixed bare-parent / `models/clip` names sort differently before their prefixes are removed. This is an ordering difference, not missing model coverage.

The other two failures use deliberately narrowed metadata: one inventory contains only CLIP and LLaVA, and one only CLIP. The argument-only variant still emits all eight parents, including directories absent from that supplied inventory. The normalized/filtered variant emits `clip, llava` and `clip`, respectively. These are synthetic inventory-boundary controls, not a claim that those directories are currently absent upstream.

The remaining controls preserve existing behavior for removed files, unrelated documentation, explicit model requests, invalid explicit names, and explicit quantization selection. The AWQ source-file control intentionally expects no automatic job because the source maps to `quantization/awq` whereas the real test directory is `quantization/autoawq`. This experiment does not repair or claim to validate a new AWQ routing behavior.

## Separate startup-dependency observation

Before the installed-environment phases, the actual candidate script was also invoked in an isolated clean Python environment with `--message 'run-slow: clip'`. It failed at the new top-level Transformers import with `ModuleNotFoundError: No module named 'transformers'`. [Probe command/result](receipts/attempt2/clean_environment.json) and [full exception](receipts/attempt2/clean_environment.stderr).

The inspected [suggestion workflow](https://github.com/huggingface/transformers/blob/f3e3ad778c38990d38100c44c74f2054b9b2aae6/.github/workflows/pr_slow_ci_suggestion.yml) checks out **main**, writes JSON metadata, and calls this script without a Python dependency-install step. This makes the new runtime dependency worth resolving separately. **We did not execute that upstream workflow, inspect its live runner packages, or establish that current production suggestions are broken.** Its main-branch execution is distinct from directly testing the unmerged PR script. No change to its trust or permission boundary is proposed.

## Method and reproduction

- Complete Transformers source checkout at `f3e3ad778c38990d38100c44c74f2054b9b2aae6`.
- Original script Git blob: `8b2955aff265d9a9a6c11833ddf369ead889660c`; SHA-256: `51adf69edb98e69a2f110ba5c048dcffc9d1904e443df4c118dbfac45da86d48`.
- Python 3.12.3; Transformers 5.18.0.dev0 from that checkout; Torch 2.13.0+cpu. [Installed packages](receipts/attempt2/packages.txt).
- Real configuration registry and actual CLI, with synthetic changed-file inputs and directory metadata derived from the source snapshot. No map substitution or mocked configuration classes.
- Fresh subprocesses; Hugging Face offline/telemetry flags enabled during checks; no model weights, model construction, GPU, network model requests, upstream job dispatch, or repository credentials passed into test commands.
- [Verifier](check.py) and [workflow](workflow.yml) are the exact corrected version executed. The workflow's checkout and action revisions are pinned. Package installation and source checkout use the network before the tests.

With the frozen source and its dependencies installed:

```sh
python check.py --source /path/to/frozen/transformers --output /path/to/new/receipts
```

The output directory should be new. Only the target source script is changed for the diagnostic phases; it is restored in a `finally` block. The verifier checks Git HEAD, clean working trees, the real CLIP-to-LLaVA relationship, exact outputs, process exit codes, and the final expected result matrix.

## Attempt history and retained evidence

| Attempt | Workflow run | Outcome |
| --- | --- | --- |
| 1 | [36475774270](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36475774270) | Our setup precondition incorrectly assumed an `awq` test directory instead of `autoawq`. All three installed phase drivers stopped before the ten CLI cases. The outer summary also raised a `KeyError` for the missing phase record. No completed 11-condition comparison. The separate clean-environment import probe did execute. |
| 2 | [36476082747](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36476082747) | Corrected the fixture to the actual directory and preserved the argument-only ordering/inventory distinctions. The complete 7/11, 6/11, 11/11 matrix was observed. Source restoration was confirmed. |

The 16 files from attempt 1 and 79 files from attempt 2 are preserved as downloaded text receipts, including empty stdout/stderr files, setup output, exceptions, both diagnostic patches and phase results. They are not 95 successful tests. [Attempt 1](receipts/attempt1/) · [Attempt 2](receipts/attempt2/).

GitHub reports artifact 10994190650 as 6,027 bytes with digest `a55eab1b592159f55044f52272bc6360380b1be599e1c8d6477f8698167f7155`; artifact 10993787166 as 21,499 bytes with digest `40c7b32f51b137c9d3bc2901dab0d57fd24a93e0653e048c8ad3d09e3ae5d6a6`. These are publisher-reported ZIP digests, **not independently recomputed ZIP checksums**. Artifact retention is 30 days; the text records here preserve the evidence beyond that window. [File manifest](file-manifest.json).

## Limits, attribution, and delivery

This validates the stated CLIP direct-dependency suggestion cases, not all backbones, transitive dependency closure, the maximum-job policy, all models' import compatibility, GPU tests, or an end-to-end CI pipeline. The normalized/filtered intervention is a diagnostic candidate, not a fully validated upstream fix. The source-only dependency concern is separate from the executed output mismatch.

Original implementation and review direction: zucchini-nlp and the existing Transformers reviewers. Independent diagnosis, controls, and reporting: **Zero × Youngseok Oh**. AI assistance was used for source review, verifier development, execution setup, and reporting. Upstream-context patches are covered by the accompanying [Transformers license](LICENSE.transformers).

The report was delivered as one [reply to the existing author review thread](https://github.com/huggingface/transformers/pull/48282#discussion_r4126587009) on 28 September 2026 at 20:13:12 UTC. The existing account-owner GitHub CLI authorization was used. The posted account, parent thread and complete body were checked, followed by an independent GitHub-connector readback. [Delivery receipt](delivery.json) and [exact posted body](upstream-reply.md) are retained. Maintainer acknowledgment, adoption and merge are not established.
