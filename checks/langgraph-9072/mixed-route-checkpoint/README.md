# LangGraph #9072: mixed parent routes and a real checkpoint restart

**Zero × Youngseok Oh | 29 September 2026**

A tested follow-through for [issue #9072](https://github.com/langchain-ai/langgraph/issues/9072), originally reported by **elizandropacheco**. It builds on the reducer-preservation discussion and our [earlier portable tests](https://github.com/YS-OH-CORE/second-paddle-notes/blob/f8a1d4776d4181d58f3965d17a8f83e2d4e84e2f/checks/langgraph-9072/pytest-pack/README.md). This is a scoped candidate and reusable test contribution, not a competing upstream PR or an approved general Command merge contract.

## The remaining failure

The previous compatibility-preserving candidate repaired parent groups whose destinations were lists of `Send`. It still failed when a sibling used one `Send`, a tuple of Sends, or a plain node-name destination. The compiled graph reached only one worker and retained only one sibling update. In a list/string example the total was **3 rather than 5**, only `call-beta` survived, and only beta ran.

`graph/state.py::_control_branch` raises `ParentCommand` for the first parent command. Returning multiple intact parent commands from the combiner therefore does not deliver them all. That is source analysis supported by compiled-graph outcomes, not a claim to have originally discovered the reporter's symptom.

The candidate collects sibling parent commands when **any parent route contains a Send**, normalizes destination representation, and preserves ordered duplicate-key writes for the graph's configured reducers. Absent/sole updates are preserved. String-only groups retain existing behavior and original test expectations; they are not claimed repaired here. Mixing local-graph and parent-graph writes is not changed.

## Same final tests, three implementations

Pinned upstream: `07b33185eab893be2ed031eedae52f09314bf77c`.

| Implementation | Unchanged upstream ToolNode tests | Prior handoff tests | New route/root/restart tests |
|---|---:|---:|---:|
| Unmodified upstream | 44 passed | 2 passed / 22 failed | 0 passed / 48 failed |
| Previous compatibility candidate | 44 passed | 24 passed | 14 passed / 34 failed |
| Mixed-route candidate | **44 passed** | **24 passed** | **48 passed** |

The final candidate passes **116 test cases in three files**, with no skips or collection errors. The comparison's 348 outcomes are not 348 independent scenarios or passing tests. Baseline/prior failures are retained with pytest exit 1; the candidate exits 0. [Summary, identities and scope](summary.json).

The 48 new cases comprise 36 keyed-state route/order/API combinations, four numeric-root cases and eight SQLite restart cases. Numeric-root and uniform-list controls already pass with the prior candidate. Its 34 remaining failures involve mixed destinations, including six restart cases. Custom longest-batch reduction, additive totals, both ToolMessage IDs and all intended workers are checked separately. No new dictionary/list merge rule replaces the application's reducers.

## Real persistence and a second process

Each restart case launches **two separate Python processes** against one new file-backed SQLite database. The first runs the actual parent/child graphs, reaches an approval interrupt, saves the checkpoint and exits normally. The second opens the database, builds a new graph, and resumes with `Command(resume="approved")`. Both sync `SqliteSaver` and async `AsyncSqliteSaver` are exercised.

Before and after restart the candidate retains total 5, longest batch `[b,c]`, both tool-result IDs and both workers. Approval is recorded once. A synthetic append-only journal contains exactly one alpha and one beta tool entry across the two processes. The prior candidate persists its already-missing sibling; reopening a checkpoint does not recover that information. The final summaries retain all 16 phase observations per implementation.

This is an **orderly stop after a persisted interrupt**, not a process kill during a write, power-loss test, concurrent-writer test or general exactly-once guarantee. It exercises public resume input, not multiple `resume` values returned by tools. No model is configured; the new tests use real graph/tool/checkpointer code with deterministic synthetic values, not mocked graph components.

## Reproduce in a disposable checkout

Requires Python 3.12, Git and uv. Source/dependency download uses the network; no credentials or model endpoint are needed. Use a new checkout, not a production environment.

```sh
git clone -c core.autocrlf=false https://github.com/langchain-ai/langgraph.git langgraph-9072-review
cd langgraph-9072-review
git checkout 07b33185eab893be2ed031eedae52f09314bf77c
# EVIDENCE is the absolute path to this directory in second-paddle-notes.
git -c core.autocrlf=false apply "$EVIDENCE/regression_tests.patch"
cd libs/prebuilt
uv sync --frozen --python 3.12
export LANGGRAPH_TEST_FAST=true LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false
uv run --frozen pytest tests/test_tool_node.py tests/test_parent_command_handoff.py tests/test_parent_handoff_durability.py -q -o addopts=
# For a candidate: apply ONE runtime patch from the repository root,
# then repeat the same test command. Both patches are relative to upstream.
```

The runtime patches are alternatives, not cumulative. Upstream should fail. Recorded tests used `LANGGRAPH_TEST_FAST=true`, tracing disabled, original repository conftest and a frozen uv environment. `LANGGRAPH_TEST_FAST` selects the existing in-memory fixtures; the eight authored restart cases separately use real SQLite files.

[Runtime candidate](mixed_parent_runtime.patch) · [Test-only patch](regression_tests.patch) · [New tests](test_parent_handoff_durability.py) · [Retained prior tests](test_parent_command_handoff.py) · [Previous runtime](previous_runtime.patch) · [Environment and verified source imports](environment.json).

Both packaged patches were applied to a separate source copy and reproduced the tested source/test bytes. An initial packaging check inherited Windows Git CRLF conversion and produced identical text but different bytes. Using per-command `core.autocrlf=false` fixed that packaging check; no global Git setting changed. The failure and correction are retained in [the packaging audit](PACKAGING_AUDIT.json).

## Evidence and boundaries

[Final upstream](receipts/final-baseline/summary.json) · [Final prior](receipts/final-prior/summary.json) · [Final candidate](receipts/final-candidate/summary.json). Each directory contains complete JUnit and stdout/stderr. Initial runs remain under `receipts/baseline`, `receipts/prior` and `receipts/candidate`.

Final comparison: byte-identical test files, original conftest, one frozen environment. Formatting/import sorting of the new file happened before that final comparison and did not alter its non-import syntax tree; no assertion was weakened. Configured Ruff checks on the changed runtime and new test pass. The initial import-order lint failure remains recorded. The full upstream lint/type/test suite was not run.

All tests were run on the owner's authorized Windows device in an isolated temporary environment. These are same-machine repeats, not third-party replication. Receipt sanitization replaces working/home paths with `[WORKDIR]` and `[HOME]`; results, error messages and synthetic observations remain. SQLite database binaries and unrelated files are not published. No existing application settings or user database was changed.

Still open: string-only multi-parent groups, non-None tool-returned resume conflicts, arbitrary root reducers/values, mixed local/parent destinations, concurrent checkpoint writers, other platforms/Python versions and the full upstream suite. The candidate's first-command resume handling is unchanged and is not a validated conflict policy. Maintainers and existing contributors must decide the grouping contract before integration. No adoption, merge or release is claimed.

Original report: **elizandropacheco**. Earlier reducer-preservation discussion: **84dnnvbdvp-debug, breken-ai and impartshadow**. LangGraph contributors authored the framework and original tests. Zero authored these new tests, analysis, candidate and execution with Youngseok Oh's direction. Other contributors retain their work and licensing.

**Zero × Youngseok Oh**
