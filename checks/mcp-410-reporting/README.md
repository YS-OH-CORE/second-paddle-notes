# MCP conformance #410: author-preserving rebase and execution evidence

This record supports [maxisbey's existing PR #410](https://github.com/modelcontextprotocol/conformance/pull/410), which corrects identity-field validation and includes warnings in the server suite summary. The original three commits have been rebased onto the inspected current main, preserving Max Isbey's authorship and author dates. The clean branch contains those commits and no additional product or test changes from this verification work.

**Result:** the rebased candidate passes 51 focused tests, the complete 639-test CI suite, 20 controlled identity CLI runs (10 baseline/candidate comparisons), and a 12-run verification experiment using the real Go SDK. “Experiment passes” includes assertions about deliberately failing or warning-producing inputs; it does not mean every SDK scenario reports success. The single-scenario server command still exits 0 for a warning-only result.

This is contribution evidence for an open proposal. It does not establish upstream acceptance, merge, or a resolution of the separate warning-policy discussion.

## Reviewable code and provenance

| Item | Revision or link |
| --- | --- |
| Inspected upstream main / comparison baseline | `7169291ec0b68eb370fddcd9947313ab0d5e4156` |
| Original PR head | `bcff2b6ff92eeefb46ed1ee8da1f7457e8bd7d1c` |
| Clean rebased head | [`eac19c4499ebb37ea359024be9aa4cd5c401c154`](https://github.com/YS-OH-CORE/conformance/commit/eac19c4499ebb37ea359024be9aa4cd5c401c154) |
| Rebased branch | [`review/pr-410-reporting-rebased-20260928`](https://github.com/YS-OH-CORE/conformance/tree/review/pr-410-reporting-rebased-20260928) |
| Complete product/test diff | [main to clean candidate](https://github.com/YS-OH-CORE/conformance/compare/7169291ec0b68eb370fddcd9947313ab0d5e4156...eac19c4499ebb37ea359024be9aa4cd5c401c154) |

| Original Max Isbey commit | Rebased commit | Preserved author date (UTC) |
| --- | --- | --- |
| `eef22663e023723a8918aedebb3ab697149a8ec5` | `2425ff69e689cb2f0b73a2c697b19da4618c15b3` | 2026-07-22 21:06:53 |
| `19f65157f8c5e7b0649e91bab0fd12a8552a46ed` | `58da0fdf1e4e18944ca47caad253085cbf4fbdc8` | 2026-07-22 21:07:14 |
| `bcff2b6ff92eeefb46ed1ee8da1f7457e8bd7d1c` | `eac19c4499ebb37ea359024be9aa4cd5c401c154` | 2026-07-22 21:16:15 |

Rebasing changed the committer to Youngseok Oh. All six non-`src/index.ts` file patches retain the original edits, ignoring hunk positions. The only conflict adaptation is in `src/index.ts`: consume `totalWarnings` in the unbaselined suite fallback while preserving the newer `requirementsExitCode(requirements, 'server', allResults)` branch. The seven-file clean diff is 193 insertions and 18 deletions.

The original exclusions remain: tier-check scoring and `sep-2575-client-sends-client-info` are outside this patch. The server metadata check remains SHOULD/WARNING; `mcp-client-initialization` remains MUST/FAILURE. The newer requirements branch is preserved, but requirements/tier behavior was not independently exercised by the additional CLI experiments.

## Why the identity correction is justified

The inspected MCP JSON schemas require `Implementation.name` and `Implementation.version` to be strings, without a `minLength` or pattern constraint. An empty string therefore satisfies these fields' schema types; a truthy number does not. Sources were pinned at spec commit `ab3a39c13bd23be691c2760e1c6c5c15a64582e1`: [draft schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/ab3a39c13bd23be691c2760e1c6c5c15a64582e1/schema/draft/schema.json) and [2025-11-25 schema](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/ab3a39c13bd23be691c2760e1c6c5c15a64582e1/schema/2025-11-25/schema.json).

The original PR replaces truthiness checks with presence/type checks and distinguishes absent metadata from present but malformed fields. That distinction is directly exercised below. This is validation of the existing proposal's field semantics, not a claim about all identity-related checks.

## Focused tests and canonical CI

The same three candidate test files were run against both product revisions:

```sh
npm test -- src/checks/checks.test.ts src/runner/server.test.ts src/scenarios/server/stateless.test.ts
```

| Validation | Baseline | Rebased candidate |
| --- | --- | --- |
| Focused tests, 3 files | 13 failed / 38 passed | 51 passed |
| `npm run check` | Not repeated for this baseline comparison | Typecheck, ESLint and Prettier passed |
| Full existing CI test job | Not rerun for this comparison | 47 files / 639 tests passed |

Of the 13 focused baseline failures, eight detect status or summary behavior and five detect diagnostic wording. Some added tests are passing controls. The evidence does not describe all added tests as failing on main. The full focused output and its exact path normalization are in [local-validation.json](local-validation.json).

The [canonical CI run](https://github.com/YS-OH-CORE/conformance/actions/runs/36383823002), test job `108804914454`, successfully ran `npm ci`, `npm run check`, `npm run build`, and `npm test`. It used verification head `4db04d329da5ef9353903c64d9aa1ef0e26f791e`, whose sole difference from the clean candidate is one push-trigger entry in the existing CI workflow: [verification-only diff](https://github.com/YS-OH-CORE/conformance/compare/eac19c4499ebb37ea359024be9aa4cd5c401c154...4db04d329da5ef9353903c64d9aa1ef0e26f791e). The publish job was skipped. [ci-verification.json](ci-verification.json) preserves job results, revision relationships and relevant log excerpts.

The separate inherited `pkg.pr.new` workflow failed because its GitHub app is not installed on this fork. No package-preview success is claimed; that result is distinct from both successful verification jobs.

## Identity behavior through the actual CLI: 20 runs

Five cases were exercised on two revisions through each of two existing CLI paths. The client experiment sends synthetic raw HTTP initialize requests. The server experiment uses the baseline everything-server behind a synthetic loopback proxy that changes only successful `server/discover` identity metadata. These fixtures intentionally control the tested values; this matrix is not independent real-SDK compatibility evidence.

| Identity fields | Client check, baseline → candidate | Server metadata check, baseline → candidate |
| --- | --- | --- |
| Normal strings | SUCCESS → SUCCESS | SUCCESS → SUCCESS |
| Empty `name` | FAILURE → SUCCESS | WARNING → SUCCESS |
| Empty `version` | FAILURE → SUCCESS | WARNING → SUCCESS |
| Truthy numbers | SUCCESS → FAILURE | SUCCESS → WARNING |
| Missing fields (`{}`) | FAILURE → FAILURE | WARNING → WARNING |

The checks are `mcp-client-initialization` and `sep-2575-server-identifies-in-result-meta`. All 29 non-target server statuses matched for every baseline/candidate pair, and the client's other INFO status was unchanged. No unrelated failure or warning occurred. The scenarios emitted no wire-schema check rows, so this matrix does not claim a separate wire-schema validation pass.

Client failures exited 1. Every single-scenario server run exited 0, including warning cases. The suite exit path is not exercised by this identity matrix.

[Identity evidence](identity/README.md) includes all 20 native reports, CLI stdout/stderr, exact invocations, discovery responses, the executed sources and their hashes: 104 preserved evidence records. A separately labeled convenience runner accepts checkout paths through environment variables; that convenience version was not rerun. Its complete path-configuration diff from the executed source is included.

## Real Go SDK execution: 12 runs

The [Go verification run](https://github.com/YS-OH-CORE/conformance/actions/runs/36384148230), job `108805871886`, succeeded using the actual Go SDK at [`827f90ba0c13edb546028df42fadc9f1211a4ff2`](https://github.com/modelcontextprotocol/go-sdk/commit/827f90ba0c13edb546028df42fadc9f1211a4ff2). Runtime versions were Go `1.25.14` and Node `24.21.0` on Linux x64; the CLI protocol version was `2025-11-25`.

The single-scenario controls use a minimal real SDK server, including a deliberately invalid tool name for a native SHOULD warning. Its HTTP requests/responses are observed without rewriting them. Full suites use the pinned SDK's unmodified `conformance/everything-server` in stateful and stateless modes. The existing conformance CLI owns scenario selection, checks, summary output and exit codes.

| Go case | Baseline and candidate native outcomes | Exit codes, baseline / candidate | Observed summary difference |
| --- | --- | --- | --- |
| Single warning only | 2 SUCCESS, 0 FAILURE, 1 WARNING | 0 / 0 | Single-scenario behavior unchanged |
| Single expected warning baseline | 2 SUCCESS, 0 FAILURE, 1 WARNING | 0 / 0 | Expected baseline behavior retained |
| Single clean | 3 SUCCESS, 0 FAILURE, 0 WARNING | 0 / 0 | Clean behavior retained |
| Single stale expected-warning baseline | 3 SUCCESS, 0 FAILURE, 0 WARNING | 1 / 1 | Stale baseline remains a failing gate |
| Active suite, stateful | 73 SUCCESS, 0 FAILURE, 0 WARNING | 0 / 0 | Candidate explicitly reports 0 warnings |
| Active suite, stateless negative configuration | 55 SUCCESS, 4 FAILURE, 1 WARNING, 2 INFO | 1 / 1 | Candidate reports the previously omitted 1 warning |

Each row represents two real executions. All eight single-scenario controls emitted `wire-schema-valid: SUCCESS`. Both stateless suites contain four native failures; the successful verification job retains and asserts those outcomes. It is not an assertion that every Go SDK scenario passes. Because those suites already have failures, this experiment does not isolate the warning-only suite exit-code difference. The focused summary tests and inspected suite fallback establish the narrower code behavior; no broader end-to-end warning-only suite exit claim is made.

The Go verification head `c8c40a565a1900edbcbd1ef0d8f0aafdaeed50f2` adds only four evidence/workflow files under `.github` on top of the clean candidate: [verification-only diff](https://github.com/YS-OH-CORE/conformance/compare/eac19c4499ebb37ea359024be9aa4cd5c401c154...c8c40a565a1900edbcbd1ef0d8f0aafdaeed50f2). [Go evidence](go/README.md) preserves all 252 artifact files, original and publication hashes, complete native checks, CLI/server logs, build/module metadata, the fixture and the executed orchestration source.

## Scope for the original author to review

The warning summary change is preserved as originally proposed. It does not settle [issue #430](https://github.com/modelcontextprotocol/conformance/issues/430), including the [later discussion of a different warning policy](https://github.com/modelcontextprotocol/conformance/issues/430#issuecomment-5406164079). The single-scenario warning-only exit-0 behavior is demonstrated independently by both the identity fixtures and the real Go SDK. No extra policy fix was silently added during the rebase.

To inspect or run the clean candidate from an existing conformance clone:

```sh
git fetch https://github.com/YS-OH-CORE/conformance.git review/pr-410-reporting-rebased-20260928
git switch --detach eac19c4499ebb37ea359024be9aa4cd5c401c154
npm ci
npm run check
npm run build
npm test
```

The three mapped commits can also be cherry-picked in order from the fetched branch. Exact experiment reproduction instructions and source distinctions are in the identity and Go subdirectories. Evidence was collected on 2026-09-28; upstream main and policy may change after the pinned revisions.

## Credit and AI-use disclosure

Max Isbey authored the original production changes and tests. Zero × Youngseok Oh performed the rebase, execution verification, evidence packaging and review handoff. OpenAI ChatGPT coding tools were used for that work and for drafting this report and the accompanying comment, disclosed under the [MCP AI-use policy](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/AI_POLICY.md). This record does not claim human review by Youngseok Oh or endorsement by the MCP maintainers.

Zero × Youngseok Oh
