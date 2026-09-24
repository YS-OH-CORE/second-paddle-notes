# A Unicode query fix can recover matches without rewriting stored checkpoints

Youngseok Oh × Zero | 25 September 2026 KST

Supplemental regression evidence for [LangGraph #9074](https://github.com/langchain-ai/langgraph/issues/9074). **samintisar** reported the bug, identified its cause, and proposed the one-line `ensure_ascii=False` query change. This review tests that proposal; it does not claim a new fix or compete with the reporter's intended PR.

## Additional question

Does the query-only change find **already-written** checkpoints, or does a demonstration pass only because its test writes new records after applying the fix?

[Completed run 36073744621](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36073744621) · [checker](check_existing_metadata.py) · [original structured summary](result.json)

An unmodified writer process used the real `SqliteSaver.put` and `AsyncSqliteSaver.aput` to create two scratch databases. Each contains 15 scenarios, with one target and one unrelated checkpoint per scenario. After that process exited, fresh base and candidate processes reopened those same databases with SQLite `mode=ro`. Only the query serializer changed. The readers also exercised `InMemorySaver` as a comparison, rebuilding its fixture independently.

## Observed results

| Case group | Base sync/async | Proposed query change sync/async | In-memory comparison |
|---|---|---|---|
| Six Unicode object/list cases | No matching target in each | One correct target in each | One target in each |
| Six compatibility controls | Correct target | Same correct target | Same correct target |
| Reordered nested dictionary | No match | Still no match | Matches |
| Literal backslash-u text versus the actual character | No match | Still no match | No match |
| Reversed list order | No match | Still no match | No match |

The Unicode cases cover accented text, Hangul, a supplementary-plane character, a non-ASCII key **inside** a matched object, a list, and deeper mixed nesting. The filter's top-level key remains the supported ASCII key `v`; this does not test non-ASCII JSON-path keys.

The compatibility controls include nested ASCII, a flat Hangul string, quote/backslash/newline escapes, a literal backslash-u sequence, a boolean and null. Every unfiltered query returned both records. Every nonempty filtered result contained only the target, not its decoy. No sorting, normalization or broadening of equality was added.

**Existing rows stayed unchanged.** The same SHA-256 over all `checkpoints` and `writes` rows, including BLOB bytes, held after seeding and after both readers:

- Sync database: `9ad262d20d9723ede1779556b298d6955dd6994d22bc16597eb7fb89aafb93af`
- Async database: `944d15e499a51468bbe1992da522a22215b4b5ec29c903e7675ee84e1f15908a`

These are hashes of logical stored rows, not the entire physical SQLite/WAL file set. The two databases contain independently generated checkpoint IDs and therefore have different fingerprints. In this fixture, the proposed query fix recovers the intended matches without re-saving, reindexing, or migrating their metadata. That is not a guarantee for arbitrary historical formats or damaged data.

The dictionary-order difference already described by the reporter remains deliberately visible as a separate limitation. A successful test report means the observed results match the stated expectations, including that unresolved case; it does not mean all backends have equivalent JSON semantics.

## Why the result fits the code

The pinned saver stores metadata with `ensure_ascii=False`, while the original object/list query branch uses the default JSON encoder setting. Python documents that the default escapes non-ASCII text. SQLite documents that a single `json_extract` path selecting an object or array returns JSON text. Thus two equivalent decoded objects can have unequal textual representations at this comparison. The candidate aligns the query encoding with the existing writer rather than rewriting saved data.

Primary references: [Python JSON encoder](https://docs.python.org/3.12/library/json.html), [SQLite json_extract](https://www.sqlite.org/json1.html#jex), [pinned query implementation](https://github.com/langchain-ai/langgraph/blob/7daa3ab49d678a5da75edb08baa87db4a2be52c3/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/utils.py).

## Reproduction and boundaries

The [workflow](https://github.com/YS-OH-CORE/second-paddle-notes/blob/8221d2004208a3613bac50022a025f75a8645860/.github/workflows/langgraph-9074-existing-unicode-20260925.yml) retrieves upstream commit `7daa3ab49d678a5da75edb08baa87db4a2be52c3`, installs the two checkpoint packages into an isolated environment, verifies the query file's Git blob `7c7e0600053ebb73eafa36d2e617c76eab547475`, and runs ordinary imports against that checkout. No source extraction, fake saver, fake SQLite engine, or patched result is used. The source file is restored afterward and `git diff --exit-code` succeeds.

The experiment is one CPU workflow, not a full application suite or multiple independent deployments. It ran on Python 3.12.3 / SQLite 3.45.1, checkpoint 4.2.0, checkpoint-sqlite 3.1.1, langchain-core 1.6.5 and aiosqlite 0.22.1. Dependencies were resolved during execution and recorded, not installed from a fully frozen lockfile. It is not a reproduction of the reporter's Windows/SQLite 3.50.4 environment.

No graph execution, model request, real account, private record, concurrent writer, PostgreSQL test, corruption recovery, or historic-client upgrade was involved. The process-local socket guard is not an OS sandbox. Setup reads public sources and package registries. The user's PC was not used. A preceding public-download attempt in the assistant's working container failed DNS resolution before testing; the cloud run completed in one attempt.

[Original archive](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36073744621/artifacts/10839760410) includes the synthetic databases, precise inputs, per-case observations, patch, environment and logs. SHA-256: `b7c3c48282bfc82dc773d98d6f905ce28910aac3d1a51f7ed4586972e6323055`. The downloaded bytes matched GitHub's artifact digest; saved observations were also checked after download. That readback is not a second runtime trial. The artifact expires after seven days; a byte-identical conversation copy was retained.

Checker SHA-256: `79ca815aa529d994250fd40e233bc0473a962a2002065d3a61eb91df68b83fe3`. Summary SHA-256: `8cba89d370f0906f0c3d6877b62c64d825959d8e49b1fa5aeecf19b4cb02da04`.

Review design, fixture, execution and writing: **Zero, an AI assistant collaborating with Youngseok Oh (@YS-OH-CORE)**. Original discovery and proposed repair: **samintisar**. No acceptance, merge, production resolution or institutional endorsement is asserted.
