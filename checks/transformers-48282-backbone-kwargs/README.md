# Transformers #48282: consumed backbone options survive parent serialization

Supplemental config-only execution for [molbap's existing review question](https://github.com/huggingface/transformers/pull/48282#discussion_r4131792526), already acknowledged by the PR author. This is not a new issue, a competing implementation or a claim to have first identified the missing kwargs return.

## Observed

With an explicit ResNet subconfig and legacy backbone options, the baseline consumes the legacy options. The PR retains all four as parent attributes and writes them to `config.json`; local reload retains them too. No exception or model-inference regression is claimed.

```python
from transformers import RTDetrConfig, ResNetConfig
cfg = RTDetrConfig(
    backbone_config=ResNetConfig(),
    backbone="synthetic-unused-name", use_timm_backbone=False,
    use_pretrained_backbone=False, backbone_kwargs={},
)
legacy = ("backbone", "use_timm_backbone", "use_pretrained_backbone", "backbone_kwargs")
print({key: cfg.to_dict()[key] for key in legacy if key in cfg.to_dict()})
# baseline: {}
# PR: all four legacy keys remain
```

These are accepted constructor inputs in both inspected revisions. The test does not invent a new precedence rule for conflicting backbone settings.

| Same eight scenarios | Passed | Failed | Process exit |
|---|---:|---:|---:|
| Prior main `2e703d6c` | 8 | 0 | 0 |
| PR `f3e3ad77` | 0 | 8 | 1 |
| PR plus diagnostic downstream cleanup | 8 | 0 | 0 |

## What the scenarios check

The eight cases are DetrConfig, RTDetrConfig, MaskFormerConfig and DPTConfig, each with a dictionary or an existing config object. Each follows construction, `from_dict`, local `save_pretrained`, and local `from_pretrained`. Caller input preservation, unrelated parent metadata and the selected ResNet fields pass in **all** phases. Only the consumed-key check differs. Eight cases with four checkpoints are not 32 distinct regressions.

The object-input cases matter: returning cleaned kwargs only from the consolidation branch is not enough if the existing-object early return bypasses that consumption. The final implementation can thread the remaining kwargs through the API or consume them centrally; the attached three-line [diagnostic.patch](diagnostic.patch) only establishes the narrow cause. It is not a complete production repair and was applied to a separate source copy.

The common parent calls `create_subconfig(..., **kwargs)`, so the helper's private keyword dictionary can be cleaned without updating the parent's. The parent later installs the original remaining kwargs as attributes. The added test makes that boundary visible through the saved file and reload, not merely by inspecting a helper return.

## Reproduce

Use a disposable Python environment with the pinned PR's declared dependencies installed. No torch, model weights, tokenizer fixture, Hub dataset or paid model is needed. The reviewer sets offline flags and rejects socket connects during execution.

```sh
python check_backbone_kwargs.py --source /path/to/full/source-checkout --out /new/results-directory
```

Run each source in a separate interpreter with the same environment. The output includes all eight cases, each checkpoint's retained legacy fields, controls, and versions. The PR process is expected to exit 1 under these baseline-preservation assertions, not because of setup or import failure.

## Provenance and limits

Baseline: `2e703d6c7e81ec584c25edc39e8bd2f5a45b04bd`, the baseline used in the earlier Bark diagnosis, not the PR's immediate parent. PR: `f3e3ad778c38990d38100c44c74f2054b9b2aae6`. Complete source archives were obtained from GitHub; the common config and backbone files were independently checked against their Git blobs. Both original source copies remained unchanged.

Python 3.12.10 on Windows; Transformers 5.18.0.dev0, huggingface-hub 1.33.0, tokenizers 0.23.2, numpy 2.5.3. One isolated environment, no model execution and no socket attempts during the tests. [summary.json](summary.json) records hashes; [baseline.json](baseline.json), [head.json](head.json) and [diagnostic.json](diagnostic.json) preserve outcomes with only the local absolute source path removed. Raw outputs and setup records are kept in the owner's local archive.

This is not the upstream suite or validation of all 313 changed files. It does not establish an effect on model outputs, pretrained weight loading, or every backbone family. No existing project tests were altered. The original refactor belongs to zucchini-nlp and the review question to molbap. Supplemental AI-assisted tests, execution and writing by Zero, under Youngseok Oh's direction. No unaided human line-by-line review or maintainer acceptance is asserted. The diagnostic context remains under [Transformers' license](LICENSE.transformers).

**Zero × Youngseok Oh**
