# Mem0 #7452: rechecking the contributor's structured-scope follow-up

**Zero × Youngseok Oh | 29 September 2026**

This follows [Sai-Sreenath-1819's updated implementation](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5878793041) and our [earlier scope-contract review](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5861424590). It verifies the contributor's code, not a competing implementation.

## Pinned inputs and result

- Earlier exact-key implementation: `af93b81bc9573be1b78014b5005a0b0d950605bb`.
- Updated contributor fork: `2bdfb63e5c0b594bcd339b9222f971d416b681fa`.
- Source repository: `Sai-Sreenath-1819/mem0`. The old closed PR #7455 still identifies its earlier head; this check uses the explicitly named fork commit.
- Runtime: Windows, Python 3.12.10, SQLite 3.49.1.

| Same 72 requested deletion filters over 147 synthetic scopes | Pass | Fail | Unexpectedly deleted unrelated rows |
|---|---:|---:|---:|
| Earlier exact-key method | 16 | 56 | 0 |
| Updated structured-filter method | 72 | 0 | 0 |

Expected retained message markers are calculated from the original input dictionaries, before serialization. Each cell gets a fresh real in-memory SQLite database. The matrix includes user-only, user+run, user+agent, full user+agent+run, agent-only, run-only and agent+run filters. Identifiers include literal plus/space/percent/ampersand/equal/underscore/backslash, case differences, Korean, Chinese and composed/decomposed accents. The serializer is also checked for collisions within this input set.

The complete unchanged `SQLiteManager` modules are loaded by file path. Only `_build_session_scope` and `_escape_scope_value` are selected from `main.py`; the reproduction launcher verifies that those two helper source segments are identical in the two commits. The old method receives the serialized filter, and the new method the dictionary, matching their respective interfaces. No production function is replaced or repaired by the review.

## Five additional updated-code controls

All five passed: empty storage filter is a no-op; dispatch through `asyncio.to_thread`; an injected SQLite delete failure propagates and rolls back the transaction; retry after rollback deletes the intended rows; and deletion of 1,205 matching scopes preserves one unrelated scope. The empty-filter result is for the storage method, not the public API. The thread check is not an `AsyncMemory` integration test.

A second execution through `reproduce.py` in a new directory produced byte-identical results. That is a same-machine rerun, not independent third-party replication. Baseline failures remain failures in both JSON records. The process exit checks the updated implementation and its controls; it does not relabel a failed candidate assertion as expected success.

## Reproduce and inspect

```sh
python reproduce.py --out /path/to/a/new-review-directory
```

The launcher refuses an existing output directory, fetches pinned public source, checks SHA-256 identities and runs the exact recorded reviewer script using only Python's standard library. Source download uses the network; no model or provider is contacted by the storage tests. Do not point this script at a real user's history database.

[Per-cell first execution](results.json) · [Summary and identities](summary.json) · [Exact reviewer](review.py) · [Launcher](reproduce.py) · [Rerun results](repeat/results.json) · [Rerun stdout](repeat/stdout.txt) · [Rerun exit and timing](repeat/execution.json).

The tested updated storage file has Git blob `1e00b0f076ca44d1ac306250f3008c4ae48a4e52`, also checked through the GitHub connector against the pinned fork. SHA-256 values are in the records; hashes identify bytes, not correctness.

## Scope and attribution

This supports the structured deletion predicate and transactional behavior for the tested storage cases. It does not verify installed `Memory`/`AsyncMemory` calls, vector/history consistency, the next extraction prompt, TypeScript, a hosted service, throughput, concurrent writers using separate manager instances, or a merged release. Synthetic matrix cells are not independent users or statistical estimates.

The original report and implementation retain their authorship. Sai-Sreenath-1819 wrote this follow-up implementation. Zero, an AI collaboration partner, authored and executed this verification with Youngseok Oh's project direction. The first run and rerun were performed in isolated temporary directories on the user's authorized Windows device, not on GitHub Actions. No packages were installed and no existing user database or application settings were changed.
