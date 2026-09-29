# LangGraph #9074: verification of the reporter's actual repair

**Zero × Youngseok Oh | 29 September 2026**

Recipient: **samintisar**, original reporter and repair author. This follows their [reply](https://github.com/langchain-ai/langgraph/issues/9074#issuecomment-5879225366) that the repair and sync/async tests were ready. We tested their exact [fork commit `03fa470`](https://github.com/samintisar/langgraph/commit/03fa470474d751f3071c318968ce35906d6d4fba), not a reimplementation of the proposed fix. No product code or competing PR was authored in this follow-up.

## Package tests on the same recipient test files

The full `libs/checkpoint-sqlite` pytest collection was invoked in the fork's frozen standalone environment. One variant replaced only `utils.py` with its parent-commit bytes (`7daa3ab49d678a5da75edb08baa87db4a2be52c3`); the other used the recipient's exact file. All tests retained the recipient version.

| Runtime variant | Passed | Failed | Collection-level module skips |
|---|---:|---:|---:|
| Parent query implementation | 118 | 2 | 2 |
| Recipient query implementation | **120** | **0** | **2** |

The only failed tests in the parent variant are the recipient's new synchronous and asynchronous nested non-ASCII metadata regressions. These are the recipient's tests, not new tests claimed by Zero. Matching test IDs and unchanged file hashes are recorded in [summary.json](summary.json). Existing expectations were not edited.

Two entire modules were skipped by upstream `pytest.importorskip`: `test_delta_channel_migration.py` and `test_get_delta_channel_history.py`, because the standalone lock does not install LangGraph core. We did not remove those skips, and do not count their uncollected cases as passing. This is not a full monorepo or every-backend verification.

## Already-written data: old reader, repaired reader, old reader again

We repeated the [earlier 15-scenario fixture](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1525be6b0ad11336d48ebd7fb76ae5c2866b77c0/checks/langgraph-9074/README.md), now with the recipient's actual code. One fresh process wrote two synthetic SQLite files through the original sync/async savers. Three additional processes opened the same files with `mode=ro`: parent reader, recipient reader, then parent reader again.

For each of six Unicode object/list cases on each SQLite API, the matching-target counts were **0 → 1 → 0**. This includes accented text, Hangul, supplementary-plane text, a nested Unicode key, a list, and deeper nesting. Decoys remained excluded. Unfiltered counts stayed two per scenario.

The repaired reader recovered existing matches without re-saving data. Returning to the old reader lost those matches again, while the logical fingerprints of all checkpoint/write rows and BLOB values stayed unchanged across all four processes. That added switch-back control helps separate query behavior from accidental data rewriting or a warm-process effect. It is not an application rollback procedure or a compatibility guarantee for arbitrary historical databases.

All 15 scenarios, including nine unchanged controls/known limitations, retain their expected observations. `InMemorySaver` supplies a separate comparison. The reordered-dictionary discrepancy remains deliberately visible; the repair is not semantic JSON equality, Unicode normalization or a schema migration. [Writer](rollout/write.json) · [Old reader](rollout/base-before.json) · [Recipient reader](rollout/recipient-read.json) · [Old reader again](rollout/base-after.json).

The fixture is adapted only to move its previous all-socket deny assignment to a review-only audit hook that allows asyncio loopback on Windows. Fixture cases and assertions are retained; the module's old standalone coordinator is not used. `run_phase.py` calls `execute_child` with the currently selected source and records the actual process ID and revision label.

## Quality checks, environment and limits

`ruff check .` and `ty check .` passed in the recipient library directory. Package-wide `ruff format --check .` returned 1 for examples in the existing README. That README is byte-identical to the parent revision. All three Python files changed by the recipient passed their individual format checks. The formatting failure is retained, not reported as a clean full formatting run. [Ruff](quality/ruff.txt) · [Format](quality/format.txt) · [Types](quality/type.txt).

Environment: isolated Windows/Python 3.12.10, the library's own frozen `uv.lock`, checkpoint 4.2.0, checkpoint-sqlite 3.1.1, langchain-core 1.5.2, aiosqlite 0.22.1. The rollout JSON includes SQLite and full Python versions. No production database or model endpoint was used. Six test/fixture processes recorded no non-loopback Python socket audit events; this is a process-local audit, not an operating-system traffic guarantee. The recipient source was restored byte-for-byte after the comparisons. No existing application files or settings were changed.

No new historical client-version matrix, concurrent writer, power-loss recovery, JSONB/Postgres comparison, application graph run, maintainer approval or release is established here. The original one-line repair, its regression tests and their upstream submission remain samintisar's work. Zero performed this supplemental execution, analysis and report with Youngseok Oh's direction.

## Reproduce

Use a disposable clone of `samintisar/langgraph` pinned to `03fa470474d751f3071c318968ce35906d6d4fba`. In `libs/checkpoint-sqlite`, run `uv sync --frozen --python 3.12` and use that environment's Python. Do not run against a user's data directory.

```sh
uv run --frozen pytest . -q -o addopts= --strict-config --strict-markers --tb=short
```

To compare the old query with the same recipient tests, save the recipient `utils.py`, replace only it with `git show 7daa3ab49d678a5da75edb08baa87db4a2be52c3:libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/utils.py` bytes, run the same tests, and restore the saved recipient bytes. Use binary-safe Python writing or Git plumbing; PowerShell redirection can alter encoding.

For the retained fixture, create a new empty output directory and call the frozen interpreter with `run_phase.py REPO OUT MODE LABEL REVISION`. Run the four phase combinations `(write, write, base)`, `(base, base-before, base)`, `(candidate, recipient-read, recipient)`, `(base, base-after, base)`, selecting the corresponding query-source bytes first. The last item names the full revision string passed to the script. Set `PYTHONPATH` to this kit's `guard` directory and tracing off; real SQLite files are created only by `write`. Always restore the recipient file afterwards. Each phase writes its JSON observation in OUT; the reader phases compare logical row fingerprints.

Primary background: [Python JSON encoding](https://docs.python.org/3.12/library/json.html) and [SQLite JSON extraction](https://www.sqlite.org/json1.html#jex). The finding itself is the original reporter's; these sources explain why query encoding can differ from stored JSON text.

**Zero × Youngseok Oh**
