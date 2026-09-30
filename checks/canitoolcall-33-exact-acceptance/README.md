# CanIToolCall #33: exact submitted-code engine acceptance

**Executed at `6111e5b96465ca672205e830ff3bdf1ef28d1df7`. The implementation remains a draft.**

The previous Ollama comparison preceded later report-output guards. This run uses the actual submitted PR commit, with a clean checkout, rather than applying old results to a new implementation. It also exercises the real compiled llama.cpp route for the first time. No runtime source, fixture or expected result was changed during these runs.

## Results

| Engine / upstream PR | Result inventory, base -> head | Changes | CLI exit |
|---|---|---|---:|
| Ollama #18663 | 29 pass / 3 fail / 19 unsupported -> 30 pass / 2 fail / 19 unsupported | 2 improvements, 1 malformed-input recovery regression | 1 |
| llama.cpp #29161 | 41 pass / 2 soft-pass / 8 fail on both sides | no status changes | 0 |

There are 51 records per side. Ollama supports 32 of them; its 19 unsupported records are unchanged. The llama.cpp comparison covers all 51, **not 51 passes**. Exit 0 means no newly regressed cases, not that its eight existing failures disappeared.

The two sides of each engine were actually compiled from complete fixed source revisions into separate temporary projects. The generated revision adapter checks the corresponding commit. Binary hashes and all per-fixture results are retained alongside build/replay logs.

```sh
python scripts/verify_upstream_pr.py --engine ollama --pr 18663 --family glm --build-jobs 2 --json NEW_REPORT.json
python scripts/verify_upstream_pr.py --engine llamacpp --pr 29161 --family glm --build-jobs 2 --json OTHER_NEW_REPORT.json
```

Use the existing frozen project environment and the documented compiler/toolchain prerequisites. Both commands used the existing fixture-pinned vocabulary-only assets. The GLM-4.5 vocabulary needed for llama.cpp was prepared with the existing converter; no model weights or serving endpoint was used.

## Exact revisions

- CanIToolCall: `6111e5b96465ca672205e830ff3bdf1ef28d1df7` (PR #33).
- Ollama base: `7af393188defd52d370464de0d2064649cab9b41`; head: `42c45aed5f4ed442e442c1ec295338acf24ec6a2`.
- llama.cpp base: `e613ef2c81bae98d59850d061ac29e6e3e88cb00`; head: `2959e3ae2706e031eac52ea6c7e44a9e0211c56a`.

The selected llama.cpp PR was already merged on 20 September. It is a real source-pair compatibility control for this verifier, not a new report to that project. It concerns invalid UTF-8 handling; this study did **not** add a targeted malformed-UTF-8 fixture or rerun its upstream tests, so unchanged GLM outcomes do not independently establish that particular fix.

## Preservation

The two pre-existing pinned Ollama binaries in this disposable study checkout were copied from the preceding research workspace; both hashes are identical before and after. For llama.cpp there was **no pre-existing pinned binary** in this checkout: the empty before/after hash maps show preserved absence, not preservation of an existing C++ binary. Neither temporary side replaces the normal engine installation.

`SOURCE_SHA256.json` lists the 212 tracked checkout files after the runs. Git HEAD and a clean tracked checkout were verified. The source hashes can be compared with the submitted commit; the report does not claim independent human execution.

Published reports/logs redact the local home/workspace prefix only. All recorded cases, statuses, engine SHAs and binary hashes remain unchanged. `MANIFEST.json` hashes the published, redacted bytes. The original local receipts and their original hash manifest are preserved separately.

## Remaining gates

The earlier repository suite of 520 pass / 367 skips, lint, format, mypy and fixture validation is a separate historical result for this same commit; it was not rerun here.

Time-limit/cancellation cleanup is still unverified. A separate local lifecycle-helper draft was started, but completion of its real-process test was blocked before execution. That helper and incomplete test were **not used, committed or published as part of this acceptance**. No cleanup success is inferred from ordinary builds finishing below their timeout.

The PR therefore remains draft. Broader timeout/process-tree behavior, platform coverage, report-write failures and maintainer scope decisions still apply. These two local sequential engine comparisons do not establish all engine families, model inference or production safety.

No new comment was posted to llama.cpp. The original project, fixtures and upstream patches retain their authorship. Zero performed the comparison and reporting under Youngseok Oh's direction; no new adoption, endorsement or independent reproduction is claimed.

**Zero × Youngseok Oh**
