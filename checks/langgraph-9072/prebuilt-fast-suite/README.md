# LangGraph #9072: complete prebuilt fast-suite compatibility check

**Zero × Youngseok Oh | 29 September 2026**

The previously published [mixed-route candidate](https://github.com/YS-OH-CORE/second-paddle-notes/tree/e0040ad37e20ae6edf15fc1b4fa3a45658202a2c/checks/langgraph-9072/mixed-route-checkpoint) was not changed. This follow-up expands the compatibility check from three selected files to the entire `libs/prebuilt` pytest collection in the project's existing fast mode.

## Observed comparison

At upstream `07b33185eab893be2ed031eedae52f09314bf77c`, both variants collected the same **300 cases across 12 test modules**. This includes 228 existing project cases and the 72 previously authored handoff/restart cases. No new regression scenario is claimed in this report.

| Variant | Existing project cases | Our existing handoff/restart cases | Overall |
|---|---:|---:|---:|
| Unmodified upstream | 228 passed | 2 passed / 70 failed | 230 passed / 70 failed |
| Same mixed-route candidate | 228 passed | 72 passed | **300 passed** |

No skip, collection error, changed test expectation or lost test ID occurred. The two runs each passed 16 saved snapshot expectations and emitted 135 warnings; the warnings remain in stdout. The comparison has 600 recorded outcomes, not 600 unique scenarios. The original tests, fixtures and saved snapshots were also byte-matched to the pinned upstream Git tree. [Identity audit](IDENTITY.json) · [Machine-readable summary](summary.json).

Coverage now includes the package's existing ReAct agent tests, graph tests, tool interception, validation/error filtering, injected state, streaming tool-call transformation and deprecation behavior, not only ToolNode's original 44 cases. All 228 original expectations passed before and after the candidate. This supports compatibility within this recorded environment; it does not prove arbitrary downstream behavior.

## Runtime identity and quality checks

Candidate SHA-256: `51972b3a8b160841775ef0830c34254e4bf86b705afc1b32ef372a13d741acbe`, identical to the earlier public candidate. No new product-code patch was introduced in this follow-up.

The following read-only checks passed for both baseline and candidate in `libs/prebuilt`:

```sh
ruff check langgraph
ruff format --check langgraph
ty check langgraph
```

These cover the package's library directory, not repository-wide formatting or type checking. [Quality records](quality/summary.json). The same installed, frozen dependency environment was used; no new dependency was installed. [Environment and actual source imports](environment.json).

## What fast mode includes and leaves out

The pinned Makefile's `test-fast` target sets `LANGGRAPH_TEST_FAST=1` and runs pytest. This review invoked that interpreter's pytest from the library directory with `.` as the collection target, `LANGGRAPH_TEST_FAST=true`, and the original conftest. It retained strict marker/config validation and wrote complete JUnit reports.

The existing upstream conftest selects its in-memory checkpointer/store fixtures in this mode. It does **not** run the Docker/Postgres/Redis-backed `make test` matrix. Our eight earlier explicit SQLite restart tests are still part of the collection and run their real file-backed two-process comparisons regardless of fast mode.

This is the complete **prebuilt fast-mode collection**, not the full LangGraph monorepo, every dependency-backend combination, every Python version, or an acceptance of the unresolved Command grouping contract. It does not resolve tool-returned `resume` conflicts, mixed local/parent updates, pure string-only groups, arbitrary root reducers or crash consistency.

## Reproduce

Use a new checkout pinned to the commit above and the earlier public kit. Apply its `regression_tests.patch` first. At `libs/prebuilt`, create the frozen Python 3.12 environment with `uv sync --frozen --python 3.12`, set `LANGGRAPH_TEST_FAST=true`, and disable tracing. Then run:

```sh
python -m pytest . -q -o addopts= --strict-config --strict-markers --tb=short --junitxml=upstream.xml
```

Here `python` must be that frozen environment's interpreter. The unmodified upstream should exit 1 with 70 failures from our added regressions. Apply the earlier `mixed_parent_runtime.patch` at the repository root using `git -c core.autocrlf=false apply`, and rerun the same collection to a different JUnit file. The candidate should exit 0 in the recorded environment.

Our safety wrapper removed credential-bearing environment variables, redirected home/config paths to newly created temporary directories, and loaded [network_guard.py](network_guard.py) as `sitecustomize.py` through a review-only `PYTHONPATH`. It permits explicit loopback and blocks non-loopback Python socket connection/DNS events before access. The guard self-test confirmed a synthetic non-loopback connection was blocked; both full-suite runs recorded 17 guarded Python processes and zero non-loopback attempts. The self-test attempt is separate from those suite counts. This is not an OS-wide traffic audit, and no real LLM call was configured.

For this review, the library source was switched between the recorded baseline and candidate bytes only in the already isolated checkout, with the candidate restored afterwards. User application files, production data and global Git configuration were not modified.

## Evidence and status

[Upstream outcomes](receipts/upstream-fast/summary.json) · [Candidate outcomes](receipts/candidate-fast/summary.json). Each receipt directory contains complete JUnit, stdout/stderr and process-level network audit events. Identifying home/temporary paths are replaced with `[HOME]`, `[REVIEW_DIR]` and `[PRIOR_REVIEW_DIR]`. No failure or warning was discarded.

Execution was on the same authorized Windows computer and Python environment as the earlier check, so this is an expanded same-environment check, not independent replication. The public candidate and original issue remain discussion-stage work. We do not claim maintainer approval, merge, deployment, or a new thank-you based on this run.

Original issue: **elizandropacheco**. Reducer-preservation discussion: **84dnnvbdvp-debug, breken-ai and impartshadow**. Original code/tests/snapshots belong to the LangGraph contributors. Zero performed this comparison and wrote the report with Youngseok Oh's direction. Existing authorship is preserved.

**Zero × Youngseok Oh**
