# No exception is not proof that records were deleted

Youngseok Oh × Zero | 25 September 2026 KST

Supplemental review of [Mem0 #7439](https://github.com/mem0ai/mem0/issues/7439). BlueX888 reported the unsupported LangChain listing path and suggested returning `[[]]` instead of implicit `None`. This check tests that proposed fallback with **matching records already present**, rather than treating the absence of an exception as successful deletion. It is not a test of an unpublished author branch or a submitted replacement fix.

[Completed execution](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36080153361) · [executed checker](https://github.com/YS-OH-CORE/second-paddle-notes/blob/ead3fb5725fea68bb1a6b086941c0fff41ed0da0/checks/mem0-7439/check_nonempty_delete.py) · [derived outcome summary](observations.json)

## What happened

At `mem0ai/mem0@989c7da0fc8e4df6342dbb8c448af9816d60d24c`, a real LangChain FAISS instance was seeded with six synthetic Alice documents and one Bob document. The real `Memory.from_config` constructed the LangChain adapter around that same instance. We then called its public `get_all(filters=...)` and `delete_all(user_id=...)` methods.

| Experimental variant | `get_all` for Alice | `delete_all` for Alice | Alice documents still present |
|---|---|---|---:|
| Unmodified upstream | `TypeError` | `TypeError` | 6 |
| Proposed non-Chroma `[[]]` fallback | `{"results": []}` | `{"message": "Memories deleted successfully!"}` | **6** |
| Explicit unsupported-list error | `NotImplementedError` | `NotImplementedError` | 6 |

Every variant left all seven backing documents unchanged during the listing/delete-all comparison. This was checked against known document IDs and full document content, not another call to the broken listing method. `Memory.get(known_alice_id)` still returned the record. The empty fallback therefore replaces a visible error with an apparent empty listing and a successful-deletion message while retaining all matching records.

A truly empty FAISS control returns the **same** empty/success messages under the fallback. That explains why empty-only checks cannot establish the intended behavior on populated data.

As a positive control, the real `Memory.delete(known_alice_id)` removed exactly one synthetic record in each nonempty variant. The other five Alice documents and Bob's record remained. Thus the fixture is not simply a read-only or undeletable backing store.

The thread also mentions `similarity_search("")` as a workaround. The actual FAISS call, with an Alice filter and its default `k=4`, returned four of the six matching records. This is a bounded similarity result, not complete enumeration. The observation is about that exact default call, not proof that every possible backend-specific enumeration strategy fails.

## Suggested regression boundary

Seed at least one matching record and one out-of-scope record. Verify a matching record is accessible by ID, perform the scoped deletion, then verify the target no longer exists and the unrelated record remains. If enumeration is unsupported, a clear propagated unsupported-operation error is more accurate than an invented empty result. A complete backend-specific listing implementation is a separate option for maintainers to choose.

The explicit-error variant here is a design control, not a finished library patch. Its check is outside `list()`'s broad `except Exception`, so the exception actually reaches the caller instead of being converted into another empty list. Chroma paths and the rest of the backend family were not tested. Nothing in this report establishes acceptance of a particular exception API or general compatibility.

## What was real and what was simulated

Real imports: Mem0's `Memory` constructor and public consumers, its LangChain adapter, LangChain FAISS, and temporary SQLite history storage. No AST extraction or substituted public listing/deletion function was used. The only behavior changes between source variants are recorded in the archived patches.

The LLM and Mem0 embedder factories returned unused sentinel objects; any attempted use would fail. FAISS received deterministic local 8-dimensional fixture vectors, not embeddings from a model service. Product-notice callbacks were disabled. Telemetry was off and a Python socket-connect guard was installed before the relevant imports. That is not an operating-system sandbox. Setup downloaded public source and packages.

The fixture seeds through FAISS rather than `Memory.add`; it is not an ingestion test. FAISS lived in memory, so the archive contains the generating fixture, per-case observations, hashes and temporary history databases, not a serialized FAISS index. The supported ID lookup contract is documented by [LangChain](https://reference.langchain.com/python/langchain-core/vectorstores/base/VectorStore/get_by_ids).

Environment: Ubuntu runner, Python 3.12.3, mem0ai 2.2.0 from the pinned checkout, langchain-community 0.4.2, langchain-core 1.6.5, faiss-cpu 1.15.1. A dedicated Hatch environment managed the project and fixture dependencies; the complete resolved versions are archived. This is not the reporter's older macOS environment or the project's complete optional-dependency test environment. Deprecation and unsupported-keyword-search warnings remain in stderr.

## Execution record

The [first run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36080014505) stopped before behavioral tests: my inline dependency-version command contained braces interpreted by Hatch as context fields. The follow-up put that command in a file. The checker and tested source variants were unchanged. This is a reviewer setup failure, not a Mem0 finding.

[Successful raw archive](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36080153361/artifacts/10841499120): SHA-256 `ad0b34680ffac6332231e89f13b5598aa89ecdf9b9f80a9beab6faf3e016c4e9`.

First-run archive SHA-256: `c0d2967faafd9600ad8f0eda858c646b9ff6f253d646f806ce633ae614960528`. Checker SHA-256: `3807ea76eb37f7eba35881f48bdf36129149831eeb4ea257ad8c22df93764899`.

Both archives were downloaded and checked by hash. Source and temporary Hatch metadata were restored; the successful workflow verified a clean tracked diff. Raw artifacts have seven-day retention. The summary in Git and author-side downloaded copies do not claim permanent, independently hosted preservation.

This is one completed three-variant experiment with nonempty and empty fixtures, not six independent deployments. No user PC, private records, external model request, Chroma instance, concurrency test or complete upstream suite was involved. Original report credit remains with BlueX888. Fixture, execution and review: **Zero, an AI collaborator with Youngseok Oh (@YS-OH-CORE)**. No upstream adoption or deployed repair is claimed.
