# CanIToolCall #25 design: pre-submission verification

Zero × Youngseok Oh | 29 September 2026

This is the same two-file design at `YS-OH-CORE/canitoolcall@b5795bcbbecab56d3b7b9ea61de36232ede046a0`, based on `redd34/canitoolcall@bdade62a9513ccd8657b5e153a9f7ff2421c832d`. No design, runtime code, fixture, snapshot, expected answer or workflow was rewritten for this verification. The design was already complete; this follow-through checks its submission evidence.

## Observed checks

Fresh temporary Windows environment, Python 3.12.10, original `uv.lock`, `uv sync --frozen`. Ruff lint, Ruff format, mypy and fixture validation succeeded. Fixture validation: 45 files, 0 issues.

The repository pytest invocation did **not** pass on this host: **466 passed, 6 failed, 367 skipped**, 839 collected and no errors. The six failures are four direct execution of POSIX-style test harness scripts (`WinError 193`), a POSIX file-mode assertion, and a colon-based environment-path assertion. These descriptions come from the recorded failures, not proposed production fixes.

A separate exact upstream checkout, a new baseline environment and the same original test suite reproduced **the same 839 outcomes**, including all six failures. All 208 existing repository files are byte-identical between that baseline and the design branch; the head adds only the two documentation files. No tests were excluded, patched, marked xfail, or relaxed. Both pytest processes exit 1. The 367 engine-dependent skips are not passes; no engine environment was installed.

[Check commands and counts](checks.json) · [Baseline comparison and all six case IDs](baseline-comparison.json) · [Full captured stdout/stderr](execution.log).

These checks say the documentation-only change did not change observed test outcomes on this machine. They do not validate the proposed development-engine builds, projected budgets, cache isolation implementation or full hosted CI. Existing release CI timestamps were rechecked arithmetically, not rerun as benchmarks. The design's two document Git blobs match the already-published originals.

The public external references were rechecked against the current official [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) and [vLLM revision-install](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/) documentation. Their statements are not guarantees that arbitrary engine commits build inside the proposed caps.

Only a new temporary checkout, environments and synthetic test output were created on the owner's authorized computer. Runtime child environments omit provider credentials. Public logs replace temporary root/home paths with `[WORKDIR]`/`[HOME]`; no raw credential or notification-email content is included. No new production or scheduled workflow was enabled. The repository's existing PR CI, if triggered by submission, is a separate result.

Analysis and local verification by Zero, with Youngseok Oh's project direction. Tests and existing source remain CanIToolCall contributors' work. The collector shell's successful completion is not substituted for the recorded pytest failures.

Zero × Youngseok Oh
