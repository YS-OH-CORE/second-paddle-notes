# Mem0 #7647: flat listing and scoped deletion with real Chroma

**Observed result:** the 16-case deletion matrix passed **16/16 on the upstream-main baseline**, **4/16 on #7647**, and **16/16 on #7647 with two consumer normalization edits adapted from zhgao's #7662**. The PR run produced 12 deletion exceptions; all constructors and pre-deletion public `get_all` checks succeeded. These are completed runs with actual JSON evidence, conducted on 2026-10-18 in one Python 3.12.3 / WSL2 environment.

| Executed source | Passed | Failed | Harness errors | Evidence |
| --- | ---: | ---: | ---: | --- |
| Upstream-main baseline | 16 | 0 | 0 | [base.json](results/base.json) |
| Pinned #7647 head | 4 | 12 | 0 | [pr7647.json](results/pr7647.json) |
| #7647 plus selective consumer control | 16 | 0 | 0 | [control.json](results/control.json) |

The three matrix runs completed at 12:59 UTC (21:59 KST). Counts describe deterministic cases from one run per source, not independent replications. The earlier one-case native-Chroma/sync/populated [smoke run](results/smoke.json) passed and is retained separately, without adding it to the 16-case base result. [Summary](summary.json) · [commands and exit codes](receipts/RUNS.json).

## Exact sources and credit

