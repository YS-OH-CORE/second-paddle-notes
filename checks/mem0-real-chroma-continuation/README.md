# Real Chroma: listing succeeds while populated Memory deletion stops at another capability

Youngseok Oh × Zero | 26 September 2026

**With the pinned legacy `langchain_community.vectorstores.Chroma` integration, the revised Mem0 adapter lists matching records correctly, but `Memory.delete_all(user_id='alice')` on a populated collection raises `NotImplementedError: Chroma does not yet support get_by_ids.` All four records remain.** The exact earlier adapter produces the same outcome. This is a separate integration limitation in this tested path, not a regression caused by Souptik96's explicit-error revision and not proof that Chroma itself cannot delete.

The preceding [recipient-revision check](https://github.com/YS-OH-CORE/second-paddle-notes/blob/5bf5a87d001dccae3a83293b11bdc417146fac3c/checks/mem0-7464-recipient-followup/README.md) verified unsupported non-Chroma behavior with real FAISS but used mocked Chroma responses. This follow-up checks the supported enumeration branch with a real local collection. It does not withdraw the earlier seven-test result or claim that every Chroma integration behaves this way.

## What was compared

Mem0 fork commit: `127bb79725aeb09d70e58620fd1d88476abf9aca`. Comparison: only `mem0/vector_stores/langchain.py` is replaced by its exact `cec74a8ebf5a9d6724104d4867868da118b58205` version in the same disposable checkout. No production patch is authored here.

Dependencies: langchain 0.3.30, langchain-community 0.3.31, langchain-core 0.3.86 and chromadb 1.5.9. The LangChain versions match our preceding review environment; this is not a latest-version comparison. The installed legacy Chroma class emits a deprecation warning recommending the separate `langchain-chroma` package. That different integration was **not tested**, so these findings must not be generalized to it or used as a verified migration recommendation.

Each case creates a new named collection in Chroma's local ephemeral client. Populated collections contain three synthetic Alice records and one Bob record, with known IDs, explicit numeric embeddings, documents and metadata. No embedding model runs. The raw collection's own `get()` records every ID, document and metadata entry before and after each operation.

## Actual observations

Both adapter versions yielded the same relevant outcomes:

| Operation | Result | Stored records afterwards |
|---|---|---|
| Adapter lists Alice's records | Returns all three matching IDs | All four unchanged |
| Adapter reads known ID `alice-1` | `NotImplementedError` from inherited `get_by_ids` | All four unchanged |
| Adapter directly deletes known ID `alice-1` | Completes | Alice's other two records and Bob remain |
| `Memory.get_all` on empty collection | Empty results | Empty |
| `Memory.get_all` on populated collection | Returns Alice's three records | All four unchanged |
| `Memory.delete_all` on empty collection | Success response | Empty |
| `Memory.delete_all` on populated collection | `NotImplementedError` | All four unchanged |
| Native Chroma scoped deletion | Completes | Bob alone remains |

There are eight selected operations per adapter, **16 observations total**. Each version met six selected behavior expectations and failed two. The failures are known-ID retrieval and the downstream populated deletion path, not two independently discovered product bugs. No case was skipped or failed during fixture setup.

This is not another observed false-success response: populated `delete_all` raises rather than announcing success. The empty-store success cannot establish that populated deletion works, because no per-record lookup is needed when no records are listed.

## The actual traceback boundary

```text
Memory.delete_all
  -> Memory._delete_memory
  -> Langchain.get
  -> VectorStore.get_by_ids
NotImplementedError: Chroma does not yet support get_by_ids.
```

The captured bound method belongs to `VectorStore.get_by_ids`; its actual source is retained in every observation. The failure is reached while fetching the existing record before deletion. In the failing populated case, the history callback is not called and the raw collection still contains the exact original IDs, contents and metadata.

By contrast, `Langchain.delete(known_id)` and native `collection.delete(where={'user_id':'alice'})` both remove the expected records in their fresh controls. They do not test Mem0's history/entity housekeeping and must not be offered as equivalent application-level fixes. Chroma's own [collection API](https://docs.trychroma.com/reference/python/collection) documents ID and metadata-filter selection for get/delete; those backend capabilities are distinct from the legacy wrapper's inherited method.

## Execution, fixtures and limits

[Completed run 36222923290](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36222923290) completed on its first workflow attempt. The [protocol](PROTOCOL.md), [test](test_real_chroma.py) and [runner](run.py) were committed before execution at `50dfd2d97a70b7895dc69b3ed77799c78ab750bd`; workflow commit `5a97874ee3ba7bd874a796b85bf9e82798e46ba3`.

Real imports: Mem0 `Memory`, the Mem0 Langchain adapter, LangChain's legacy Chroma class and an actual Chroma ephemeral collection. The existing recipient `_build_memory_instance` helper supplies mocked model/embedder factories, configuration, history and telemetry. Its original source remains unchanged. Storage listing, by-ID access, deletion and before/after reads are not mocked. Full production initialization, hosted services, asynchronous Mem0 calls and model behavior are not covered.

Python socket/DNS calls were blocked in the measurement subprocesses; no attempts were recorded. Setup downloads public source and dependencies. This is a Python guard, not an OS network sandbox. No user data, credentials, active deployment or paid inference was used. The scratch source is restored afterwards.

The test invocation uses `--noconftest`, explicit pytest-mock/pytest-asyncio and disabled plugin autoload. It is not the full upstream suite. The resolved environment includes Pydantic 2.13.5, pytest 9.1.1 and pytest-asyncio 1.4.0 on the Ubuntu Python 3.12 runner. The deprecation warning is retained, not suppressed. Remaining dependency resolution was not fully locked.

A green workflow means all planned observations and controls finished, including recorded expectation failures. It does not mean all functionality checks passed. No server fix, maintainer approval, new deployment or external replication is implied.

## Reproduce and audit

With the two adjacent Python files, use a new disposable root:

```sh
python run.py --root /absolute/new_directory --probe ./test_real_chroma.py
```

This downloads the pinned checkout and creates an isolated environment. Never point it at an active application or user data. [SUMMARY.json](SUMMARY.json) holds the compact outcome matrix.

[Raw artifact 10898694527](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36222923290/artifacts/10898694527): 91,167 bytes; SHA-256 `7aa3b210ab468fe70b0468264876fe2b2b7e25ce6d12c6fffc032ae0efdefd90`. It retains all 16 before/after states and return values, exception traces, bound-method source, JUnit files, exact Mem0 source/test snapshots, protocol, logs and environment. Artifact retention is 30 days; the conversation evidence archive also preserves the original ZIP.

The local audit checked the archive digest and byte-identical pre-execution scripts, matched all logged rows to saved observations, recomputed each output/state expectation, checked JUnit failures, and verified unchanged content/metadata for retained records. Both adapter outcomes match after excluding source-path differences in tracebacks. This is reanalysis of the actual run, not a second runtime execution or independent external replication.

## Review conclusion

The existing explicit-error fix addresses the unsupported listing false-success problem. Separately, claiming populated deletion compatibility for this legacy Chroma integration requires a known-ID capability check or an explicitly supported integration path. This observation is a scope clarification for the ongoing review, not a request to expand or block that fix.

Original issue diagnosis: BlueX888. Revised implementation and reused fixture: Souptik96. Supplemental local-storage tests and analysis: Zero, working with Youngseok Oh. Authorship context remains disclosed in the repository. No upstream issue or competing PR was created by this experiment.
