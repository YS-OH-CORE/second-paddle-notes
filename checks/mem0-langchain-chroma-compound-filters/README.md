# Mem0 LangChain/Chroma compound filters: populated reproduction

**Compound identity filters return a false empty list through Mem0's Langchain adapter on the tested main commit.** With matching records present, synchronous `delete_all` raises `IndexError`; asynchronous `delete_all` reports success while leaving every record in place. A control that changes only the compound equality predicate fixes all eight integration cases, preserving the existing nested list contract and both memory consumers.

The complete [main results](results/main.json), [control results](results/control.json), [summary](summary.json), command [receipts](receipts/RUNS.json), and stdout/stderr have been inspected. This package retains **two integration executions, 16 cases total**, including all four failing main cases. Neither matrix was repeated and no case was excluded. These are focused correctness observations, not a full-suite or performance result.

## Observed results

Each case begins with two matching targets and three nonmatching records. Both two-ID and three-ID scopes were exercised through the real `Memory` and `AsyncMemory` APIs.

| Source and adapter/API | Cases | Compound `get_all` before deletion | `delete_all` | Direct Chroma state afterward | SQLite `DELETE` rows per case |
| --- | ---: | --- | --- | --- | ---: |
| Main, native Chroma, sync and async | 4 | Exactly two targets | Success | Exactly three controls | 2 |
| Main, LangChain Chroma, sync | 2 | `{"results": []}` | `IndexError` | All five records unchanged | 0 |
| Main, LangChain Chroma, async | 2 | `{"results": []}` | Success message | All five records unchanged | 0 |
| Equality control, both adapters and APIs | 8 | Exactly two targets | Success | Exactly three controls | 2 |

Main passed **4/8** cases; the control passed **8/8**. Both executions had zero harness errors, unchanged source during their respective runs, and zero model calls. All three control records retained their IDs, documents and metadata in every case. In the four failing main cases, the complete observed before/after snapshots were identical: both targets were still accessible by ID, collection count stayed five, and SQLite history stayed empty. Single-user listing controls worked before deletion in all cases. See [summary.json](summary.json) for the complete case mapping.

This makes the asynchronous success response materially misleading: it accompanies zero target deletion, not a successful deletion of an already-empty scope.

## Actual error and traceback

The following error was captured from the Langchain adapter during the main synchronous two-ID deletion; the three-ID case reports the same validation failure with `run_id` included:

```text
Error listing vectors from Chroma: Expected where to have exactly one operator, got {'user_id': 'alice', 'agent_id': 'agent-a'} in get.
```

The exception propagated by the public synchronous API was recorded as follows. Only private path prefixes are redacted:

```text
Traceback (most recent call last):
  File "<OUTPUT_DIR>/check_compound_filters.py", line 96, in observe
    result = function()
             ^^^^^^^^^^
  File "<OUTPUT_DIR>/check_compound_filters.py", line 432, in <lambda>
    ops["delete_all"] = await observe(lambda: memory.delete_all(**filters))
                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<MAIN_CHECKOUT>/mem0/memory/main.py", line 1937, in delete_all
    memories = self.vector_store.list(
               ^^^^^^^^^^^^^^^^^^^^^^^
IndexError: list index out of range
```

In the asynchronous cases the adapter logged the corresponding error, but the public return value was `{"message": "Memories deleted successfully!"}`. Direct known-ID reads and the independent canonical `$and` query still returned both `target-0` and `target-1`; collection count remained five and `sqlite_history_after.value` was `[]`. The full exceptions, per-operation adapter logs, direct backend validation errors and public responses are retained in [results/main.json](results/main.json).

## Cause and the limited control

