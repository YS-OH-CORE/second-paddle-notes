# LangGraph #9072: portable pytest regressions and an upstream compatibility correction

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

**The revised experimental candidate passes all 44 tests in the unchanged upstream `tests/test_tool_node.py` file and all 24 tests in the new standalone parent-handoff regression file.** This is two specified test files, not the full repository or prebuilt-library suite.

The first comparison exposed a compatibility gap in our previous candidate. We preserved that failing result and corrected the implementation without changing either set of test expectations.

## Use the test-only deliverable

Apply [validated/regression_tests.patch](validated/regression_tests.patch) at upstream commit `7daa3ab49d678a5da75edb08baa87db4a2be52c3`. It adds one standalone pytest file, `libs/prebuilt/tests/test_parent_command_handoff.py`; it does not change runtime code and does not depend on any of our prior probe scripts.

```bash
git apply regression_tests.patch
cd libs/prebuilt
python -m pytest tests/test_parent_command_handoff.py -q
```

Use the project's test environment. The buggy base is expected to fail 22 cases; the two string-route controls pass. For the experimental comparison, [validated/compatibility_runtime.patch](validated/compatibility_runtime.patch) contains the runtime changes tested here. It is not a production-complete or approved patch. [run_pack.py](run_pack.py) creates an isolated checkout/environment and performs the full comparison. See [PROTOCOL.md](PROTOCOL.md) for the original plan and the declared follow-up after the first result.

## Observed results on the same test collections

The final [run 36137199855](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36137199855) executed three implementations in fresh pytest processes, with original repository conftest and `LANGGRAPH_TEST_FAST=true` (the existing memory-backed mode).

| Implementation | Original ToolNode tests | New parent-handoff regressions |
|---|---:|---:|
| Unchanged upstream | 44 passed / 44 | 2 passed, 22 failed / 24 |
| Exact previous normalized candidate | 43 passed, 1 failed / 44 | 24 passed / 24 |
| Compatibility-preserving candidate | **44 passed / 44** | **24 passed / 24** |

There were no skipped tests or collection/setup errors in those six processes. The final run accounts for **204 pytest outcomes**, including intentional failures in the base and earlier candidate. It does not mean 204 distinct regression scenarios or 204 passing tests. The revised candidate contributes 68 passing outcomes. The 24 new cases include two tests that pass only when an unreduced conflicting update correctly raises `InvalidUpdateError`.

[First run 36136696015](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36136696015) had already compared base and the earlier candidate, producing 136 outcomes and exposing the same original-test failure. Both the original and new test-file bytes, and the resolved dependency environment, were identical between the two runs. Neither assertion set was relaxed to fix the failure.

## What the existing test caught

[`test_tool_node_parent_command_with_send`](https://github.com/langchain-ai/langgraph/blob/7daa3ab49d678a5da75edb08baa87db4a2be52c3/libs/prebuilt/tests/test_tool_node.py#L1197-L1281) sends two parent commands that do not set `update`. Our prior normalization joined two empty sequences into `update=[]`; the expected original command retains `update=None`. These commands compare unequal even though their printed representations are identical.

A separate real-combiner diagnostic recorded:

| Implementation | Actual update | Same printed representation as expected? | Equal to expected Command? |
|---|---|---|---|
| Upstream | `None` | Yes | Yes |
| Prior candidate | `[]` | Yes | No |
| Revised candidate | `None` | Yes | Yes |

This is an object-compatibility distinction caught by the existing test, not evidence of lost worker destinations in that particular no-update control.

The correction uses `is None`, not truthiness: if the incoming update is absent, preserve the accumulated update; if only the accumulated one is absent, adopt the incoming value unchanged. Only combine ordered keyed writes when both updates are present. The first parent command and combined Sends are still preserved. The earlier numeric-addition, longest-batch, message-ID, worker and mixed-representation assertions continue to pass.

## Scope and provenance

Upstream pin: `7daa3ab49d678a5da75edb08baa87db4a2be52c3`.
Original ToolNode Git blob: `95e161b9078e3123afa1854247a5dfd132410a53`.
Original test module Git blob: `47ebdcae0d936167649c0d33103650388d290a9a`.
Earlier candidate SHA-256: `be4a47872cfd4764a3fcc3ae0e093295706a87f3b5d9960ab6dd6ebb8645ab8c`.
Revised candidate SHA-256: `9051ab2c778e2f511257b13b7ed66d05e90dda07c5e7e69daaa34d1b88f14bfd`.
Tested standalone file SHA-256: `72b32cafacefd2d2cb57ebf74df2151ee3f7983b090c824ae17212d473508ecc`.

Runtime/checkpoint/SDK libraries were installed from the pinned checkout. The pytest guard checked their actual source import paths and candidate hash in every test process. Python socket connections/DNS were blocked during tests, with zero recorded attempts. Tracing was disabled; no hosted model or real-user-memory service was used. The original tests retain their own mocks; the new regression file uses real tools and compiled parent/child StateGraphs with deterministic values. Python 3.12.3, pytest 8.4.2, langchain-core 1.6.5, Pydantic 2.13.5. The full dependency list is retained in the artifacts.

Only the new file was import-sorted/formatted; its non-import AST was checked unchanged, and its configured Ruff lint check passed. The original upstream test file was hash-checked unchanged after each execution. Locally applying both distributed patches to the retained original source reproduced the exact tested source and test-file bytes. [AUDIT.json](AUDIT.json) records the readback checks. This audit reanalyzes the actual Actions runs; it is not independent external replication.

Unresolved scope: arbitrary root updates, mixed parent destinations, multiple non-None resume values, other Python versions, full repository testing and checkpoint replay. No assertion of a complete fix, maintainer endorsement, merge or downstream adoption follows from these results.

Final artifact: [10864787400](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36137199855/artifacts/10864787400), 134,204 bytes, SHA-256 `27f17ec57257e4784b0cfd7d49ce267a402021c382907113ec46ff623c5dedb4`.
First artifact: [10865441597](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36136696015/artifacts/10865441597), 106,587 bytes, SHA-256 `6e31b214a7b25bf7893252c81bf0b0783ed83ef95d268e271caf7a472e70779b`.
Actions artifacts retain all JUnit, failure tracebacks, per-process logs, guard records, sources and environment for 30 days. The test patches and audit are also committed here.

Credit: original issue by elizandropacheco; reducer-preservation discussion by 84dnnvbdvp-debug, breken-ai and impartshadow; existing tests by LangGraph contributors. This work corrects Zero's own experimental candidate and packages supplemental tests. Zero is an AI collaboration partner working with Youngseok Oh.
