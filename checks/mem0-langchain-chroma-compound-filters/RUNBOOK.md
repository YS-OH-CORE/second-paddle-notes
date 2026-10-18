# Reproduce the compound-filter experiment

These portable commands describe a fresh independent reproduction. The already-completed executions are preserved in [results/main.json](results/main.json), [results/control.json](results/control.json), [receipts/MAIN_RUN.json](receipts/MAIN_RUN.json), and [receipts/RUNS.json](receipts/RUNS.json). There are two recorded integration executions, 16 cases total; the commands below do not represent additional runs.

## 1. Prepare an isolated environment and paths

Use a clean checkout of `mem0ai/mem0` at `0724291bd864cf807e88ee8981c8226644e8fb42` and read its applicable `AGENTS.md` files. The recorded execution reused a Hatch-managed environment with Python 3.12.3 on WSL2. [dependencies.json](dependencies.json) records the package versions inspected in both matrices; it is a selected-version record, not a complete environment lockfile.

If creating a new environment, use Hatch as required by the upstream instructions. This optional standalone `hatch.toml` configuration reproduces the focused package selection without adding optional dependencies to Mem0's core dependency list:

```toml
[envs.compound-filters]
python = "3.12"
features = ["test"]
dependencies = [
  "chromadb==1.5.9",
  "langchain-chroma==0.2.6",
  "langchain-community==0.3.31",
  "langchain-core==0.3.86",
  "ruff==0.16.0",
]
```

Run `hatch env create compound-filters` from that checkout and use the interpreter in the directory returned by `hatch env find compound-filters`. The following commands assume Linux/WSL paths. Set these task-specific variables to absolute paths in your own workspace:

```bash
CF_MAIN=/absolute/path/to/pinned-mem0-checkout
CF_CONTROL=/absolute/path/to/new-control-worktree
CF_KIT=/absolute/path/to/this-evidence-directory
CF_OUTPUT=/absolute/path/to/new-reproduction-output
CF_PYTHON=/absolute/path/to/hatch-environment/bin/python
mkdir "$CF_OUTPUT"
```

Use a new output directory, not an existing result directory. Confirm the exact source and an empty tracked diff before proceeding:

```bash
git -C "$CF_MAIN" rev-parse HEAD
git -C "$CF_MAIN" status --short --untracked-files=no
"$CF_PYTHON" --version
```

The expected HEAD is `0724291bd864cf807e88ee8981c8226644e8fb42`. An untracked local Hatch configuration is not a source change; a tracked SDK edit would invalidate the unchanged-main comparison.

## 2. Capture each command's stdout, stderr and exit code

This shell helper keeps expected regression failures visible without halting later evidence collection:

```bash
cf_capture() {
  local cf_label="$1"
  shift
  local cf_status=0
  "$@" >"$CF_OUTPUT/$cf_label.stdout.txt" \
    2>"$CF_OUTPUT/$cf_label.stderr.txt" || cf_status=$?
  printf '%s\n' "$cf_status" >"$CF_OUTPUT/$cf_label.exit-code.txt"
  printf '%s: exit %s\n' "$cf_label" "$cf_status"
}
```

Use each label once. Keep the output files even when a command fails. The harness itself refuses to overwrite JSON result paths and checks source identity before and after its matrix.

## 3. Run unchanged main and establish the grammar regression

```bash
cf_capture main "$CF_PYTHON" "$CF_KIT/check_compound_filters.py" \
  --repo "$CF_MAIN" --label main-compound-filters \
  --output "$CF_OUTPUT/main.json" --expect observe

cd "$CF_MAIN"
cf_capture grammar-main env MEM0_TELEMETRY=false PYTHONPATH="$CF_MAIN" \
  "$CF_PYTHON" -m pytest "$CF_KIT/test_langchain_compound_filter_control.py" -q
```

The recorded matrix result was **4 passed, 4 failed**, with four false-empty listings and two false-success deletions. `--expect observe` deliberately returns exit 0 when behavioral failures were captured. The standalone grammar test returned exit 1 with **2 failed, 2 passed**. It validates a real Chroma request grammar at a substituted collection boundary; the populated matrix is the evidence for stored records and deletion.

## 4. Apply only the source control and run the same matrix

