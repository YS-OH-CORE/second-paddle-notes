# PyTorch: intermediate tangent mutation after functionalization

**A bounded CPU experiment reproduced an output-tangent difference between eager execution and internal `dispatch_functionalize` using the two changed runtime Python files from [PR #192656](https://github.com/pytorch/pytorch/pull/192656).** The candidate passed three controls and failed the intermediate-mutation comparison: eager returned `[48., 54.]`, while the functionalized path returned `[18., 24.]`. This is a two-file source overlay on a fixed wheel, not a complete build of either upstream commit. [Observed candidate results](receipts/attempt2/candidate.json), [raw failure output](receipts/attempt2/candidate.stderr.log)

The existing implementation is by **HussainNizamani**. This additional experiment investigates the proposed fresh-tangent semantics and preserves that authorship.

## Witness and results

```python
def f(dual):
    work = dual * 2
    fwAD.unpack_dual(work).tangent.add_(10)
    return work * 3
```

The test uses float64 primal `[1., 2.]` and input tangent `[3., 4.]`. In eager execution, the intermediate tangent becomes `[6., 8.]`, then `[16., 18.]` after mutation, and the final multiplication produces `[48., 54.]`. Tangent extraction occurs inside the active forward-AD dual level. The complete executable witness is in [repro.py](repro.py).

| Candidate case | Eager output tangent | Functionalized output tangent | Result |
|---|---|---|---|
| Read-only tangent inspection | `[18., 24.]` | `[18., 24.]` | Pass |
| Mutation of an explicit tangent clone | `[18., 24.]` | `[18., 24.]` | Pass |
| Mutation of the intermediate's actual tangent | `[48., 54.]` | `[18., 24.]` | Assertion failure |

The eager analytic-oracle test also passes, for **3 passes, 1 failure, 0 errors, and 0 skips** on the candidate files. All completed cases return primal `[6., 12.]`. Both input tensors' **values** remain unchanged; this is not a metadata or storage-identity audit. The failing assertion is specifically the output-tangent comparison, after the primal and input-value comparisons pass. [Structured observations and test statuses](receipts/attempt2/candidate.json), [independent stderr record](receipts/attempt2/candidate.stderr.log)

With the corresponding parent files, the same four tests produce **1 pass, 0 failures, 3 errors, and 0 skips**. The eager oracle passes; all three functionalized cases reach the reproduction's explicit guard because `unpack_dual(...).tangent` is `None`. Those `RuntimeError`s are raised by the test's guard, not directly by PyTorch. The parent therefore does not provide a numerically correct baseline for these functionalized cases. [Parent observations](receipts/attempt2/parent.json), [parent stderr](receipts/attempt2/parent.stderr.log)

Both test processes exit `1` without timing out. The workflow succeeds because [run.py](run.py) requires this exact counterexample and its controls. Missing tests, import errors, unexpected exceptions, failing controls, different numerical values, changed provenance, or incomplete source restoration cannot satisfy that gate. [Final summary](receipts/attempt2/SUMMARY.json)

## Exact execution boundary

| Component | Identity |
|---|---|
| Candidate source | [`eb9c90dd1f2b67cadf9f7681176f1b5fab074423`](https://github.com/pytorch/pytorch/commit/eb9c90dd1f2b67cadf9f7681176f1b5fab074423) |
| Actual candidate parent | [`061ace3a865340a4f6a351e5ef8f3a7f37b6645e`](https://github.com/pytorch/pytorch/commit/061ace3a865340a4f6a351e5ef8f3a7f37b6645e) |
| Installed wheel | `torch==2.13.0+cpu` |
| Wheel binary git version | `cf30153c4c131c8164ee7798e5022d810682e2cb` |
| Interpreter | Python `3.12.3` |
| Installer | uv `0.9.28` |
| Accelerator metadata | CUDA build `None`, HIP build `None`, CUDA available `False` |

The [workflow](workflow.yml) checks out the exact upstream commits. In one disposable wheel environment, the runner replaces only `torch/_subclasses/functional_tensor.py` and `torch/autograd/forward_ad.py`; each variant then runs in a fresh interpreter. All binaries and other Python files remain supplied by the same wheel. The untouched wheel is imported first for provenance, rather than subjected to another functionalization test suite. [Original wheel record](receipts/attempt2/original-wheel.json)

Loaded-file SHA-256 values match the exact upstream sources:

| Variant | Runtime file | SHA-256 |
|---|---|---|
| Parent | `torch/_subclasses/functional_tensor.py` | `91fd79c21e9119a530958514d1de8520098cbaa8f8ad8cf41ad6d898d047a2ad` |
| Parent | `torch/autograd/forward_ad.py` | `289adf8dbb998f011fbe189852bd9f95931c0fe36c12922aacaaa877b96e4a23` |
| Candidate | `torch/_subclasses/functional_tensor.py` | `5e5235ce069c7eae3a06cb0c97e3411e9dfcf190e39abc2d0ad1b275e90a6a51` |
| Candidate | `torch/autograd/forward_ad.py` | `d493b00c81ea6d359b13673c5777c339774f0bd55d93dbaefe10d41c6ef69954` |

See the [source manifest](source-manifest.json) and each variant's raw JSON for provenance. Original files were captured before replacement and restored in `finally`; both restoration hash checks passed. [Restoration record](receipts/attempt2/SUMMARY.json)

Resolved dependencies include `expecttest==0.3.0`, `hypothesis==6.168.3`, `numpy==2.5.3`, and `unittest-xml-reporting==3.2.0`. The [complete package record](receipts/attempt2/packages.txt) preserves the environment; dependencies beyond the explicitly pinned components were resolved during setup, not fully locked in advance.

## Execution history and retained evidence

These were two separate workflow runs; each has GitHub `run_attempt=1`.

| Experiment attempt | CI run | Evidence/workflow commit | Outcome |
|---|---|---|---|
| 1 | [36452573996](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36452573996) | [`db32a8fe695d64b4d774e70dee3272476f521905`](https://github.com/YS-OH-CORE/second-paddle-notes/commit/db32a8fe695d64b4d774e70dee3272476f521905) | Setup failure; zero tests executed |
| 2 | [36453154812](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36453154812) | [`32ec7835739c728cca5d6a48c959da61aaab7832`](https://github.com/YS-OH-CORE/second-paddle-notes/commit/32ec7835739c728cca5d6a48c959da61aaab7832) | Exact required evidence signature established |

Attempt 1 imported both source variants but lacked `xmlrunner`, which PyTorch's runner enables in CI. It supplies no numerical result. Before attempt 2, the environment gained the XML runner dependency; the status recorder was corrected to recognize XML runner's test-ID wrappers, and explicit XML output directories were added. The witness, assertions, and evidence gate were unchanged. [Attempt 1 receipts](receipts/attempt1), [attempt 2 receipts](receipts/attempt2), [attempt ledger](ATTEMPTS.md)

Attempt 2 stderr reports XML generation under a hidden subdirectory derived from the absolute test path. The artifact uploader's [default hidden-file exclusion](https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/action.yml) omitted those XML files. **XML is not retained.** Raw stdout, stderr, return-code records, structured test statuses, source hashes, packages, and summaries are retained; no further run was made solely to collect XML.

## Interpretation and limits

The result is consistent with the candidate's [fresh wrapping of the unpacked tangent](https://github.com/pytorch/pytorch/blob/eb9c90dd1f2b67cadf9f7681176f1b5fab074423/torch/_subclasses/functional_tensor.py#L354-L375) separating its functional mutation history from the tangent subsequently consumed by `work * 3`. The [unchanged `unpack_dual` contract](https://github.com/pytorch/pytorch/blob/eb9c90dd1f2b67cadf9f7681176f1b5fab074423/torch/autograd/forward_ad.py#L151-L158) returns the tangent as-is. This source explanation is an inference supported by the differential experiment.

Only an intermediate is mutated, avoiding the [internal transform's input-mutation propagation exception](https://github.com/pytorch/pytorch/blob/eb9c90dd1f2b67cadf9f7681176f1b5fab074423/torch/_subclasses/functional_tensor.py#L831-L903). Whether this operation should be supported, explicitly rejected, or otherwise documented remains a maintainer decision.

The experiment establishes an **output-tangent discrepancy in the stated source-overlay environment**. It does not establish incorrect gradients in ordinary model training, a complete source-build result, an end-to-end AOTAutograd or `torch.compile` failure, GPU behavior, or behavior of the separate public C++ functionalization fix [#192638](https://github.com/pytorch/pytorch/pull/192638).

## Attribution and upstream status

Upstream copyright and license notices are preserved in [LICENSE.pytorch](LICENSE.pytorch). The two original PyTorch runtime source files are not republished here; the runner obtains them from exact upstream checkouts.

The [upstream comment draft](upstream-comment-draft.md) **has not been posted**. Its AI analysis is contained in a disclosed quote block. PyTorch's [AI policy](https://github.com/pytorch/pytorch/blob/97b6a194e98d7965467541490d74ee44c862a563/AI_POLICY.md) and [agent instructions](https://github.com/pytorch/pytorch/blob/97b6a194e98d7965467541490d74ee44c862a563/AGENTS.md) require actual human review and human commentary before an upstream interaction. This report does not claim those steps occurred, or imply author adoption, maintainer approval, or merge.

Additional experiment and report: **Zero × Youngseok Oh**.

File integrity: [SHA-256 manifest](file-manifest.json).
