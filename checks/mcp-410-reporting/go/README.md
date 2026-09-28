# Completed Go SDK evidence for MCP conformance PR #410

The [real Go SDK verification job completed successfully](https://github.com/YS-OH-CORE/conformance/actions/runs/36384148230) on 2026-09-28. It executed **12 CLI executions (six baseline/candidate comparisons)** through the existing conformance CLI using **Go 1.25.14**, **Node v24.21.0**, and the pinned Go SDK. Every orchestration assertion passed, including the deliberately negative controls.

This supplements [maxisbey's PR #410](https://github.com/modelcontextprotocol/conformance/pull/410), preserving its original product-code scope. A successful verification job means the recorded outcomes matched the controls. It does **not** mean that every SDK scenario passed.

## Provenance

| Input | Exact revision |
| --- | --- |
| Clean candidate | `eac19c4499ebb37ea359024be9aa4cd5c401c154` |
| Baseline | `7169291ec0b68eb370fddcd9947313ab0d5e4156` |
| Go SDK, resolving the author's `827f90b` | `827f90ba0c13edb546028df42fadc9f1211a4ff2` |
| Verification commit | `c8c40a565a1900edbcbd1ef0d8f0aafdaeed50f2` |

The [verification commit](https://github.com/YS-OH-CORE/conformance/commit/c8c40a565a1900edbcbd1ef0d8f0aafdaeed50f2) is directly based on the clean candidate and adds only four `.github` evidence/workflow files. Its workflow separately checks out the candidate at the clean revision and creates the unchanged baseline worktree. The copied fixture, orchestration script, workflow, and preparation README were checked byte-for-byte against that published verification commit.

The protocol mode was **2025-11-25**, on Linux x64. Runtime, source hashes, complete checks, and assertion outcomes are retained in [summary.json](./summary.json). Detailed provenance and hashes are in [manifest.json](./manifest.json).

## Observed suite results

The script built the pinned SDK's **unmodified** `conformance/everything-server` and invoked the actual CLI's `server --suite active --spec-version 2025-11-25` path.

| Go server mode | Revision | SUCCESS | FAILURE | WARNING | INFO | CLI exit | Printed warning total |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Stateful | Baseline | 73 | 0 | 0 | 0 | 0 | Omitted |
| Stateful | Candidate | 73 | 0 | 0 | 0 | 0 | 0 |
| Stateless | Baseline | 55 | 4 | 1 | 2 | 1 | Omitted |
| Stateless | Candidate | 55 | 4 | 1 | 2 | 1 | **1** |

The candidate's printed warning count agrees with the actual recorded checks. The baseline omits that count. Both stateful runs passed all 73 checks.

The stateless configuration is an intentional negative control. Its four failures are retained in full:

- `elicitation-sep1034-general`
- `elicitation-sep1330-general`
- `tools-call-elicitation`
- `tools-call-sampling`

Its warning is `server-sse-multiple-streams-session`: initialization supplies no session ID. The two INFO checks concern session-ID visibility and skipped session-lifecycle coverage. This mode does not support the server-to-client interactions expected by the failing dated scenarios.

**The stateless suite contains four FAILURE checks as well as its warning. Both revisions therefore exit 1. These Go runs demonstrate warning-summary accounting; they do not isolate or prove a warning-only suite exit-code transition.**

## Observed single-scenario controls

The minimal fixture uses the real Go SDK public registration API and Streamable HTTP transport. At the pinned SDK revision, an invalid tool name is logged but remains registered. `warning/tool` supplies an intentional application-level SHOULD violation; `warning_tool` is the clean control. No SDK response bytes are fabricated or mutated.

Each control ran `server --scenario tools-list --spec-version 2025-11-25` on both revisions:

| Control | SUCCESS / FAILURE / WARNING, each revision | Baseline exit | Candidate exit |
| --- | --- | ---: | ---: |
| Warning only, no expected-failures baseline | 2 / 0 / 1 | **0** | **0** |
| Matching per-check baseline for the warning | 2 / 0 / 1 | 0 | 0 |
| Clean, no expected-failures baseline | 3 / 0 / 0 | 0 | 0 |
| Clean with a stale expected-failures entry | 3 / 0 / 0 | 1 | 1 |

All **eight** single-scenario controls emitted `wire-schema-valid: SUCCESS`. The baseline entry was `tools-list:tools-name-format`.

**The unbaselined warning-only single-scenario command still exits 0 on both revisions.** This is a remaining gap in the original PR's scope, preserved and explicitly checked here. It is not reported as fixed.

## Complete retained evidence

[raw-go-evidence.json](./raw-go-evidence.json) contains **all 252 files** from the executed CI artifact, totaling **636,735 original bytes**. Each record includes:

- its original relative path within the artifact;
- original and normalized byte counts;
- original and normalized SHA-256 hashes;
- its complete normalized UTF-8 content.

This includes every CLI check file, full stdout and stderr, invocation and exit metadata, Go build/module records, minimal-fixture HTTP observations, the expected-failures file, empty logs, and the original full summary. The separate `summary.json` is a convenient copy of that same artifact record. JSON/JSONL files inside the raw container are stored as strings, preserving their formatting and decoded bytes.

The executed sources are copied alongside the evidence:

- [run-go-evidence.mjs](./run-go-evidence.mjs): orchestrates builds and existing CLI invocations; it does not implement a separate conformance runner.
- [go-fixture/main.go](./go-fixture/main.go): real SDK single-scenario fixture with transparent HTTP observation.
- [go-evidence-workflow.yml](./go-evidence-workflow.yml): exact workflow used by the successful job.
- [preparation-README.md](./preparation-README.md): the original preparation document from the verification commit. Its historical “not executed” statement describes preparation time; **this completed-execution README and the actual artifact are the current result**.

The stateful/stateless full suites used the SDK's unmodified existing server. Their evidence is the CLI checks and full server logs. HTTP-body observations are provided by the minimal single-scenario fixture only.

## Exact normalization and integrity

The sole transformation of copied evidence is literal UTF-8 replacement of the observed CI workspace prefix:

```text
/home/runner/work/conformance/conformance  →  <CI_WORKSPACE>
```

All other bytes are retained, including failures, stderr, ANSI escapes, timestamps, ephemeral loopback ports, public URLs, JSON formatting, and empty files. The 252 normalized records total **630,147 bytes**. Container JSON escaping changes representation only; decoding each record's `content` reproduces its normalized file bytes. The SHA-256 hashes are calculated before container serialization.

No transient artifact-download URL, signed download credential, or access token is included. Original artifact files remain untouched. `manifest.json` records per-artifact hashes, exact source provenance, and hashes of the publication files other than the manifest itself.

## Reproduction and limits

Use the copied workflow as the exact reproduction record. The orchestration accepts prepared baseline, candidate, and pinned SDK checkouts:

```sh
node run-go-evidence.mjs \
  --baseline /path/to/baseline \
  --candidate /path/to/candidate \
  --sdk /path/to/go-sdk \
  --output /path/to/new-results-directory \
  --suite-modes stateful,stateless
```

The output directory must be new. Go/npm dependencies require ordinary dependency-download access; all server tests use loopback and require no external accounts or credentials. `build-work/` contains caches and binaries and was excluded from the uploaded evidence by the workflow. No additional SDK execution was performed to assemble this publication.

These results cover the pinned Go SDK and protocol mode 2025-11-25. They do not establish other SDK/version coverage, erase the stateless failures, repair the single-scenario warning exit gap, or demonstrate an isolated warning-only suite exit transition.
