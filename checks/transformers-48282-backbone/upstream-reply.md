AI-assisted CPU follow-up on this mapping at `f3e3ad778c38990d38100c44c74f2054b9b2aae6`: the map contains CLIP -> LLaVA, but the actual suggestion CLI prints only `clip` (exit 0) for a changed CLIP model/config/test file.

The call site passes the function as the key:

```python
get_composite_files(get_composite_files)
```

That is a valid hashable key, so the string-keyed map returns `[]` rather than raising. With the full directory inventory, the real map has eight CLIP parents: `granite4_vision`, `llava`, `llava_next`, `llava_next_video`, `omdet_turbo`, `sam3`, `video_llava`, and `vipllava`. None appears in the original CLI output; nine total jobs would be below the 16-job cap.

I compared the unchanged script with two small interventions using the real registry and CLI, synthetic changed-file metadata, and directory metadata from the complete frozen checkout. The same 11 conditions give:

| Variant | Conditions met |
| --- | ---: |
| Original | 7/11 |
| Argument-only correction | 6/11 |
| Correct argument + `models/` normalization + inventory filter | 11/11 |

The argument-only correction **does restore all eight parents** in the full-inventory cases. Its five unmet conditions are three ordering-only differences and two deliberately narrowed-inventory controls, not five coverage omissions. All ten actual CLI invocations per installed-environment phase exit 0; the verifier checks their output.

The [executed diagnostic diff](https://github.com/YS-OH-CORE/second-paddle-notes/blob/42bc566da6ff91bb3db6b5afa7e067dfd86336a2/checks/transformers-48282-backbone/receipts/attempt2/normalized_filtered/diagnostic.patch) passes the backbone name, keeps parent entries in the existing `models/` namespace, and checks them against `repo_content`. Removed-file, documentation, explicit model/quantization, and invalid-name controls retain their behavior.

Separate setup point: the new top-level Transformers import fails in a clean interpreter even for `--message 'run-slow: clip'`. The inspected suggestion workflow has no dependency-install step and runs **main**, not this PR head. I have not run that upstream workflow or established a current live-CI failure; how should this script receive its registry dependency?

[Reproducer, source/environment details, both attempts and complete receipts](https://github.com/YS-OH-CORE/second-paddle-notes/blob/42bc566da6ff91bb3db6b5afa7e067dfd86336a2/checks/transformers-48282-backbone/README.md) · [Completed CPU comparison](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36476082747). Attempt 1 stopped on my incorrect `awq` versus `autoawq` fixture assumption; its failure is retained. No model execution or upstream CI dispatch; no full-PR compatibility claim.

Zero × Youngseok Oh
