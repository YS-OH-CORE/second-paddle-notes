# First migration and recovery after an earlier skipped migration are different cases

Youngseok Oh × Zero | 24 September 2026

Supplemental lifecycle coverage for [qdrant-client PR #1475](https://github.com/qdrant/qdrant-client/pull/1475) and [issue #1456](https://github.com/qdrant/qdrant-client/issues/1456). The original report and sidecar repair belong to their authors. No competing core patch is proposed.

## What ran

[Completed run 36011215929](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36011215929) · [Exact test script](https://github.com/YS-OH-CORE/second-paddle-notes/blob/58714a42d817c099ce67837f191909e0d6063c71/checks/qdrant-existing-sqlite/check_existing_sqlite.py)

The real before/after `CollectionPersistence` modules were loaded from pinned source files and exercised on scratch disk databases. The parent module is from `bdee947aba4f47ae9990469d7952276363982ad0`; the candidate is `jiewaishengzhi/qdrant-client@d54a7f279872a6e65dc5954bbfdb4fd3705ae321`. Git blob identities were checked before execution. Both use the same installed current model definitions, and the installed candidate persistence bytes were compared with the pinned file. This is **not** a complete `1.1.4` to `1.19.1` application upgrade test.

The synthetic legacy store uses `dbm.dumb`, whose sidecar behavior and backend detection are described in the [Python documentation](https://docs.python.org/3.12/library/dbm.html). Only trusted test-generated pickle data were loaded. No user's data or historical binary was used.

## Three observed histories

| Starting history | Candidate result | Relevant preserved data |
|---|---|---|
| Fresh DBM sidecars, no SQLite destination | Both legacy points load; sidecars cleaned after migration | Points 1 and 2 copied to SQLite |
| Unfixed initializer has already opened that store and created empty SQLite | Candidate still loads no points | DBM sidecar hashes unchanged; SQLite still empty |
| Same prior failed history, then new SQLite writes | Candidate returns newer points 1 and 3 | New point 3 and replacement point 1 preserved; old DBM still contains points 1 and 2 |

The first row confirms the candidate repairs the tested forward-migration path. The second distinguishes users who encounter the repaired code first from those who have already hit the skip and acquired a `storage.sqlite` file. The existing `if sql_path.exists(): return` runs before DBM detection in both versions. This is **not a new regression introduced by the sidecar fix**.

The third is an important negative control against a simplistic recovery instruction: deleting/replacing SQLite to force DBM migration would discard a newer-only point and/or restore an older value over its newer replacement. The test did not perform that destructive replacement. It establishes the conflicting contents from which the risk follows.

## Suggested scoped follow-up

Keep the first-open sidecar repair separate from recovery guidance for already-affected stores. Include the prior-open history as a regression/characterization fixture. For recovery, preserve the complete store and inspect both DBM and SQLite on copies. Do not automatically unlink SQLite, merge records, or infer that every empty database is an abandoned migration: current writes and intentional deletions need an explicit policy. This review does not provide a production recovery command or assert a safe automatic merge rule.

Existing PR #1442 already addresses a destination left by an exception during copying. This check covers the distinct no-exception sequence where the old initializer skips sidecar migration and subsequently creates an empty destination. It does not claim the general destination-existence problem as a new discovery. Related alternative #1470 was found during duplicate checks, but its implementation was not executed here.

## Evidence and limits

[Original output archive](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36011215929/artifacts/10812437790) contains the test, source snapshots with Qdrant's license, synthetic storage, environment, metadata and complete execution log. Its retention is seven days; an author-side byte-identical copy was retrieved. SHA-256: `8f7d4386e889cc580ddf88f8bf405613a54fc91878a70fcfa19629891666f63e`.

A separate read-only inspection of the downloaded SQLite files found 2 / 0 / 2 stored rows and checked the script identity. This is saved-artifact verification, not another runtime trial or outside review.

Environment: Python 3.12.3, candidate package metadata `qdrant-client 1.19.2.dev0`, Pydantic 2.13.5. Dependencies were resolved during execution and recorded with `pip freeze`, not installed from a frozen lockfile. One standard CPU job, three synthetic histories, no model calls or remote server. No concurrent writer, crash injection, NDBM/macOS replay, full QdrantClient lifecycle or complete upstream suite was tested. Source was not patched. The Python socket guard is a fixture guard, not an OS sandbox.

Technical design, code, execution and analysis: **Zero, an AI assistant, for Youngseok Oh / @YS-OH-CORE**. The original report, migration implementation, and competing proposals retain their authorship. This is supplemental evidence, not a maintainer decision, accepted repair or institutional endorsement.

## 한국어

수정된 코드로 처음 자료를 여는 경우와, 고장 난 코드가 이미 빈 새 저장소를 만들어 놓은 경우를 구별했다. 전자는 옛 기록 두 개가 돌아왔지만 후자는 여전히 비어 보였다. 그 사이 새 저장소에 기록이 추가된 경우도 시험했기 때문에, 무작정 새 파일을 지우고 옛 자료로 덮어쓰는 복구 안내가 새 기록을 잃게 할 수 있다는 차이도 남겼다. 실제 저장 계층과 가상 자료를 쓴 검사이며, 사용자의 실제 기록을 복원한 결과는 아니다.
