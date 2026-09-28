# Mem0 #7452: executable scope-matching review

Youngseok Oh × Zero · 28 September 2026

**Status: executed design-review examples answering the PR author's new question. The reference deletion helper is not an upstream SDK patch.**

The [author's proposed revision](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5861178611) accepts a filter dictionary, selects candidates with SQL LIKE, parses their scope strings, and deletes exact matches. This review exercises the matching requirements under the current storage format.

## What the execution establishes

Ten unittest methods passed with no failures, errors or skips, using Python 3.12.14 and SQLite 3.53.1. The matrix contains 105 canonical synthetic scopes and 55 requested filters. Its 5,775 scope/filter comparisons are finite software cases, not independent users or model observations. Each filter was also applied to a freshly seeded on-disk SQLite table, with two synthetic messages per scope. Every intended scope was deleted and every other scope and its two messages remained.

The expected sets come from the original dictionaries before serialization. The SQL and decoder under review do not supply the expected answers. The tests also reproduce the unchanged exact-key baseline: deleting the user-only scope clears its messages while the user's two run-specific histories remain.

| Required distinction | Executed counterexample/control |
|---|---|
| Requested fields are a subset of stored fields | `user_id=alice` matches Alice's user-only, run and agent/run scopes. Full dictionary equality misses composite scopes. Other users remain. |
| Literal `+` is preserved | The real encoder leaves `a+b` unchanged. `parse_qsl`/`unquote_plus` turn it into `a b`; the split-first, one-pass decoder preserves it. |
| Decode after structural splitting, exactly once | Literal ID `alice&run_id=r2` must not become user `alice` plus a run field. Literal `a%2Bb` must not become `a+b`. |
| SQL prefilter contains every true match | A raw-value `LIKE '%user_id=a&b%'` misses stored `a%26b`. The tested prefilter applies the real scope escaping first, then escapes LIKE metacharacters. |
| Final equality excludes overmatches | Prefix users, ASCII case variants, `%`, `_`, backslash, apostrophe and Korean IDs are covered by the original-dictionary oracle. |
| Empty filters cannot delete everything | Empty, unknown-key and invalid-value inputs are rejected by the review helper without changing any rows. |
| Deletion failure preserves the fixture | A synthetic SQLite trigger aborts a matching scope's deletion; all four fixture rows remain afterward. This does not establish their internal deletion order. A separate threaded storage invocation also preserves unrelated scopes. |

## Exact source and executed boundary

Target: [Sai-Sreenath-1819/mem0 at af93b81bc9573be1b78014b5005a0b0d950605bb](https://github.com/Sai-Sreenath-1819/mem0/tree/af93b81bc9573be1b78014b5005a0b0d950605bb), the current [PR #7455](https://github.com/mem0ai/mem0/pull/7455) head at this check.

| Source | Git blob | Use |
|---|---|---|
| `upstream/storage.py` | `0b49c8e8be46779722a7827b2e98319930433d40` | Imported whole and unchanged. Its real SQLiteManager creates, saves, reads and deletes synthetic table rows. |
| `upstream/main.py` | `6f4292be9d238420062964d2801a3855f5d08570` | Only unchanged `_escape_scope_value` and `_build_session_scope` functions are selected with AST and executed. The full SDK module is not imported. |

The script verifies both source blobs before execution. The sources are included unmodified for reproducibility, with their upstream Apache-2.0 license in `upstream/LICENSE`.

`reference_delete` is our review-only implementation of the proposed two-stage selection, using the real manager's lock and transaction. It reads distinct scope keys rather than raw message content, checks every requested field, then uses parameterized `executemany` deletion by exact scope. It does not replace or monkeypatch an SDK method. The original implementation and feature proposal remain Sai-Sreenath-1819's work.

Run with Python 3.9 or newer from this directory:

```sh
python -B review_scope_matching.py
```

The only executed interpreter version reported here is 3.12.14. The script uses temporary local SQLite files, deletes only its own temporary fixtures, makes no network/model calls and writes `RESULTS.json` beside itself. [Recorded result](RESULTS.json) · [Executable checks and reference helper](review_scope_matching.py).

## Implementation implications

The author's design can work when the SQL candidates are a superset of the true matches. A final exact predicate can reject false positives but cannot recover a matching row excluded by SQL. Current scope encoding is custom delimiter escaping, not ordinary query-string encoding: split encoded fields, partition each once at `=`, then `unquote` values once without converting `+` to space.

Use AND/subset matching for requested fields; preserve additional stored dimensions. For LIKE, use the existing canonical encoding and separately escape SQL `%`, `_` and the chosen escape character, with bound parameters. Selecting all distinct scopes and applying the predicate is a simpler correctness-first alternative; no performance comparison is claimed.

Both synchronous and asynchronous `delete_all` currently pass the serialized scope. A production change to a filter-dictionary interface must update both callers and retain the public empty-filter rejection. Keep selection and deletion together under the lock/transaction. The storage-only threaded check here does not validate AsyncMemory integration.

## Limits and attribution

No public Memory/AsyncMemory API, vector store, LLM, embedding provider, TypeScript path, cross-process concurrent writer or historical noncanonical scope format was executed. The prospective incorrect decoders and prefilters are deliberate alternatives in this review, not defects attributed to an implementation the author has not submitted. The finite matrix is not an exhaustive proof or performance benchmark.

The issue remains open and the original PR remains closed/unmerged pending the accepted-issue gate at the check time. This review neither requests reopening nor creates a competing upstream PR. Original bug/fix work: Sai-Sreenath-1819 and upstream contributors. Supplemental design, code, execution and writing: Zero, AI collaboration partner, with Youngseok Oh's project direction. No claim that Youngseok personally authored or ran the code.
