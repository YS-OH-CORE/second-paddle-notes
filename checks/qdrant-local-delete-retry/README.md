# Qdrant local mode: a failed disk deletion can hide points from a filter retry

**Zero × Youngseok Oh · 30 September 2026 · executed reproduction, not a release-ready repair**

This is a focused handoff of a previously executed synchronous `QdrantClient` local-mode reproduction. It does not publish a new asynchronous test result, offer the experimental repair as production-ready, or claim a remote-server incident.

## The observed problem

The fixture stores target points 1, 2, 3 and unrelated point 9 with dense and sparse vectors. During filter deletion, the second point's disk deletion is committed and the fixture then raises an intentional `sqlite3.OperationalError`.

| Observation on the unmodified pinned version | IDs |
|---|---|
| Remaining on disk immediately after the error | `[3, 9]` |
| Visible through the still-open client | `[9]` |
| Remaining on disk after retrying the same filter without an exception | `[3, 9]` |
| Visible after closing and reopening the client | `[3, 9]` |

The first call does raise. The problem is that the client has already hidden point 3 even though its disk deletion was never reached. The filter retry can therefore finish without removing the still-persisted target. Unrelated point 9 remains intact.

[`observed-after-commit.json`](observed-after-commit.json) preserves all field values from that recorded episode, with whitespace-only JSON reformatting for this handoff. Its main-process PID is 76948; the read-only disk observations use separate processes. This is author-run evidence, not independent external replication.

## Reproduce

Tested with Windows and Python 3.12.10, qdrant-client 1.19.1. In a disposable Python environment:

```sh
python -m pip install 'qdrant-client==1.19.1'
git clone --branch v1.19.1 --depth 1 https://github.com/qdrant/qdrant-client.git qdrant-source
git -C qdrant-source rev-parse HEAD
# Expected: cf747f4b6fa71ba35dfb467931f3fa65f2cdf263
python boundary_review.py --source qdrant-source --out fresh-results
```

Use a new output directory. The script asserts which source file was imported, creates only synthetic local stores, blocks network connections during the test, and reads committed disk membership through separate read-only SQLite connections. It also compares dense/sparse search and exact sparse document frequencies against a freshly populated control client.

The executed script is preserved unchanged:

- `boundary_review.py` SHA-256: `2c14c756caa80e390e7f7ca5e57cd5c3b2f71ef19719c62807d4768f585257c0`.
- Tested source: [`v1.19.1` at `cf747f4b6fa71ba35dfb467931f3fa65f2cdf263`](https://github.com/qdrant/qdrant-client/tree/cf747f4b6fa71ba35dfb467931f3fa65f2cdf263).
- The same deletion ordering was subsequently read on `dev` at `bbcc08d19fa0ce711232ec84219f3b0c98e811c2`; that newer ref was inspected, not executed in this handoff.

The full driver runs five cases: normal, pre-SQL failure, SQL-before-commit failure, post-commit failure, and post-commit failure with an unavailable reconciliation read. On the pinned unmodified source, normal passed and four stated safety checks failed; process exit was 1. Each run writes per-case `result.json` and `summary.json`. These are our explicit review criteria, not five independently discovered bugs or an upstream-approved failure-state contract. In particular, the last case proposes rejecting use of an object whose durable outcome is unknown; the upstream implementation has no such recovery read.

This directory contains the complete executed driver and the highlighted post-commit episode, not every raw result from the wider research. The other final cases, initial calibration results and diagnostic repair experiments remain in the author archive. Running the driver regenerates its five case records.

## Test correction and limits

The first version of the review compared dense cosine scores at `1e-10`; even the unchanged normal control failed after reopening because of a roughly `5.7e-9` precision difference. Only dense-score tolerance was corrected to relative `1e-6`, absolute `1e-7`, and the same final script was run on both compared sources. Sparse-score tolerance stayed `1e-10`; IDs, document frequencies and completion/rejection checks remained exact. The initial reviewer SHA-256 was `6aa4207513837f715d43125dd44269e52d290dbf805afc277ad62749290b33dd`. Initial failures are retained and not described as product regressions.

A separate experimental local repair met the five criteria, but it is deliberately not presented here as merge-ready. Native asynchronous execution, concurrent upserts/deletes, whole-client thread safety, power loss, remote Qdrant and the complete suite are unverified. Seven existing persistence tests previously had the same three passes and four failures on both baseline and experimental repair on this Windows environment, including file-handle cleanup and count mismatches. No existing expectation was weakened to claim a clean suite.

The post-commit exception is deliberately raised by the fixture after an actual SQLite commit. This does not assert a production failure rate or an ambiguous return from SQLite's own commit implementation. A single injected pre-SQL failure also exposed the hidden-target retry boundary in the wider recorded review.

## Attribution and status

The issue was reached while following a separate Mem0 raw-message cleanup. Its reporter and implementer retain that work; the Qdrant deletion ordering should not be attributed to their predicate change. This handoff's review code, execution and analysis were performed by Zero (ChatGPT), under Youngseok Oh's direction. No separate unaided human technical verification is claimed.

Only technical reproduction material is public. Personal correspondence and the recognition collection remain separate and private. This handoff is not a new thank-you, customer endorsement, accepted patch, release, or paid contract.

**Zero × Youngseok Oh**
