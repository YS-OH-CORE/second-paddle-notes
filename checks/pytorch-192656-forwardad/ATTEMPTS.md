# All execution attempts

These two runs belong to the same bounded two-file source-overlay experiment. Both used the exact parent and candidate Python sources in fresh subprocesses over one disposable CPU wheel. They were not full source builds of either PyTorch commit. Downloaded ZIPs passed CRC validation and matched the recorded SHA-256 values before extraction.

## Attempt 1: missing XML test-runner dependency

- [Run 36452573996](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36452573996)
- Workflow commit: `db32a8fe695d64b4d774e70dee3272476f521905`
- Source imports, exact source-file hashes, and binary provenance were recorded successfully. Test startup then failed because `xmlrunner` was unavailable.
- **Zero tests executed.** The strict comparison gate rejected the empty test-status lists. This run did not confirm the numerical hypothesis.
- Original wheel Python files were restored.
- All 16 extracted files: [attempt1](receipts/attempt1/), including the startup error logs and summary.
- Downloaded artifact: ID `10984043369`, 8,173 bytes, SHA-256 `8a096ce7578c1b6880d2d1887b6179e74d86a0659db0339ea14284e3aa7a1d13`.

## Attempt 2: completed comparison

- [Run 36453154812](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36453154812)
- Workflow commit: `32ec7835739c728cca5d6a48c959da61aaab7832`
- Added `unittest-xml-reporting==3.2.0`. Before this run, the status recorder was also made compatible with XML runner result objects by matching test IDs. The numerical test logic and strict expected-result gate were preserved.
- Candidate: **3 passed, 1 assertion failure, 0 errors, 0 skipped**, exit 1, no timeout. Read-only and clone-mutation parity controls passed. Mutating an intermediate dual's tangent produced `[48., 54.]` eagerly and `[18., 24.]` under internal `dispatch_functionalize`.
- Parent: **1 passed, 3 errors**, exit 1, no timeout. The three errors came from the reproduction's explicit guard for a missing tangent, not an exception raised directly by the library. This does not establish a regression from a numerically correct parent.
- Both variants used Python `3.12.3`, `torch==2.13.0+cpu`, and binary git version `cf30153c4c131c8164ee7798e5022d810682e2cb`. Source hashes matched the frozen upstream files. The original wheel Python files were restored byte-for-byte.
- A successful workflow means the specified discrepancy, controls, provenance, and restoration checks matched. Individual test subprocesses intentionally exit 1 for the expected failure/error patterns.
- All 16 extracted files: [attempt2](receipts/attempt2/), including raw stdout/stderr, structured observations, test statuses, package list, process exits, and summary.
- Downloaded artifact: ID `10984196257`, 13,427 bytes, SHA-256 `a5dbabaa01d3ad1a72d0c62021f3b18d0c5415d08933a98bc0df679804097642`.

## Artifact limitation

JUnit XML was generated below hidden `.home...` output directories. The upload action's default `include-hidden-files: false` excluded those directories. **No XML files were retained in either downloaded artifact.** The complete raw stdout/stderr and structured per-test statuses were retained and agree with the summary; the result does not rely on an unavailable XML file. No additional run was performed solely to recover XML.

## Retention, attribution, and handoff

The original Actions artifacts have a 30-day retention setting. The extracted text receipts are committed here to keep the evidence inspectable after that expiration. `file-manifest.json` records byte counts and SHA-256 hashes for all files in this report directory except the manifest itself. `source-manifest.json` separately records the exact upstream source hashes; the runner checks out those source files from the original repository.

PyTorch's [AGENTS.md](https://github.com/pytorch/pytorch/blob/97b6a194e98d7965467541490d74ee44c862a563/AGENTS.md) and [AI_POLICY.md](https://github.com/pytorch/pytorch/blob/97b6a194e98d7965467541490d74ee44c862a563/AI_POLICY.md) require actual human review and human commentary for upstream issue/PR interaction. The quoted, AI-disclosed [comment draft](upstream-comment-draft.md) has not been posted. It does not attest that Youngseok Oh has reviewed or approved its exact content.

AI assistance was used in this verification work. The original PR design and implementation remain HussainNizamani's work. PyTorch's license is retained in `LICENSE.pytorch`.

Zero × Youngseok Oh
