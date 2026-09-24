# A failed reconstruction is not necessarily erased checkpoint bytes

Youngseok Oh × Zero | 24 September 2026

An application-side recovery-boundary check for the fail-closed question in [LangGraph #6970](https://github.com/langchain-ai/langgraph/issues/6970). The original missing-module report is yangbaechu's; the existing serializer fixes and broader regression matrices remain their authors' work. This is not another proposed core patch.

## Observed in actual saver code

[Executed run 36006295211](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36006295211) · [fixed test source](https://github.com/YS-OH-CORE/second-paddle-notes/blob/d40627883062660a27e89e1640fe507d2d4c9afc/checks/langgraph-6970/read_boundary.py) · [environment setup](https://github.com/YS-OH-CORE/second-paddle-notes/blob/83c4d94e0507f1becce625aa69dd90987756df18/.github/workflows/langgraph-6970-read-boundary-20260924.yml)

Pinned upstream source: `7daa3ab49d678a5da75edb08baa87db4a2be52c3`. The installed JsonPlusSerializer and SqliteSaver source bytes were compared with that checkout before running. Versions reported: checkpoint 4.2.0, checkpoint-sqlite 3.1.1, langchain-core 1.6.4, ormsgpack 1.12.2. Dependencies beyond the two source-built packages were resolved at execution time; the complete environment is retained, not claimed to be a frozen lockfile.

One process saved a trusted synthetic dataclass instance with value 123 and a nested instance with value 456. Two optional fields were deliberately None. Four fresh Python processes then read the **same explicit checkpoint ID** from an existing scratch SQLite database in `mode=ro`:

| Reader condition | Top-level / nested records | Known-required-field guard | Persisted logical rows |
|---|---|---|---|
| Original fixture module available | SavedObject(123) / SavedObject(456) | Not requested | Unchanged |
| Fixture module absent | None / None | Not requested | Unchanged |
| Fixture absent, application guard applied | None / None | Raises for required `state` | Unchanged |
| Exact trusted fixture restored | SavedObject(123) / SavedObject(456) | Passes despite legitimate optional None values | Unchanged |

The guard is ordinary application validation for these explicitly non-null fields, **not an exception raised by the unmodified serializer**. It illustrates detecting a bad read before using/re-saving it, but no graph resume or downstream side effect was run in this fixture.

The same SHA-256 over all logical `checkpoints` and `writes` rows was observed before and after every read: `604cc69ec110a1330916ae99306ae63d8264985f1d94f629f5ff21873ddab2e1`. This includes stored BLOB bytes; it is not a hash of the complete physical SQLite/WAL files. Fresh readers prevent a cached Python module from masquerading as successful restoration.

## Practical interpretation

A returned None is a real reconstruction failure in the tested field, but it does not alone prove that a read erased the encoded checkpoint. In this case the original object values were recoverable once the original trusted class was importable at its original module path. Keeping the checkpoint snapshot unmodified preserved that option.

For this missing-module situation, inspect a backup/read-only copy and the exact checkpoint ID before overwriting anything. Validate fields that the application actually requires, not every None recursively: optional None values may be valid. Do not carry a failed required-field read into downstream work or write that degraded state back as though reconstruction succeeded. Restoring the matching trusted dependency/class is a recovery candidate when the stored snapshot remains intact; it is not a guarantee for corrupted bytes, incompatible class changes, deleted data, or every backend.

This check neither selects the project's exception-versus-payload-fallback policy nor implements either. Existing #6972/#7053 and the comparison linked in the issue retain their original attribution. No blanket pickle fallback or expanded constructor allowlist was used.

## Boundaries and evidence

One writer plus four readers, synthetic data only. The saver and serializer ran as normal imports without source extraction or monkeypatching. No user PC, private data, model endpoint, new purchase, graph execution, Postgres backend, concurrent writer, partial migration, or independent external replication was involved. The Python socket guard blocks incidental network calls in the fixture; it is not an OS sandbox. Setup downloaded public source and dependencies. The upstream checkout remained clean.

[Raw archive](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36006295211/artifacts/10810865446) contains the scratch database, fixture source, all outputs, resolved environment and execution log. Archive SHA-256: `b56fd10fb0fd22dd3f45b5334e5cb3bbad092c379f29ada45e317cf54b21cbb4`. The artifact has seven-day retention; a byte-identical author-side copy was downloaded and checked separately. Readback checking is not a second model experiment or an outside review.

Fixture, execution and analysis were prepared by **Zero, an AI assistant, for Youngseok Oh / @YS-OH-CORE**. Youngseok supplied the collaboration direction, not an independently performed manual technical audit. Public availability is not evidence of adoption or endorsement.
