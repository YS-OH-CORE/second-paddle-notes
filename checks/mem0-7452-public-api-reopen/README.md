# Mem0 #7452: public API, process reopen, and a separate persistence failure

**Zero × Youngseok Oh | 30 September 2026 KST**

Follow-up to the [original report](https://github.com/mem0ai/mem0/issues/7452) and our [earlier storage-only review](../mem0-7452-recipient-recheck/README.md). Original report: **ac12644**. Exact-key and structured-filter implementation: **Sai-Sreenath-1819**. This contribution verifies those implementations; it is not a competing production fix.

## Result

The structured-filter change fixes the next-prompt raw-message retention checks in all **20 tested API scenarios**: 10 filter/control shapes through `Memory`, and the same 10 through `AsyncMemory`. That is not an all-green end-to-end verdict. Two unmodified async scenarios lost durable vector-deletion state across process reopen, a separate observation also seen in the earlier implementation.

| Unmodified implementation | API | Complete paths passing | Complete paths failing | Next-prompt checks passing | Reopen-state mismatches |
|---|---|---:|---:|---:|---:|
| Earlier exact-key `af93b81b` | sync | 3/10 | 7/10 | 3/10 | 0 |
| Earlier exact-key `af93b81b` | async | 3/10 | 7/10 | 3/10 | 2 |
| Structured-filter `2bdfb63e` | sync | 10/10 | 0/10 | 10/10 | 0 |
| Structured-filter `2bdfb63e` | async | 8/10 | 2/10 | 10/10 | 2 |

A complete path requires both the seed/delete and fresh-process reopen/probe phases to pass. The two phases are not counted as separate scenarios. This is one comparison, not an estimate of population failure rates. The preliminary single-case check and diagnostic interventions are separate receipts, not extra independent successful cases.

[Exact aggregate](summary.json) · [Every scenario and verdict](scenario-outcomes.json) · [Full sanitized observations, prompts and stdout/stderr](receipts.zip).

## What the user-only check now distinguishes

Three synthetic users occupy five user/agent/run scopes. Deleting one user targets three scopes and must preserve the two unrelated scopes. With the old exact-key implementation, matching vector facts disappear but matching raw messages survive; all three return to their own next extraction inputs after an orderly process exit/reopen. The structured implementation removes those messages as well. Its unrelated histories still appear in their own next inputs, not other scopes, and new synthetic memories can still be stored.

The additional shapes are user+run, user+agent, exact user+agent+run, agent-only, run-only, agent+run, unmatched filters, rejected empty public filters, and raw messages for which the synthetic extractor produced no vector memories. Valid identifiers include plus, percent, ampersand, equals, underscore and Korean. Internal whitespace is not used because the public API rejects it.

## The separate async failure must remain visible

In the structured implementation's unmodified async run, the `agent` and `run` cases had the expected vector state immediately after deletion but additional old vector facts after reopening. Their raw-message cleanup and next-prompt marker checks still passed. The original stderr includes `cannot start a transaction within a transaction`. Do not interpret the structured-filter repair as broken because of this distinct vector-persistence boundary, or hide these failures behind the successful prompt checks.

Two separately labeled controls help explain it. First, a diagnostic wrapper serializes only local Qdrant `CollectionPersistence.delete` calls; all 10 async complete paths pass in that run with the same reviewer and assertions. This is evidence about scheduling, not a general thread-safety guarantee or a production patch. Second, deliberately failing one local disk deletion produces a success-shaped `delete_all` reply and no target vector in the immediate view, but one target vector reappears after reopening. The injected failure is not represented as a naturally occurring result.

The inspected qdrant-client 1.19.1 source marks local point IDs deleted in memory before calling disk persistence. The persistence method uses a shared SQLite connection for DELETE and commit. Mem0's `AsyncMemory.delete_all` gathers per-record exceptions, logs them, then returns the success message. This explains the directed-fault observation. The concurrency mechanism is additionally supported, but not exhaustively proven, by the scheduling control. The two revisions' `_delete_memory` methods are identical. See [inspected source excerpts](source-analysis.json); source excerpts retain their original authorship and licenses.

## Method and reproducibility

The unchanged reviewer has SHA-256 `2f2a22c0efd89211402595694dea7d174af4cad72a256520a04b94eb95b9eb61`. It uses real installed `Memory`/`AsyncMemory` public APIs, real file-backed SQLite, and local file-backed Qdrant. Only LLM and embedding factories are replaced: the LLM fixture records fully constructed request messages and returns controlled JSON, while the embedder returns deterministic eight-dimensional vectors. No live model, production database, customer record or API key is used.

Every scenario receives its own fresh storage directory. Separate Python processes perform seed/delete and reopen/probe. Expected retention is derived from the original scope dictionaries, not from the implementation's serialized-key predicate. The prior and updated SDKs were installed in separate Hatch environments; all 44 observed distribution versions match. All 152 `mem0/` and project-metadata files in each source copy match their pinned Git blobs. Source code and assertions were not changed during the comparison. The local Hatch review configuration is the only added environment file.

Pinned revisions: `af93b81bc9573be1b78014b5005a0b0d950605bb` and `2bdfb63e5c0b594bcd339b9222f971d416b681fa` in `Sai-Sreenath-1819/mem0`. [Source identities](source-identities.json) · [Installed versions](dependency-versions.json).

For a fresh disposable checkout of either pin, copy `hatch-review.toml` to its root as `hatch.toml`. It records the observed dependency versions for a repeatable review environment. With Python 3.12 and Hatch available, run the commands below as separate commands, not a success-dependent `&&` chain: baseline seed failures must not prevent the probe. `EVIDENCE` points at this evidence directory and `OUT` at a new synthetic output directory.

```sh
hatch run review:python "$EVIDENCE/public_path_review.py" --phase seed --mode sync --out "$OUT"
hatch run review:python "$EVIDENCE/public_path_review.py" --phase probe --mode sync --out "$OUT"
```

Repeat in a different new output directory with `--mode async`, and in the other pinned checkout. The runner's exit is 1 if any assertion verdict fails, 0 only if all collected scenarios pass; a preparation error is not a passing test. The recorded run used already-created Hatch environments; the portable dependency-pinned configuration was generated from those inventories, not independently reinstalled here.

For the serialized diagnostic control, prefix the unchanged reviewer's path with `serialize_qdrant_delete_control.py` in both commands. For the directed fault, use `inject_one_persistence_failure.py` only for the seed command, `--mode async --case user`, then run the ordinary reviewer for the probe against the same output. Do not apply either control as a production fix.

## Limits, evidence handling and attribution

The recorder forbids non-loopback socket connections and recorded no attempted ones during these tests. Source/dependency preparation uses network access, which is different from the test itself. Optional spaCy and fastembed components are absent; their warnings are preserved. This does not validate entity extraction, BM25, model reasoning, hosted Mem0, remote Qdrant, TypeScript, arbitrary filter syntax, concurrent user add/delete requests, sudden crashes or power loss. A source hash establishes identity, not correctness.

The full 18/20 structured result is retained; the diagnostic 10/10 is not substituted for it. Failures are not relabeled expected successes. The remaining local persistence and error-reporting issue needs a separately scoped correction. No changed assertion, competing PR, maintainer acceptance, upstream merge, release or paid work is claimed.

`receipts.zip` retains every full-comparison phase, the initial structured single-case check, both diagnostic controls and their logs. It excludes SQLite/Qdrant database binaries and temporary profile files. Machine-local paths are replaced with `[REVIEW_WORKDIR]` and `[HOME]`; synthetic scope values, observations and verdicts are retained. Its internal manifest identifies the sanitized files. Initial report-assembly errors are recorded in `summary.json`; fixing packaging did not rerun or change tests.

Original report and implementation keep their contributors' credit. Zero (ChatGPT) authored and executed this verification, analysis and packaging under Youngseok Oh's project direction on his authorized Windows device. No separate unaided human technical review or third-party rerun is claimed. Mem0 and qdrant-client code excerpts retain their respective project licensing; this report does not relicense either project or the surrounding archive.

**Zero × Youngseok Oh**
