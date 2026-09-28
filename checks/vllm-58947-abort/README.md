# vLLM #58947: abort cleanup after real remote-load admission

## Result

At PR Python head [`365706a27300453ba9218c1585a64a1f44b54254`](https://github.com/vllm-project/vllm/commit/365706a27300453ba9218c1585a64a1f44b54254), the complete remote-prefill lifecycle test file passed **13 tests: 11 existing cases and two added abort cases**, with zero errors or skips. A deliberate negative control that removed one deferred-cleanup statement failed both new cases on the public waiting statistics. Production source was then restored.

This supports the existing abort cleanup in [njhill's scheduler PR #58947](https://github.com/vllm-project/vllm/pull/58947). The negative control is an intentionally altered implementation, not a discovered failure of that PR. We contribute a regression test and verification evidence; this record does not claim an upstream adoption or merge.

[Successful CI run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36453327818) · [Exact test patch](receipts/attempt4/test.patch) · [Result summary](receipts/attempt4/SUMMARY.json)

| Implementation exercised | Test scope | Passed | Failed | Errors / skipped |
| --- | --- | ---: | ---: | ---: |
| Frozen PR source plus test addition | Entire remote-prefill lifecycle file | 13 | 0 | 0 / 0 |
| Same source with one abort-cleanup statement removed | Two new abort cases | 0 | 2 | 0 / 0 |

The first subprocess exited 0; the control exited 1. Neither timed out. The workflow succeeds only when the intended positive/control comparison is observed. Full evidence is retained in the [candidate log](receipts/attempt4/candidate.log), [candidate JUnit](receipts/attempt4/candidate.xml), [control log](receipts/attempt4/removed_deferred_cleanup.log), and [control JUnit](receipts/attempt4/removed_deferred_cleanup.xml).

## Review question and coverage gap

[robertgshaw2-redhat asked whether abort clears the new deferred state and needs coverage](https://github.com/vllm-project/vllm/pull/58947#discussion_r4123349049). [njhill pointed to the existing cleanup](https://github.com/vllm-project/vllm/pull/58947#discussion_r4123733262).

The existing core tests `test_abort_request_waiting_for_remote_kvs` and `test_abort_request_finished_recving` set a request's status after `add_request()`. They verify request retention/removal but do not run remote-load admission, allocate its KV blocks, or populate both new waiting structures through scheduling. See the [frozen existing core tests](https://github.com/vllm-project/vllm/blob/365706a27300453ba9218c1585a64a1f44b54254/tests/v1/core/test_scheduler.py).

The addition extends the [existing remote-prefill lifecycle file](https://github.com/vllm-project/vllm/blob/365706a27300453ba9218c1585a64a1f44b54254/tests/v1/kv_connector/unit/test_remote_prefill_lifecycle.py), reusing its fixtures. It exercises actual admission, block ownership, abort statistics, receive completion, reclamation, and subsequent progress.

## What the two cases exercise

The pool has six blocks, including the reserved null block: **five usable blocks**. A remote-prefill request acquires three blocks through the real scheduler and Nixl scheduler. A local request needs four blocks and cannot fit while that load holds its allocation. No request status or queue membership is manually assigned.

The two parameter values of `test_aborted_remote_load_releases_capacity_after_receive` cover:

- **Abort before receive completion.** The request leaves scheduling accounting, but its three blocks remain owned while the simulated transfer is outstanding. The local request still cannot run. A later `finished_recving` signal releases those blocks.
- **Abort after receive completion, before promotion.** The completion signal has been processed, but the request has not resumed execution. Abort immediately releases its allocation.

Both cases assert the public waiting counts, verify that the local request subsequently reuses freed block IDs, feed its simulated EOS result through `update_from_output()`, and finish with the existing `assert_scheduler_empty()` checks. The normal, non-abort lifecycle cases run in the same file.

The completion signals and model-runner outputs are synthetic, as in the upstream unit fixtures. The Scheduler, KV cache manager, block pool, and Nixl scheduler are real implementations. No worker performs a device transfer or model inference.

### Ownership matters

For this D-side path, the connector's `request_finished()` hook does not itself request delayed release. The Scheduler retains blocks when an aborted request is still awaiting `finished_recving`; its completion handler later frees them. An already-received request can release immediately. The test preserves that distinction and does not replace the connector hook.

## Negative control and restoration

In a temporary checkout, [the runner](run.py) removes exactly this statement from `Scheduler.finish_requests()`:

```python
self.deferred_waiting.difference_update(waiting_requests_to_remove)
```

Both new cases then fail on:

```text
(stats.num_waiting_reqs, stats.num_skipped_waiting_reqs)
actual: (0, 1)
expected: (1, 0)
```

This demonstrates sensitivity to the reviewer's cleanup concern through reported scheduler behavior. The control stops at that assertion; it does not establish a downstream deadlock or failed KV reclamation in the altered implementation.

A `finally` block restores the original scheduler bytes. Its final SHA-256 matches the initial hash, and the recorded production diff is empty. [Initial inputs and hashes](receipts/attempt4/inputs.json) · [Restoration receipt](receipts/attempt4/SUMMARY.json)

## Frozen source and CPU binary provenance

This was a CPU Python-development installation using precompiled binaries, not a full source build.

| Component | Exact provenance |
| --- | --- |
| Python source | PR head `365706a27300453ba9218c1585a64a1f44b54254` |
| Source tree | `eac71de736907afd5010f7fd6487de6d343b5016` |
| CPU binaries | Official vLLM `0.30.0+cpu` release wheel |
| Binary source commit | `ced6857afa0ea7b2e3f0846a62e1394e90f15607` |
| Final workflow commit | `491a2d4cb6a5b94b6f9a0678e90a4a9ed98b7f96` |
| Runtime | Python 3.12.3, Torch 2.13.0+cpu, Ubuntu runner with glibc 2.39 |
| Explicit codec dependency | `torchcodec==0.14.0+cpu` from the PyTorch CPU index |

The [wheel inspector](fetch_official_cpu_wheel.py) checks the fixed official asset's size, publisher SHA-256, platform compatibility, metadata, and applicable Torch requirement. Its [manifest](receipts/attempt4/wheel/manifest.json) distinguishes the release binary commit from the PR Python commit. The asset's filename uses a manylinux platform tag while its internal WHEEL file retains a generic Linux tag; that platform-only difference is preserved in [tags.json](receipts/attempt4/wheel/tags.json).

The runner verifies that the imported scheduler comes from the frozen checkout and that Torch has no CUDA build. The upstream root and unit conftests remain unchanged, including the existing CPU block-size fixture. [Installed packages](receipts/attempt4/packages.txt) · [Installation log](receipts/attempt4/install.log)

## All four execution attempts

These are separate workflow runs, not four successful replications. The first three reached no test result.

| Attempt | Run | Outcome and retained evidence |
| --- | --- | --- |
| 1 | [36451518079](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36451518079) | Automatic CPU-wheel metadata lookup returned HTTP 404. Our initial install pipeline lacked `pipefail`, so execution continued and ultimately lacked Torch. Zero tests. [Receipts](receipts/attempt1/) |
| 2 | [36452491157](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36452491157) | The official release asset matched its digest and size, but our strict filename/WHEEL tag equality check rejected its platform-only retag. Zero tests. No artifact was uploaded because inspection metadata was outside the upload path. [Preserved excerpt](receipts/attempt2/tag-check-excerpt.log) |
| 3 | [36452985480](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36452985480) | Installation succeeded; importing the scheduler failed through a GPU TorchCodec dependency requiring `libnvrtc.so.13`. Zero tests. [Receipts](receipts/attempt3/) |
| 4 | [36453327818](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36453327818) | Explicit CPU TorchCodec installation resolved that environment issue. Full file: 13 passed. Deliberate control: two expected assertion failures. [Receipts](receipts/attempt4/) |

[ATTEMPTS.md](ATTEMPTS.md) records setup corrections and artifact availability.

## Reproduction and limits

Use a disposable checkout and the [captured workflow](workflow.yml), corresponding to the [executed workflow commit](https://github.com/YS-OH-CORE/second-paddle-notes/blob/491a2d4cb6a5b94b6f9a0678e90a4a9ed98b7f96/.github/workflows/vllm-58947-abort.yml). It follows the [upstream CPU Python-only installation route](https://github.com/vllm-project/vllm/blob/365706a27300453ba9218c1585a64a1f44b54254/docs/getting_started/installation/cpu.md), with the verified release wheel selected explicitly.

[run.py](run.py) appends [test_addition.py](test_addition.py), checks source provenance, executes the full file and targeted control, restores production source, and writes receipts. The test command is:

```bash
.venv/bin/python -m pytest \
  tests/v1/kv_connector/unit/test_remote_prefill_lifecycle.py -v --tb=short
```

This evidence covers scheduler lifecycle behavior in the documented CPU environment. It does not validate NIXL/RDMA transport, GPU execution, model outputs, Rust frontend changes, distributed performance, the whole PR, or every connector. No production repair is proposed here.

## Credit and license

The scheduler design and implementation belong to **njhill**; the abort review question is **robertgshaw2-redhat**'s. The test builds on vLLM's existing fixtures and lifecycle tests. Original vLLM copyright notices are retained; the upstream Apache-2.0 license is included as [LICENSE.vllm](LICENSE.vllm).

**Zero × Youngseok Oh** contributed the focused test and verification record. AI assistance was used for analysis, test development, environment diagnosis, and reporting.


File integrity: [SHA-256 manifest](file-manifest.json).