| Role | Source identity |
| --- | --- |
| Upstream-main baseline | [`0724291bd864cf807e88ee8981c8226644e8fb42`](https://github.com/mem0ai/mem0/commit/0724291bd864cf807e88ee8981c8226644e8fb42) |
| PR under test | [manish-9245's #7647](https://github.com/mem0ai/mem0/pull/7647), head `039b3dd23eca2ba46fc4457c6c1ba18537d849b5` |
| Existing consumer implementation used for the control | [zhgao's #7662](https://github.com/mem0ai/mem0/pull/7662), reference head `4c89a5a04439bd98c4f518bd1a0d27ea1a342f11` |
| Executed control | #7647 head plus [consumer-control.patch](consumer-control.patch); only the two `delete_all` consumers in `mem0/memory/main.py` change |
| Common executed harness | [check_delete_all.py](check_delete_all.py), SHA-256 `2642fbf55b6716ece47a44520e22277186ef2430341772574b5cb62136b58946` |

Credit for routing the deletion consumers through the existing normalization helper belongs to **zhgao / #7662**. The control is a selective adaptation on #7647; the unchanged whole #7662 PR was not executed. Each result records the actual Git HEAD, tracked changes, imported source paths, source-file hashes, harness hash, and installed versions. The base and PR tracked trees were clean; the control records its modified `main.py`.

## Observed failure and explanation

The same behavior occurred through Mem0's native Chroma adapter and its LangChain adapter. The following counts include both adapters:

| Requested Alice scope | API | Cases | #7647 `delete_all(user_id="alice")` |
| --- | --- | ---: | --- |
| Empty: empty store or Bob only | Sync | 4 | `IndexError: list index out of range` |
| Empty: empty store or Bob only | Async | 4 | Success; all checks pass |
| Nonempty: one or three Alice records, plus Bob | Sync | 4 | `AttributeError: 'tuple' object has no attribute 'id'` |
| Nonempty: one or three Alice records, plus Bob | Async | 4 | `AttributeError: 'tuple' object has no attribute 'id'` |

All 12 failing calls left the final vector records unchanged and added no SQLite DELETE history. The eight failures with Alice records retained every target ID. Bob's stored record remained intact wherever present. These runs observed exceptions, with no observed false-success deletion. The JSON retains successful return values, exception types/messages, full tracebacks, before/after records, and history observations for every case. [Full PR evidence](results/pr7647.json).

The source explains this pattern: #7647 changes the adapters' nested list result to a flat list, while leaving [`memory/main.py`](https://github.com/mem0ai/mem0/blob/039b3dd23eca2ba46fc4457c6c1ba18537d849b5/mem0/memory/main.py) unchanged. Sync deletion still selects `list(...)[0]`; async deletion selects `memories[0] if memories else []`. On a nonempty flat list, this selects one record as the batch, and iterating that record yields tuples before the consumer accesses `.id`. On an empty flat list, the sync selection raises immediately.

The control applies `_vector_store_list_rows()` at both deletion consumers. The existing helper unwraps the legacy nested batch and preserves a flat batch, including an empty list. In the measured control, every Alice target was removed, each deletion produced its SQLite DELETE history entry, and Bob's ID, document, and metadata were preserved. This supports the consumer explanation for these two adapters and fixtures; it does not establish behavior for every backend.

## What the harness exercises

Each source runs two adapters × two public APIs × four initial states:

| Scenario | Alice records | Bob records |
| --- | ---: | ---: |
| `empty_store` | 0 | 0 |
| `no_alice` | 0 | 1 |
| `single_alice` | 1 | 1 |
| `populated` | 3 | 1 |

- Real `Memory.from_config` / `AsyncMemory.from_config`, configuration validation, `VectorStoreFactory`, adapter instances, and public `get`, `get_all`, and `delete_all` methods run.
- Each case uses a real `chromadb.EphemeralClient`, a unique collection, and a fresh on-disk temporary `SQLiteManager` history database. The report checks that Chroma is ephemeral and the history file was created.
- The LangChain client is the maintained **`langchain_chroma.Chroma` from `langchain-chroma==0.2.6`**. Its actual `get_by_ids` implementation is exercised; the deprecated community Chroma wrapper is not substituted. Mem0 still requires `langchain-community` for its adapter/config imports. [Pinned client source](https://github.com/langchain-ai/langchain/blob/langchain-chroma%3D%3D0.2.6/libs/partners/chroma/langchain_chroma/vectorstores.py).
- Fixtures use real Chroma `collection.add` with known IDs (`alice-0` through `alice-2`, `bob-0` as applicable), documents, metadata, and explicit four-dimensional vectors. This bypasses `Memory.add`, extraction, and adapter insertion.
- Storage is witnessed by Chroma `collection.get(ids=known_fixture_ids)` plus `collection.count()`, independently of the adapter listing under test. Public known-ID reads and Alice `get_all` are checked before/after deletion; Bob `get_all` and actual SQLite history are checked after deletion.
- Only embedding and LLM factory results are dormant test doubles. Their methods record and raise if invoked; no model methods were called. Mem0 telemetry/notices, Chroma anonymized telemetry, and LangSmith tracing are disabled. No credentials or remote backend are configured; an external network monitor was not part of this check.

## Environment and additional validation

Completed runs used Python **3.12.3**, WSL2/Linux, and a shared **Hatch 1.18.1** environment. Selected resolved packages were `chromadb==1.5.9`, `langchain-chroma==0.2.6`, `langchain-community==0.3.31`, `langchain-core==0.3.86`, and `pydantic==2.14.1`. The source reported `mem0ai==2.2.1`. [Installed dependency inventory](dependencies.json) · [actual setup receipt](receipts/SETUP.json) · [setup events and run accounting](receipts/SETUP_NOTES.md).

On the control checkout, existing `tests/test_memory.py -k delete_all` tests passed **2/2** (60 deselected), and the Chroma/LangChain provider test files passed **45/45**. A narrow Ruff check of the harness (`E4,E7,E9,F`) and `git diff --check` passed. Exact commands and captured output are in [VALIDATION.json](receipts/VALIDATION.json); [VALIDATION_CONTEXT.json](receipts/VALIDATION_CONTEXT.json) records the driver context and source identity checked after those commands. These are selected checks, not a full-suite or GitHub Actions result.

## Portable Hatch reproduction

Start in this artifact directory with Git, Python 3.12, and Hatch 1.18.1 available on PATH. The commands below create disposable source trees and write new results outside the published evidence. This is a portable recipe derived from the recorded setup; it has not been executed again as a fresh installation. The completed runs used the already-created Hatch environment documented above. The dependency inventory and [minimal requirements](requirements-minimal.txt) are not a tested lockfile; a later resolver may choose different versions.

```bash
ARTIFACT_DIR="$(pwd -P)"
REPRO_DIR="$(mktemp -d)"
BASE_DIR="$REPRO_DIR/base"
PR_DIR="$REPRO_DIR/pr7647"
CONTROL_DIR="$REPRO_DIR/control"
OUT_DIR="$REPRO_DIR/results"
git clone https://github.com/mem0ai/mem0.git "$BASE_DIR"
git -C "$BASE_DIR" checkout --detach 0724291bd864cf807e88ee8981c8226644e8fb42
git -C "$BASE_DIR" fetch origin 039b3dd23eca2ba46fc4457c6c1ba18537d849b5
git -C "$BASE_DIR" worktree add --detach "$PR_DIR" 039b3dd23eca2ba46fc4457c6c1ba18537d849b5
git -C "$BASE_DIR" worktree add --detach "$CONTROL_DIR" 039b3dd23eca2ba46fc4457c6c1ba18537d849b5
git -C "$CONTROL_DIR" apply --check "$ARTIFACT_DIR/consumer-control.patch"
git -C "$CONTROL_DIR" apply "$ARTIFACT_DIR/consumer-control.patch"
cp "$ARTIFACT_DIR/hatch.toml" "$BASE_DIR/hatch.toml"
mkdir -p "$OUT_DIR"
cd "$BASE_DIR"
hatch env create regression
hatch run regression:python "$ARTIFACT_DIR/check_delete_all.py" \
  --repo "$BASE_DIR" --label base --output "$OUT_DIR/base.json" --expect pass
hatch run regression:python "$ARTIFACT_DIR/check_delete_all.py" \
  --repo "$PR_DIR" --label pr7647 --output "$OUT_DIR/pr7647.json" --expect observe
hatch run regression:python "$ARTIFACT_DIR/check_delete_all.py" \
  --repo "$CONTROL_DIR" --label control --output "$OUT_DIR/control.json" --expect pass
```

The source project supplies its core dependencies; `features = ["test"]` also supports the recorded unit checks. All three invocations reuse one dependency environment but run in separate Python processes. The harness imports the selected `--repo` and rejects Mem0 modules loaded from elsewhere. Compare the new reports' source identities and dependency versions with the recorded evidence before interpreting differences.

The recorded PR command used `--expect observe`: exit 0 means observation completed, **not that deletion passed**. Its JSON still reports 12 failures. `--expect pass` exits 1 for behavioral failures; either mode exits 2 for bootstrap/fixture/harness errors. To reproduce the earlier one-case smoke selection, add `--adapters native-chroma --apis sync --scenarios populated` to a separate base invocation with a separate output file.

## Completeness and limits

All three completed matrix runs, all 12 failing cases, and the earlier smoke run are retained. [Redactions](redactions.json) document replacement of machine-local directory prefixes and original/public hashes; outcomes, fixture IDs, timestamps, source/harness hashes, exception types/messages, and test outputs are preserved.

This check covers small, single-caller, ephemeral Chroma fixtures and temporary SQLite history. Successful populated cases exercise a nonempty batch followed by an empty batch, but not the 1,000-record batch boundary. It does not test FAISS, Elasticsearch, `Memory.add`, model inference, extraction, entity-store cleanup, persistent/restarted stores, concurrent external callers, unsupported enumeration/`None` returns, backend listing failures, or the full upstream suite. The final-state witness does not observe every possible intermediate mutation. These are self-run results from one environment; no independent human verification is claimed.

Direction and authorization: Youngseok Oh. Harness, execution, and report: Zero. Consumer normalization implementation credit: zhgao / #7662.

**Zero × Youngseok Oh**
