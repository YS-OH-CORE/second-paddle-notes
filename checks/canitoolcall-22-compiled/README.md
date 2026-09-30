# CanIToolCall #22: isolated compiled verification, first real Ollama comparison

**Executed result and implementation draft. Not a merge-ready PR.**

This addresses [redd34's requested compiled-engine verification](https://github.com/redd34/canitoolcall/issues/22). CanIToolCall base: `bdade62a9513ccd8657b5e153a9f7ff2421c832d`. The existing fixture corpus and expected results were not edited. Ollama's parser fix belongs to jstar0; this work adds isolated builds, comparison orchestration and supplemental verification.

## Actual command and result

```sh
uv run --frozen python scripts/verify_upstream_pr.py --engine ollama --pr 18663 --family glm --build-jobs 2 --json report.json
```

```text
ollama/ollama#18663  base 7af393188 -> head 42c45aed5
(two isolated full-source builds; pinned harness unchanged)
fixtures replayed: 51   fixed: 2   regressed: 1
  glm/glm47-marker-in-arguments: fail -> pass
  glm/glm47-missing-last-close-arg-value: pass -> fail
  glm/glm47-significant-whitespace: fail -> pass
```

The command returned **1**, the requested regression exit, not a build/setup error. The 51 result records consist of **32 supported fixtures and 19 unchanged unsupported fixtures**. Base: 29 pass, 3 fail, 19 unsupported. Head: 30 pass, 2 fail, 19 unsupported. Do not interpret 51 as 51 successful parser executions.

Full engine pins:
- Base: `7af393188defd52d370464de0d2064649cab9b41`
- Head: `42c45aed5f4ed442e442c1ec295338acf24ec6a2`

Both sides were actually built from complete engine sources, with the real Go replay harness and C++ detokenizer, in separate directories. No changed-file overlay or model inference was used.

## What regressed, precisely

The existing `glm/glm47-missing-last-close-arg-value` fixture is a **malformed-input recovery** case. Its final `</arg_value>` is missing while `</tool_call>` remains. It is derived by the project's fixture generator, not a newly invented output or a newly collected incident. Its provenance and exact token IDs are retained in [regressed-fixture.json](regressed-fixture.json).

```text
<tool_call>get_weather<arg_key>city</arg_key><arg_value>Berlin</arg_value><arg_key>unit</arg_key><arg_value>celsius</tool_call>
```

The unchanged expected result includes both `city=Berlin` and `unit=celsius`. Base meets that expectation. Head instead returns no tool call and reports `OllamaError: incomplete GLM tool call: XML syntax error on line 1: element <arg_value> closed by </tool_call>`. This is a regression against the suite's stated recovery expectation, not evidence that all valid GLM calls fail. Whether the repair policy should change remains an upstream decision; no expected value was changed to conceal the difference.

The target marker-in-string and significant-whitespace fixtures both improve. Full per-case checks and parser metadata are in the two side result files under [receipts](receipts). Native token events and synthetic chunking strategies remain labeled by the original adapter; they are not separate production incidents.

## Pin preservation and scope

The existing pinned harness was built in this disposable study checkout before comparison. Its two actual binary hashes matched before and after:

- `ctcreplay`: `e09c53d2309a47a9bb4c9b47a4721c9d30cb9e0345db98d9582f01aa3d0d7f72`
- `ctc-detok`: `676b1b9a57a94f78ac9c61a0068b6550f403e58a3e416d5aebb908df43724c42`

These are not hashes of unrelated user installations. A temporary revision-specific adapter subclass uses the ordinary version check with the side's exact commit; normal adapter pins and fixture expectations remain unchanged.

The actual replay used Go 1.26.0 and Ollama's llama.cpp tag b11081 for token rendering. The existing vocab-only conversion path built the selected GLM-4.7/5.3 assets at their fixture pins, with no model weights. Fixture GLM-4.7 vocabulary SHA-256: `6b9f8ab9bceda63102fc1fc9775e79287dd4c921eaefa03a9170ab4a14ae6570`. Each result retains vocabulary and engine provenance.

Setup downloaded source and dependencies into an isolated WSL research directory. Replays used the offline local parser path, not a serving endpoint. This is not full model, network-server or production-load validation.

## Implementation and checks

[implementation-draft.patch](implementation-draft.patch) contains the reusable compiled verifier, CLI dispatch, full-SHA overrides, isolated build recipes, tests, documentation and changelog. Python-engine swapping is otherwise unchanged; this does not replace the separately pending report-validation PR #31.

The 26 new orchestration tests passed on Linux and Windows. These use controlled subprocess doubles for isolation and error paths; the real Ollama result above is separate.

The first full candidate suite recorded 497 pass, 1 fail and 367 engine-dependent skips. The failure was the original test that locates the literal default Ollama pin. Retaining the literal pin plus an explicit override fixed that without editing the test. The corrected suite then recorded **498 pass, 0 fail, 367 skips**, compared with unchanged upstream **472 pass, 0 fail, 367 skips**. Both the initial failure and final logs are retained under [checks](checks).

The full compiled replay used the earlier, functionally equivalent SHA override spelling. Its exact executed files are preserved in `receipts/executed-source`. The current patch includes the subsequent literal-pin compatibility correction; the expensive full replay was not repeated after that spelling correction. Do not conflate these source snapshots.

Format, mypy and fixture validation passed. Lint still reports **one RUF002 warning-as-error for the attribution separator in the new docstring**, and its failing exit is preserved. Completing additional CLI/exit-contract test code and a later lint correction were blocked before execution in this session; those changes are not represented as completed. No quality check was disabled.

Therefore this remains an implementation draft: the dedicated argument/exit tests need finishing, lint needs resolving, and the llama.cpp route has orchestration coverage but **no real llama.cpp PR replay** yet. Build cancellation/process-tree cleanup, unsupported inputs and cross-platform behavior also require review before broad use. No merge-ready PR is claimed or opened.

## Reproduction and preserved evidence

Apply the draft to a separate checkout of the fixed CanIToolCall base. Install the existing lockfile with `uv sync --frozen`, supply the documented POSIX toolchains and existing pinned vocabulary-only assets, then run the command above. The per-side build and replay logs are retained even when a regression produces exit 1. Missing/inconsistent results and harness errors return exit 3.

Published receipts replace only the private workspace/home path with placeholders; no fixture expectations or result statuses were changed. The full original local records are retained separately. The implementation patch is a draft, not an invitation to apply it to a production engine installation.

Original project, fixtures and engine fixes retain their authorship. Analysis, implementation, execution and writing here: Zero, with Youngseok Oh's direction. AI assistance is disclosed; no unaided human technical review is claimed. Source context is covered by [the project's license](LICENSE.canitoolcall).

**Zero × Youngseok Oh**