At the pinned source, [`Langchain.list`](https://github.com/mem0ai/mem0/blob/0724291bd864cf807e88ee8981c8226644e8fb42/mem0/vector_stores/langchain.py) forwards the flat identity dictionary to Chroma's `where`. Chroma rejects multiple fields at that dictionary level. The adapter catches the exception and returns `[]`; both `get_all` implementations interpret that as no results. The synchronous deletion consumer indexes `[0]`, producing the recorded exception. The asynchronous consumer treats the empty outer list as an empty batch and returns the recorded success message. The [native Chroma provider](https://github.com/mem0ai/mem0/blob/0724291bd864cf807e88ee8981c8226644e8fb42/mem0/vector_stores/chroma.py) already constructs logical conjunctions.

[`langchain-list-compound-equality.patch`](langchain-list-compound-equality.patch) adds **eight lines** in the Chroma-backed listing branch. For multiple ordinary field names with scalar equality values, it combines the predicates under `$and`. It leaves single-field inputs and existing logical predicates on their prior path, does not mutate caller data, and preserves nested `[rows]` output.

During the control matrix, **only `mem0/vector_stores/langchain.py` was modified**. Both memory consumers, native Chroma and all other hashed source files were identical to main. The source-only control ran at **14:40:01–14:40:04 UTC** on 2026-10-18. The separate provider-test patch was applied at **15:17:01 UTC**, after that integration result already existed; it cannot explain the matrix's change from four failures to zero. The recorded [control diff](logs/control-diff.stdout.txt), [final diff](logs/final-diff.stdout.txt), source identities and [command timestamps](receipts/RUNS.json) make that ordering reviewable.

The intervention supports equality-predicate encoding as the cause of these observed failures. It is a **limited equality control**, not a production-complete fix: the integration fixture uses string identity values, and the patch does not repair general error propagation, arbitrary metadata operators or the search path. This experiment is separate from [PR #7647](https://github.com/mem0ai/mem0/pull/7647)'s flat-list change; no edits from that PR or deletion-consumer normalization are included.

## Experiment design

[`check_compound_filters.py`](check_compound_filters.py) uses actual `Memory/AsyncMemory.from_config`, `VectorStoreFactory`, native Chroma and Mem0 Langchain backed by maintained `langchain_chroma.vectorstores.Chroma`. Each case has a unique ephemeral collection and a real temporary SQLite history database.

| Scope | Two targets | Three independent controls |
| --- | --- | --- |
| `user_id=alice`, `agent_id=agent-a` | Records deliberately in different runs | Different user; different agent; different user and agent |
| Above plus `run_id=run-a` | Both records in that exact scope | Different user; different agent; different run |

A run-only difference remains in scope when `run_id` is absent. The two-ID fixture therefore tests that condition positively instead of treating another run as a negative control.

Fixtures are inserted directly into Chroma with explicit IDs, text, metadata and precomputed four-dimensional vectors. Only unused LLM and embedding factory returns are substituted; their model methods raise if called. Actual ingestion, model inference and search are not exercised. Telemetry/tracing is disabled by environment configuration.

The independent witnesses are direct Chroma known-ID reads, collection counts, explicit canonical `$and` equality queries, public per-ID reads, and actual SQLite history. Adapter listing is never used as storage ground truth. The measured stored state covers IDs, count, documents and metadata; it does not establish bitwise embedding preservation. The deliberately submitted raw flat Chroma query fails in all 16 cases, including the control, because that diagnostic bypasses both adapters. Those expected direct-query errors are retained and do not determine a case's behavioral pass result.

## Focused regression checks

| Check | Unchanged main | Equality control | Evidence |
| --- | --- | --- | --- |
| Real populated integration matrix | 4 passed, 4 failed | 8 passed | [main](results/main.json), [control](results/control.json) |
| Standalone real-Chroma-validator boundary tests | 2 failed, 2 passed | 4 passed | [main log](logs/grammar-main.stdout.txt), [control log](logs/grammar-control.stdout.txt) |
| Updated existing provider regression | 1 failed against main source | Included in provider suite below | [failure log](logs/validated-test-main.stdout.txt) |
| LangChain and native Chroma provider files, with test-only patch | Not run as a combined baseline suite | 45 passed, 0 skipped | [provider log](logs/provider-tests-control.stdout.txt) |
| Selected Ruff rules `E4,E7,E9,F` | — | Passed on harness, standalone tests, adapter and updated provider test | [first pass](logs/focused-lint.stdout.txt), [provider pass](logs/provider-lint-control.stdout.txt) |
| `git diff --check` | — | Passed before and after the test patch | [receipts](receipts/RUNS.json) |

The standalone grammar tests call Chroma's real `validate_where` at a substituted external collection boundary. They establish valid request grammar and pass-through behavior, not actual storage/deletion semantics. The [test-only patch](existing-langchain-test-only.patch) strengthens the existing mocked provider test with that validator and an independent equality evaluator over a target and three negative controls. Its Chroma import is optional; the actual focused provider execution skipped **zero** tests. All failing outputs are retained. No full upstream suite, unrestricted package lint, GitHub Actions or independent human rerun is claimed.

## Source and environment identity

Both matrices used Git HEAD **`0724291bd864cf807e88ee8981c8226644e8fb42`** in separate fresh Python processes with identical recorded dependencies. Python was **3.12.3**, on Linux/WSL2 (`Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`). The existing Hatch-managed regression environment was reused without dependency installation in this experiment.

| Identity | SHA-256 |
| --- | --- |
| Executed harness | `8783d575f4d1b33a5003db580241e9a698b2ba09b99d3b717a15755366a6496a` |
| Main `mem0/vector_stores/langchain.py` | `895944935d18ed68a99f0443b9c0591e27d7e7b6bcb2c609bd17ac02a383760d` |
| Control `mem0/vector_stores/langchain.py` | `4f6fb1306ba5aee144d2b9c17836d1781f96f703f2fae9ba0cc868de014f1186` |
| Unchanged `mem0/memory/main.py`, both matrices | `f329ca4a17af1fbefb32ac10d4cc7ae7ddbdb7435a87eb74c30915cff98b8b7c` |

Recorded versions include `mem0ai==2.2.1`, `chromadb==1.5.9`, `langchain-chroma==0.2.6`, `langchain-community==0.3.31`, `langchain-core==0.3.86`, and `pydantic==2.14.1`. See [dependencies.json](dependencies.json) and each result's `source_identity`, `source_identity_after` and `imported_sources` for the remaining recorded identity details. The installed distribution version is context; the imported SDK source is the pinned checkout verified by the harness.

## Reproduction, provenance and limits

[RUNBOOK.md](RUNBOOK.md) gives portable commands and the expected observed counts. [EXECUTION_STATUS.json](EXECUTION_STATUS.json) summarizes the completed evidence. The full result bundle contains 42 payload files covered by [redactions.json](redactions.json), plus that map itself. Its changes replace private absolute path prefixes only; counts, errors, timestamps and synthetic fixture values are retained. Original raw files were preserved by the executing workflow.

Not tested: ingestion, model inference, search, general metadata operators, other LangChain stores, unsupported enumeration, entity cleanup, persistence/restart behavior, concurrent external callers, the 1000-item batch boundary, or the full upstream suite. No security-boundary or bitwise embedding guarantee follows from these fixtures.

Historical [issue #3260](https://github.com/mem0ai/mem0/issues/3260) reported native Chroma multi-field validation. **parshvadaftari's** [merged PR #3269](https://github.com/mem0ai/mem0/pull/3269), merge `42e60d672448ee69c500d466a7e4dc0cf607f22c`, added native normalization while changing Langchain listing to forward the complete raw predicate. Its mocked Langchain collection accepted that representation. This work investigates that remaining path and credits the earlier discovery. Related [issue #7025](https://github.com/mem0ai/mem0/issues/7025) reproduces synchronous empty-outer-list handling with a fake store; the present populated real-backend fixture also establishes asynchronous false success.

Zero authored the harness, control, analysis and issue text and executed the commands through the account owner's authorized workflow. Youngseok supplied direction and authorization; no independent human rerun is claimed. The corresponding upstream issue-form choice is **“AI found and wrote this, and I have not reproduced it myself.”** Any eventual upstream code PR still requires an accepted issue and a signed CLA; this evidence package is not an upstream code PR.

**Zero × Youngseok Oh**
