# 23 October 2026: Qdrant release and Mem0 review follow-through

Zero × Youngseok Oh. Fresh, bounded execution against the authors' actual updated code; no production code changes, model calls, or private user data.

## Qdrant #1510: released fix

The [maintainer confirmed #1510 was fixed in v1.20.0](https://github.com/qdrant/qdrant-client/issues/1510#issuecomment-6360867021). The [22 October release](https://github.com/qdrant/qdrant-client/releases/tag/v1.20.0) includes the work from [#1515](https://github.com/qdrant/qdrant-client/pull/1515). Implementation and integration remain credited to adityaanikam and joein; our contribution is the original report, review and this release comparison.

Fresh Windows / Python 3.12.14 execution used SHA256-verified official PyPI wheels and the same dependency environment. Six scenarios per version cover the synchronous and asynchronous local-client front ends, each with normal deletion, an injected pre-delete error on point 2, and an error injected after point 2's real SQLite deletion committed. A separate read-only process checks disk IDs. The same-filter retry, unrelated point 9, dense/sparse query IDs after retry, and reopened state are checked.

| Version | Passed scenarios | Failed scenarios | Process exit |
|---|---:|---:|---:|
| 1.19.1 | 2 | 4 | 1 |
| 1.20.0 | 6 | 0 | 0 |

For the after-commit case, 1.19.1 retained point 3 on disk while hiding it from the live client, and retry left it on disk. In 1.20.0 the unreached point remains visible and retry leaves only point 9; reopening agrees. Immediately after the synthetic after-commit exception, the already-deleted point 2 can still appear in memory until retry. This comparison does not claim immediate cache/disk equality, whole-batch atomicity, crash durability, concurrent persistence, a remote-server result, or a full-suite pass. The asynchronous front end was tested sequentially.

The initial reviewer installed its no-network guard too early and rejected Windows asyncio's local socket-pair bootstrap before any case ran. The final reviewer installs that same guard after loop bootstrap and before the cases. Product code and assertions were not changed. Both final runs recorded zero socket-connect attempts during the cases. Final reviewer SHA256: `1db01cd1a438e9fb4a42650984d316d470db65c10e9ab20855a9ae20b9f1e704`.

## Mem0 #7647: author follow-up

[manish-9245 reported the two consumer fixes](https://github.com/mem0ai/mem0/pull/7647#issuecomment-6347118756) at `465c701cf4322e7f60120207081ada213f829a59`. We ran the unchanged 18 October reviewer, SHA256 `2642fbf55b6716ece47a44520e22277186ef2430341772574b5cb62136b58946`, against that exact head using the existing Hatch environment: **16 passed, 0 failed, 0 harness errors; exit 0**. The tracked checkout remained unchanged.

The 16 cases combine native Chroma and LangChain Chroma, synchronous and asynchronous Memory APIs, and empty/no-target/single-target/populated scopes. Real constructors, adapters, embedded Chroma, temporary SQLite history and public read/delete methods are exercised. Stored-state witnesses use direct collection reads and counts, not the list method under review. Model/embedding factories are unused test doubles; telemetry/tracing are disabled. Ingestion, inference, other vector stores, batches over 1,000, entity cleanup and the full upstream suite are not tested.

Historical 18 October execution of the same reviewer: main 16/16, earlier PR head 4/16, and a source-only consumer control 16/16. Those are retained prior results, not rerun today. That earlier control matched zhgao's existing #7662 implementation; it is not presented as a new patch authored here. Today's result verifies the author's updated #7647 branch, which was still draft/open/unmerged at inspection.

AI-assisted analysis and execution by Zero under Youngseok Oh's direction. External authors retain their implementation and integration work. This is not independent unaided human certification or an upstream merge decision.

## Inspect and reproduce

[Qdrant reviewer](verify_qdrant_release.py) · [1.19.1 result](qdrant-1.19.1.json) · [1.20.0 result](qdrant-1.20.0.json) · [official wheel provenance](packages.json) · [Mem0 per-case follow-up](mem0-465c701-summary.json).

The unchanged Mem0 reviewer and its historical controls are in the [18 October evidence kit](https://github.com/YS-OH-CORE/second-paddle-notes/tree/29d52a03e9ba80c221c189ef2ca6fa67ae3a90c9/checks/mem0-7647-flat-list-delete-all). Today's per-case summary removes machine-local paths while retaining source hashes, dependency versions, assertions, fixture counts and model-call counters. Raw logs remain retained by the reviewer.

For Qdrant, use an isolated Python 3.12 environment, install qdrant-client 1.20.0 and the dependency versions in the result files, download the two wheels in `packages.json`, verify their SHA256 values, and extract each into a separate directory. Run `python -I verify_qdrant_release.py --package EXTRACTED_WHEEL --out NEW_RESULT_DIR` once per wheel. The result directory must not exist. Exit 1 for 1.19.1 is the reproduced regression; exit 0 for 1.20.0 is the bounded success. The committed reviewer retains the Windows CRLF bytes used in the recorded hash.
