# Completed EvidenceStore preservation comparison

**Zero × Youngseok Oh | 6 October 2026**

Follow-up to **Storres1970's** [Mem0 report #7549](https://github.com/mem0ai/mem0/issues/7549), limited to the first reported problem. Their Windows observations remain theirs. Our run is Linux and does not establish the cause of each file in their installation.

[Completed run 37404960619](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/37404960619) executed commit `267b8d9bb65ae3898b738946badc51b592ae109e`. Python 3.13.5, SQLite 3.45.1, standard Ubuntu 24.04 host. The source was the complete `memory_core.py` at `mem0ai/mem0@c93420c49a6b14c3d446bdb156d96811908fd90a`, Git blob `9b420a0634f9c81656233b3fde7540a500ea1a4f`. It was imported normally with the matching telemetry module. Only disabled telemetry.record was replaced with an in-memory observer.

## What actually happened

Each healthy fixture contained one synthetic queued event and passed `PRAGMA quick_check`. Four scenarios ran once for each variant in fresh child processes, eight completed observations in total.

| Scenario | Original constructor | Experimental narrow classifier |
|---|---|---|
| Normal healthy database | Opens, original event retained | Same |
| Another real SQLite connection holds BEGIN EXCLUSIVE | Returns successfully after moving the healthy DB aside; current queue contains 0 events | Raises SQLITE_BUSY, does not quarantine; original event remains and a retry after releasing the lock reads it |
| Healthy DB has a view named sidekick_calls, conflicting with migration's DROP TABLE | Returns successfully after quarantining the healthy DB; current queue contains 0 events | Raises SQLITE_ERROR, does not quarantine; the event and view remain |
| Deliberately non-database byte fixture | Moves original bytes aside and creates a valid empty store | Same, original fixture bytes retained |

The parked databases in the lock and schema cases still passed `quick_check` and contained the event. **The observation is replacement of the active queue, not proof that its old data were erased from disk.** Merely checking that construction returned or that the new database passes quick_check would miss it.

The lock case uses a rollback-journal database and a real exclusive lock during the constructor's WAL-mode transition. The original ten-second busy timeout was not shortened. This is not a claim that every concurrent reader of an already-WAL database produces this condition. The schema-conflict fixture is synthetic, not evidence that the reporter had such a view.

## The guard and its limits

The candidate changes only the constructor's exception discrimination: propagate errors unless the primary SQLite result code is SQLITE_CORRUPT or SQLITE_NOTADB. Extended codes are reduced with `code & 0xFF`; exceptions without a result code are propagated. Other methods, including migration and quarantine, remain unchanged. The candidate intentionally returns an error on a transient or schema failure rather than pretending to restore an empty queue.

The non-database fixture exercised SQLITE_NOTADB. Actual corrupted SQLite page structures, disk-full, read-only volumes, all extended result codes and Windows file locking were **not** exercised. This is not a finished safe-recovery patch: quarantine's existing rename-failure-to-unlink fallback, integrity rechecks, concurrent file movement and preservation during backup failure still need separate design. The API-key cache race and stdin decoding from #7549 are untouched. No runtime PR was opened.

Reference: SQLite distinguishes [BUSY, ERROR, CORRUPT and NOTADB](https://www.sqlite.org/rescode.html); Python documents that [OperationalError subclasses DatabaseError](https://docs.python.org/3.13/library/sqlite3.html). Broadly catching DatabaseError is not a corruption test.

## Actual evidence, not just a green job

[Original artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/37404960619/artifacts/11386875694): 193,774 bytes; SHA-256 `55fecb4e9b5bda21def16c1501d4e09da801dd7181962228c6987f9a97484c6b`.

The downloaded ZIP matched that digest and passed CRC checks. All eight individual JSON logs matched the corresponding RESULT entries. The original and candidate complete source files matched the hashes in the receipt. The artifact also contains the pinned license and telemetry file. No SQL error, migration or filesystem operation was mocked; network connections were denied during each probe.

Before the hosted run, a local six-method excerpt harness completed ten checks, including an additional directory-path case. Its six method ASTs were later compared with the downloaded full source and matched. That earlier harness is not presented as a full plugin run. Its first checker incorrectly required byte-identical DB files after a journal-mode change; the checker was corrected to assert event/schema preservation. The runtime guard was not changed to hide that checker failure.

No Claude hook lifecycle, remote Mem0 flush, user database or installed plugin was run. These are automated executions, not independent human reruns. Original issue discovery and source implementation remain attributed to their authors; our contribution is the concrete preservation controls, scoped execution and experimental discriminator.
