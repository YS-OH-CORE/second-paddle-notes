# MCP conformance PR #533: cleanup when a connection completes after timeout

## Handoff and authorship

The [follow-up commit `95dd2e2`](https://github.com/YS-OH-CORE/conformance/commit/95dd2e2c64c7173e5f3ddfada7b03512f88eef89) addresses a reproduced late-connection gap in [aton-of-data's PR #533](https://github.com/modelcontextprotocol/conformance/pull/533), directly on `a95deff303dc2221654fe4331daf657e0f2ac690`. The author's cleanup fix `644d355d710ccbde6a446ca8c73cd06d5590a69d`, authorship, and three tests are preserved above base `7169291ec0b68eb370fddcd9947313ab0d5e4156`.

The addition is one 166-line test and a `+15/-5` change in `src/runner/server.ts`. [Complete follow-up diff](https://github.com/YS-OH-CORE/conformance/compare/a95deff303dc2221654fe4331daf657e0f2ac690...95dd2e2c64c7173e5f3ddfada7b03512f88eef89). This handoff makes no adoption or merge claim.

## Reproduced failure

The author's fix closes outstanding connections returned by `ctx.connect()`. A session can exist while SDK connection setup still awaits the HTTP acknowledgment of `notifications/initialized`. A timeout then leaves the cleanup sweep without a returned connection to close.

After the acknowledgment, the original runner gives the connection to the abandoned scenario. Its `prompts/list` receives `-32601`, skipping its success-path close. The leaked session occupies the fixture's sole slot; a healthy successor receives HTTP 503. [Exact final-test failure](final-original-red.log)

The follow-up marks the scenario finished before the sweep. `ctx.connect()` checks before opening another connection and after awaiting one. A late connection is closed and rejected before the abandoned scenario receives it. Existing tracking and the five-second DELETE timeout remain. [Candidate source](https://github.com/YS-OH-CORE/conformance/blob/95dd2e2c64c7173e5f3ddfada7b03512f88eef89/src/runner/server.ts)

## Regression design and result

The test uses actual `runServerConformanceTest`, SDK 1.29.0 `Client`/`StreamableHTTPClientTransport`, and a minimal HTTP fixture imposing capacity one. The fixture is not an SDK server implementation.

It holds the initialized notification's acknowledgment until the runner returns `scenario-timeout`, then releases HTTP 202. A network barrier observes cleanup or an abandoned late probe before starting the successor. After the runner's 1,000 ms timeout, ordering uses acknowledgments and requests, without quiet-time sleeps. Snapshots precede teardown, registered with `onTestFinished`.

| Observation | Original PR head plus final test | Follow-up candidate |
| --- | --- | --- |
| Late-session DELETEs | 0 | 1 |
| Abandoned `prompts/list` probes | 1 | 0 |
| Healthy successor | FAILURE, capacity rejected | SUCCESS |
| Healthy-session DELETEs | 0 | 1 |
| Live fixture sessions before teardown | `s1` | None |

The exact final regression failed on the unchanged original head. [Existing CI run `36391589358`](https://github.com/YS-OH-CORE/conformance/actions/runs/36391589358) passed on the exact candidate: **626 tests across 48 files**, including the author's three tests, plus `npm ci`, `npm run check`, and `npm run build`. [CI verification](standard-ci-verification.json) · [Validation logs](standard-ci-validation.log)

The separate inherited [package-publication workflow](https://github.com/YS-OH-CORE/conformance/actions/runs/36391485935) built successfully but failed at publication: the service returned HTTP 404 because the `pkg-pr-new` app is not installed on this fork. No package publication is claimed. [Publication verification and scope](package-publication-verification.json)

## Exact sources and evidence

[Reproduction commands and archive layout](REPRODUCE.md) describe the two comparisons and all retained attempts.

| Item | Identity |
| --- | --- |
| Candidate commit | `95dd2e2c64c7173e5f3ddfada7b03512f88eef89` |
| Candidate tree | `ebdb44df64e66dbf9b2060c8137e4ca360e560ee` |
| Final new-test SHA-256 | `ca7e920dd8b3c7a156dc35d5d41a62afe0ebca7050cc72c288a41dc8b1ce0a18` |
| Candidate runner SHA-256 | `604d0203639951868d7f7ecebb96de2d97a7b4e97a1fef452c59f68280ebbd54` |

[Original-head execution metadata](final-original-red.json) and [candidate check metadata](final-candidate-check.json) record commands, exits, times, and input hashes. The pre-commit local check records the original HEAD plus candidate file hashes; CI checked out the exact candidate commit.

Development logs retain earlier formatting/cleanup revisions. The final-source comparison uses `final-original-red` and exact-candidate CI. The [raw archive](raw-runs.tar.gz) and [manifest](raw-runs-manifest.json) retain failed attempts, including `local-capacity-01` startup failure, corrected `local-capacity-02`, and the complete extracted CI artifact.

## Separate SDK capacity experiment

The separate lab compares built conformance CLIs against the unchanged conformance baseline's bundled TypeScript `everything-server.ts` using installed SDK 1.29.0, and the Go SDK repository's unchanged `conformance/everything-server` at `827f90ba0c13edb546028df42fadc9f1211a4ff2`. A loopback fixture imposes a four-session admission cap, with clean and injected `prompts/*` `-32601` conditions. The proxy owns both the capacity policy and injected failures.

[Capacity CI `36393089365`](https://github.com/YS-OH-CORE/conformance/actions/runs/36393089365), launched from verification commit `b3c0471b8a49620fbf69daed8359becc41cb1a70`, tested clean candidate `95dd2e2`: **eight cells and 94/94 experiment assertions passed**. Both SDKs produced the following per-cell observations before teardown. [Results](capacity-results.json) · [CI provenance](capacity-ci-verification.json)

| CLI / fixture | SUCCESS / FAILURE | Issued / successful DELETEs | Residual origins | Cap denials |
| --- | --- | --- | --- | --- |
| Baseline, clean | 73 / 0 | 32 / 31 | 1 DNS | 0 |
| Candidate, clean | 73 / 0 | 32 / 31 | 1 DNS | 0 |
| Baseline, reject prompts | 66 / 7 | 30 / 26 | 4 prompts | 3 |
| Candidate, reject prompts | 68 / 5 | 32 / 31 | 1 DNS | 0 |

Each baseline negative run had four intended prompt failures and three capacity-induced failures: the fifth prompt and two DNS checks. Each candidate negative run retained all five intended prompt failures, deleted all five injected sessions exactly once, and had zero capacity denials. Non-prompt statuses matched its clean control. All four negative CLI exits remain **1**; the experiment passes by asserting these outcomes.

This matrix compares pre-fix `7169291` with the combined author cleanup and late guard in `95dd2e2`. Its ordinary prompt-error results validate the author's cleanup as retained in the candidate. The separate original-head-versus-candidate regression above isolates the late-handshake addition.

The residual DNS session bypasses `ctx.connect()` and remains visible in clean and candidate ledgers. These counts measure issued IDs without successful DELETEs, not SDK memory. Claims concern prompt-owned cleanup and controlled failures, not SDK conformance. [Lab sources and predefined assertions](lab/README.md)

## Limits and assistance

Cleanup begins once a pending handshake exposes a `Connection`. It does not cancel a permanently pending bootstrap at the deadline; the session slot can remain occupied until setup completes.

OpenAI Codex was used for analysis, implementation, tests, evidence preparation, and this report under Youngseok Oh's direction. Youngseok Oh directs publication; no complete manual code-review claim is made. Credit for the original fix and three tests remains with aton-of-data.

Zero × Youngseok Oh