```bash
git -C "$CF_MAIN" worktree add --detach "$CF_CONTROL" \
  0724291bd864cf807e88ee8981c8226644e8fb42
git -C "$CF_CONTROL" apply --check "$CF_KIT/langchain-list-compound-equality.patch"
git -C "$CF_CONTROL" apply "$CF_KIT/langchain-list-compound-equality.patch"
git -C "$CF_CONTROL" diff -- mem0/vector_stores/langchain.py

cf_capture control "$CF_PYTHON" "$CF_KIT/check_compound_filters.py" \
  --repo "$CF_CONTROL" --label compound-equality-control \
  --output "$CF_OUTPUT/control.json" --expect pass

cd "$CF_CONTROL"
cf_capture grammar-control env MEM0_TELEMETRY=false PYTHONPATH="$CF_CONTROL" \
  "$CF_PYTHON" -m pytest "$CF_KIT/test_langchain_compound_filter_control.py" -q
cf_capture focused-lint "$CF_PYTHON" -m ruff check --select E4,E7,E9,F \
  "$CF_KIT/check_compound_filters.py" \
  "$CF_KIT/test_langchain_compound_filter_control.py" \
  mem0/vector_stores/langchain.py
cf_capture control-diff-check git diff --check
```

At this point the only tracked modification must be the eight added lines in `mem0/vector_stores/langchain.py`. Its expected SHA-256 is `4f6fb1306ba5aee144d2b9c17836d1781f96f703f2fae9ba0cc868de014f1186`. The recorded control matrix passed **8/8** and the grammar tests passed **4/4**. The source and both deletion consumers were otherwise unchanged.

`--expect pass` returns exit 1 for behavioral failures. Setup/fixture errors, an incomplete matrix or a source identity change produce exit 2. Inspect the JSON instead of treating a shell exit code alone as the behavioral result.

## 5. Apply the separate provider-test change after the matrix

The existing mocked provider test expected the invalid raw dictionary. The test-only patch uses Chroma's real validator and checks matching/nonmatching fixture records independently of the exact predicate encoding. Apply it only after the source-only integration result is recorded:

```bash
git -C "$CF_CONTROL" apply --check "$CF_KIT/existing-langchain-test-only.patch"
git -C "$CF_CONTROL" apply "$CF_KIT/existing-langchain-test-only.patch"
cp "$CF_CONTROL/tests/vector_stores/test_langchain_vector_store.py" \
  "$CF_OUTPUT/test_langchain_vector_store_validated.py"

cd "$CF_MAIN"
cf_capture validated-test-main env MEM0_TELEMETRY=false PYTHONPATH="$CF_MAIN" \
  "$CF_PYTHON" -m pytest \
  "$CF_OUTPUT/test_langchain_vector_store_validated.py::test_list_with_filters" -q

cd "$CF_CONTROL"
cf_capture provider-tests-control env MEM0_TELEMETRY=false PYTHONPATH="$CF_CONTROL" \
  "$CF_PYTHON" -m pytest \
  tests/vector_stores/test_langchain_vector_store.py \
  tests/vector_stores/test_chroma.py -q
cf_capture provider-lint-control "$CF_PYTHON" -m ruff check --select E4,E7,E9,F \
  mem0/vector_stores/langchain.py tests/vector_stores/test_langchain_vector_store.py
cf_capture final-diff-check git diff --check
cf_capture final-diff git diff -- \
  mem0/vector_stores/langchain.py tests/vector_stores/test_langchain_vector_store.py
```

The copied test was executed against unchanged main source and **failed once**, confirming the improved regression detects the problem. With the source and test patches, the two provider files passed **45 tests, 0 skipped**. Selected Ruff rules and `git diff --check` passed. The optional `pytest.importorskip("chromadb.api.types")` was exercised without skipping in the recorded environment.

The original source-only matrix completed at **14:40:04 UTC**, while the test-only patch was applied at **15:17:01 UTC** on 2026-10-18. The test changes therefore did not influence either integration matrix. Keep the same causal separation in an independent reproduction.

## 6. Interpret the actual stored state

For each case, compare compound public responses with `direct_chroma_before`, `direct_chroma_after`, the canonical scope queries, public known-ID reads and `sqlite_history_after` in its JSON. A correct case lists/deletes exactly `target-0` and `target-1`, retains all three control documents/metadata, ends with collection count three, and writes two `DELETE` rows. Main's failing LangChain cases retained all five records and wrote none; the asynchronous success message did not prove deletion.

The raw flat backend query is a deliberate diagnostic and still raises after the control because it bypasses normalization. Its presence in a successful control report is expected. No inference, ingestion, search, general filter-operator support, other backends, persistent restart behavior, batching boundary, full-suite result or performance claim follows from these commands. Preserve any deviations and investigate them before interpreting the comparison.
