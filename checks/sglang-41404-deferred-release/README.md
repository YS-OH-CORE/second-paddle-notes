# SGLang #41404: unchanged CPU suite and a PP ordering question

## Observed result

The **unchanged** `test/registered/unit/disaggregation/test_deferred_decode_kv_release.py` at [PR #41404](https://github.com/sgl-project/sglang/pull/41404), frozen head `d574752ef39eb3ef73f87c40dca95d76222f9483`, passed **24 tests with no failures, errors, or skips** in a CPU environment. The direct unittest process exited 0. An earlier import-only probe checked the actual module paths and exact source bytes, discovered the same 24 tests, and did not itself execute tests.

[CI run 36460117279](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36460117279) · [Raw test stderr](receipts/attempt1/upstream.stderr) · [Method execution log](receipts/attempt1/upstream.stdout) · [Source/import receipt](receipts/attempt1/import.json) · [Summary](SUMMARY.json)

This establishes that the existing suite runs successfully with actual SGLang imports in the recorded environment. **It is not a reproduction of the additional partial-publication / intervening-abort hypothesis below.** No new test case or production patch was applied. The existing tests and PR implementation remain their original authors' work, including ShangmingCai's contribution.

## Additional source-review question

The PR adds forced drain-ack registration when a failed transfer reaches `pop_transferred`. Its notification call remains conditional on `not abort_notified`. A separate `abort()` can set `abort_notified` while leaving the tracker unarmed when metadata publication ended before `init_time` was set. The question is whether that earlier notification can bypass the later forced registration in a real scheduler ordering.

The inspected PP/device loop supports a source-level route: it snapshots transfer IDs before adding newly preallocated requests; the current release-ID list can therefore exclude a new request, and a later iteration ingests external input before transfer cleanup. The [detailed source assessment](reachability.md) walks through the exact frozen lines, receiver state transitions, a two-peer PP/TP mapping, and remaining limits.

**Evidence status: inference, unexecuted.** The composed sequence was not run, and full ServerArgs/model initialization and a distributed PP server were not launched. The inferred effect is delayed reclamation until the bounded device-release timeout despite a possible drain acknowledgment. This report does not establish corruption, an unbounded leak, or measured service impact.

Two tempting alternative arguments were rejected during source review: built-in backends do not support a positive host-receive threshold at this head, and unequal PP sizes violate the inspected mapping assertion when decode PP is greater than one. The retained argument uses device destinations, threshold zero, equal PP sizes, and unequal TP sizes. See [excluded routes and exact references](reachability.md#excluded-reachability-arguments).

## Environment and source integrity

| Component | Observed identity |
| --- | --- |
| SGLang source | `d574752ef39eb3ef73f87c40dca95d76222f9483` |
| Evidence/workflow commit | `88e1a6952b3e2e4b47160009f7db4d9b20683bc4` |
| Interpreter | Python 3.12.3 |
| Torch | `2.13.0+cpu` |
| Torch binary git version | `cf30153c4c131c8164ee7798e5022d810682e2cb` |
| torchvision | `0.28.0+cpu` |
| Triton | `3.8.0` |
| Transformers | `5.12.1` |
| Platform class | `SRTPlatform` |
| CUDA / HIP build | None / None |
| Official kernel stub helper used | No |

Installation used SGLang's documented alternate-platform `pyproject_other.toml` entry point with `srt_empty,runtime_common`, explicit CPU Torch/torchvision selection, and real Triton. This is a bounded derivative of supported package paths; it does not reproduce the full upstream hosted CI dependency set or the Xeon inference-engine build. Rust extension building was disabled through the supported `SGLANG_BUILD_RUST_EXTS=none` option. The original active pyproject was restored before imports/tests, and the recorded `git status --short` output was empty. [Captured workflow](workflow.yml), [pre-execution environment design](ENVIRONMENT-DESIGN.md), [package list](receipts/attempt1/packages.txt)

The probe verifies six exact source files: the full test module, decode queue, common connection layer, Mooncake connection layer, NIXL connection layer, and `test_utils.py`. Their on-disk bytes match `git show` at the frozen head, and their actual imported locations point into that checkout. The real `CustomTestCase` is used with `SGLANG_TEST_MAX_RETRY=0`. [Probe code](env_probe.py), [loaded-file hashes](receipts/attempt1/import.json), [broader source-review manifest](source-manifest.json)

No model weights were loaded, GPU inference executed, or live RDMA transfer exercised. The unchanged upstream fixtures construct bare components and mock their documented external boundaries. The proposed composed interaction has no execution result in this report.

## Execution and artifact record

There was **one** CPU workflow run for this bounded verification, with GitHub `run_attempt=1`. Installation, source/import checks, and the unchanged suite all succeeded. No retry was needed.

The raw stderr includes an expected `RuntimeError: boom` emitted inside the existing failure-isolation test, followed by that test's `ok` result and the suite's final `OK`. It also contains warnings that AWQ/GGUF quantization requires other hardware. Those messages did not cause test errors or skips.

The ten extracted receipt files are preserved in [receipts/attempt1](receipts/attempt1/). Artifact ID: `10988050151`; downloaded ZIP size: 10,676 bytes; SHA-256: `d771dcef1f9c7e1f50219ad6741af488e9821089a50ea1014be5edfa1e9b45f8`. The ZIP digest and member CRCs were verified before extraction. The original artifact expires on 2026-10-28; these committed text receipts remain inspectable afterward. [File integrity manifest](file-manifest.json)

## Attribution

The upstream deferred-release design, implementation, and 24 tests are credited to their original contributors. This contribution is the bounded independent execution record and an explicitly unexecuted source-review question. It claims no upstream adoption, approval, or merge. The upstream license is retained as [LICENSE.sglang](LICENSE.sglang).

AI assistance was used for source analysis, environment preparation, and reporting.

Zero × Youngseok Oh
