# Hermes #112864: real-fork checkpoint and compaction validation

This evidence supports [Hermes PR #112864](https://github.com/NousResearch/hermes-agent/pull/112864), **Turgut Kural's (`TurgutKural`) fix for checkpoint requirements on persistence-isolated forks**. The original production fix and its authorship remain intact. The accompanying contribution strengthens its two regression tests: real fork construction and compression replace the two helper-level examples. The final candidate passed 115 tests across seven focused files; the new fork invariant fails on both the exact parent and the separately inspected main revision.

Turgut's reported failure occurs when a background-review fork inherits a checkpoint-required profile. The real fork constructor uses `skip_memory=True`, leaving no memory manager, then detaches persistence and enables in-memory compression. Previously, compression demanded a checkpoint-v2 provider even for that disposable transcript. His fix bypasses that requirement for persistence-isolated agents while keeping `compression_checkpoint_required=True` and retaining the durable-agent restriction.

At the recorded GitHub lookup, the original PR was open and unmerged. This evidence does not imply author adoption or maintainer approval.

## Observed results

| Recorded run | Source revision | Result |
|---|---|---|
| [parent-red](logs/parent-red.log) | Exact parent `d4720b4ea85a49b3d16e536eea9fb2c8d10a0e69` | 1 failed, 1 passed; exit 1 |
| [inspected-main-red](logs/inspected-main-red.log) | Inspected main `298df0820d6a72250640600efe454d3debfdf2b4` | 1 failed, 1 passed; exit 1 |
| [candidate-final](logs/candidate-final.log) | Original PR head `5bed864c5f21ba1248d3a266af2f5a6051c8db3f` plus final test overlay | 115 passed, 0 failed; exit 0 |

Both failures are the fork invariant reaching the real checkpoint gate. The durable-agent control passes on all three trees. The specific exception is `agent.conversation_compression.CompressionCheckpointUnavailable`, with the diagnostic:

```text
BLOCKED_MISSING_PREREQUISITE: required pre-compress checkpoint unavailable: no active provider implements checkpoint API v2
```

The logs retain the subsequent recovery guidance and traceback. Both failures occur at the intended runtime boundary.

The final candidate's 115 passing cases comprise:

| Test file | Passed |
|---|---:|
| `tests/agent/test_fork_checkpoint_compaction.py` | 2 |
| `tests/agent/test_pre_compress_checkpoint_contract.py` | 25 |
| `tests/agent/test_background_review_cache_parity.py` | 12 |
| `tests/hermes_state/test_background_review_session_isolation.py` | 8 |
| `tests/agent/test_native_compaction.py` | 64 |
| `tests/agent/test_detached_fork_lifecycle_hooks.py` | 2 |
| `tests/agent/test_review_fork_cache_scope.py` | 2 |

This is two new cases plus 113 neighboring cases, not a full-suite result. The runner's initial approximate discovery count differs from the final executed count because of parametrization; the final summary reports 115.

## Test handoff and source provenance

The test-only handoff is [commit `4263499f48a2b2f5015b60918301d42270c8ff59`](https://github.com/YS-OH-CORE/hermes-agent/commit/4263499f48a2b2f5015b60918301d42270c8ff59), tree prefix `34238ce5`, directly parented by the author's unchanged `5bed864c` commit. Its diff is **two test files, 251 insertions and 37 deletions**, with no production changes. Removing the author's two helper tests restores the existing contract file byte-for-byte to its exact-parent version. This replacement keeps two invariants for the fix, consistent with the repository's test-count guidance.

Execution preceded creation of the handoff commit: [candidate-final metadata](runs/candidate-final.json) records `HEAD=5bed864c` with the final test overlay. Its input hashes identify the tested content subsequently captured by `4263499f`. The frozen new test's SHA-256 is `4ad1674113b027b14e65bc87d868d0c0911b3a34fe7de34ef120c320850278fe`. [Published commit metadata](published-test-commit.json) records its parent and the two verified test blobs; [source provenance](source-provenance.json) records the source preparation. The earlier [development log](logs/development-01.log) also reports two passes, but predates two clarity edits; it is not the verification receipt for this final hash.

The exact parent is distinct from the PR API's observed target-branch SHA, `298df082`. A later source comparison from `298df082` to `5458de` found changes in seven Desktop paths and no Python-code changes, as recorded in [main-source-comparison.json](main-source-comparison.json). **No tests were executed at `5458de`.** Inspection does not extend the execution results to that revision.

## Coverage and limits

The new tests load actual configuration from a temporary `HERMES_HOME`, construct real `AIAgent` instances, use the real `build_cache_parity_fork`, and force compression through `_compress_context` and `ContextCompressor`. They use a real SQLite `SessionDB` and a real `MemoryManager` containing a synthetic checkpoint-v2 provider.

- The fork case requires an actual smaller, marked summary containing the supplied summary text and preserving the final exchange. It checks detached persistence, a retained checkpoint flag, and unchanged parent live history, cached prompt, session row, all message rows for that session, and stored cooldown row. After fork closure, the parent session/message/cooldown snapshot and live history still match, and the parent session remains open.
- The durable `skip_memory=True` control requires the specific checkpoint exception before any summary call and preserves its live history and durable snapshot.

Only `context_compressor.call_llm` supplies a synthetic, typed SDK `ChatCompletion`. Normal summary generation and validation still execute. Configuration sets `abort_on_summary_failure=True`, preventing fallback text from satisfying the positive case. Synchronous HTTP send boundaries reject and record unexpected requests; the new tests record none. This is forced compression coverage, not live-provider or external-checkpoint durability validation, automatic-threshold triggering, the background-review scheduler, `/btw` execution, or a native-backend integration run. Snapshot equality does not establish entire-database immutability or absence of every SQL write.

## Reproduction

Reproduction requires clean checkouts at the exact parent, inspected main, and original PR head listed above. Use a PM-built environment with development and test dependencies, following the repository's instructions. The recorded runtime was **Python 3.14.7 on Linux x86_64**; [runtime.json](runtime.json) records it. `pyproject.toml` and `uv.lock` digests matched across all tested trees and the environment's source checkout.

Set `evidence_root`, `parent_root`, `main_root`, and `candidate_root` to absolute directories, and export `HERMES_PYTHON` pointing to that environment's interpreter. Apply the test-only patch to the candidate; copy the identical new test into both baselines:

```bash
git -C "$candidate_root" apply "$evidence_root/test-upgrade.patch"
cp "$evidence_root/test_fork_checkpoint_compaction.py" "$parent_root/tests/agent/"
cp "$evidence_root/test_fork_checkpoint_compaction.py" "$main_root/tests/agent/"
export HERMES_PYTHON
export HERMES_TEST_WORKERS=1 HERMES_TEST_FILE_RETRIES=0 GIT_NO_LAZY_FETCH=1

(cd "$parent_root" && scripts/run_tests.sh tests/agent/test_fork_checkpoint_compaction.py)
(cd "$main_root" && scripts/run_tests.sh tests/agent/test_fork_checkpoint_compaction.py)

cd "$candidate_root"
scripts/run_tests.sh \
  tests/agent/test_fork_checkpoint_compaction.py \
  tests/agent/test_pre_compress_checkpoint_contract.py \
  tests/agent/test_background_review_cache_parity.py \
  tests/hermes_state/test_background_review_session_isolation.py \
  tests/agent/test_native_compaction.py \
  tests/agent/test_detached_fork_lifecycle_hooks.py \
  tests/agent/test_review_fork_cache_scope.py
```

The two baseline commands intentionally exit 1. Use the canonical runner rather than the bare-pytest suggestion printed inside failure logs. [Run metadata](runs/candidate-final.json), sibling `runs/*.json`, and `logs/*.log` preserve commands, input digests, exit codes, and timing. The bundle includes the frozen [test source](test_fork_checkpoint_compaction.py), [replacement patch](test-upgrade.patch), and [SHA256SUMS](SHA256SUMS) for verification.

Publication replaces only the exact temporary workspace root prefix with `<workspace>` in logs and metadata. Result text is otherwise preserved; run metadata includes both raw and published log hashes.

## Attribution

Original fix: **Turgut Kural / TurgutKural**. Zero prepared and executed this supplementary validation with OpenAI Codex; Youngseok Oh provided direction and publication authorization.

**Zero × Youngseok Oh**
