# MCP conformance #165: real SDK proof for simple-text error handling

The rebased change makes `tools-call-simple-text` fail when a tool returns `isError: true`, even when the result contains nonempty text. It also sends `arguments: {}`, allowing SDK 1.29.0 to execute the no-argument diagnostic tool when registered with an empty input schema.

The comparison used the **existing built conformance CLI**, a real **@modelcontextprotocol/sdk 1.29.0** `McpServer` and `StreamableHTTPServerTransport`, and loopback HTTP. Runtime: **Node v24.19.0, Linux x64**. Protocol mode: **2025-11-25**. Recorded on 2026-09-28.

| Product-code checkout | Revision |
| --- | --- |
| Baseline | `7169291ec0b68eb370fddcd9947313ab0d5e4156` |
| Rebased candidate used by the SDK CLI comparison | `0a0039d9226d8dfae490a22256f901c6c97ce8a8` |

The SDK comparison was recorded against candidate `0a0039d`, before the supplemental regression tests were committed. The final clean head is [`89c0d2f9db7f5173cefa8d9dcc2740b262f98947`](https://github.com/YS-OH-CORE/conformance/commit/89c0d2f9db7f5173cefa8d9dcc2740b262f98947). That supplemental commit adds only the regression file and leaves the SDK-tested product code unchanged.

Both compared checkouts have package-lock SHA-256 `8c30fe8f15735bc4660c682225b12ec84bbd08c22e839127445d06b5476c4945` and used the same installed dependency tree.

## Observed CLI behavior

All ten runs emitted **`wire-schema-valid: SUCCESS`**. The scenario check ID remained **`tools-call-simple-text`** for success and failure. All orchestration assertions passed.

| Actual SDK fixture | Baseline CLI / scenario | Candidate CLI / scenario | Handler calls, baseline → candidate |
| --- | --- | --- | --- |
| Text; `isError` absent | exit 0 / SUCCESS | exit 0 / SUCCESS | 1 → 1 |
| Text; `isError: false` | exit 0 / SUCCESS | exit 0 / SUCCESS | 1 → 1 |
| Same nonempty text; `isError: true` | **exit 0 / SUCCESS** | **exit 1 / FAILURE** | 1 → 1 |
| Requested diagnostic tool missing; unrelated tool registered | **exit 0 / SUCCESS** | **exit 1 / FAILURE** | 0 → 0 |
| Successful tool; explicit `inputSchema: {}` | **exit 0 / SUCCESS despite an SDK validation error** | exit 0 / SUCCESS after actual execution | 0 → 1 |

The first three fixtures omit `inputSchema` so argument validation cannot mask error-flag behavior. The deliberate error retains identical nonempty text and changes only `isError`.

The SDK itself generates the missing-tool result: `MCP error -32602: Tool test_simple_text not found`, with `isError: true`. For the baseline empty-schema fixture, the SDK rejects undefined arguments before the handler runs; the error includes `Invalid input: expected object, received undefined`. The candidate sends `{}` and reaches that handler once. These error results were not synthesized by the fixture.

## Local regression checks

The complete captured output is in [local-validation.log](./local-validation.log):

- Baseline, six added regression cases: **3 failed, 3 passed**. The failures expose accepted `isError: true` results, accepted unknown-tool text errors, and omitted empty arguments.
- Candidate, new regression file plus existing `tools.test.ts`: **39 passed across 2 files**.
- Candidate `npm run check`: type checking, ESLint, and Prettier completed successfully.

The baseline failures are retained in full, including assertion details and stack locations. npm warnings and stderr have not been removed. Both SDK-comparison builds passed; their complete stdout and stderr are included in the raw bundle. The ten-case SDK comparison succeeded on its first execution, with no preliminary failed fixture run or discarded comparison.

## Reproduce the SDK comparison

[sdk-fixture.mjs](./sdk-fixture.mjs) follows the installed SDK's `dist/esm/examples/server/simpleStatelessStreamableHttp.js`: one server/transport per request, no session ID, listeners bound to `127.0.0.1` on ephemeral ports. It observes HTTP request bodies, actual SDK response bytes, and handler invocations.

[run-sdk-evidence.mjs](./run-sdk-evidence.mjs) builds each prepared checkout with `npm run build` and invokes its existing CLI:

```sh
node dist/index.js server --url http://127.0.0.1:PORT/mcp \
  --scenario tools-call-simple-text --spec-version 2025-11-25 \
  --timeout 15000 -o RESULTS
```

It reads the CLI-generated checks and exit codes; it does not implement another conformance runner. With both checkouts and dependencies prepared:

```sh
node run-sdk-evidence.mjs \
  --candidate /path/to/rebased-candidate \
  --baseline /path/to/baseline \
  --output /path/to/new-evidence-directory
```

Use a new output directory to retain earlier results. Omitting `--output` creates a timestamped directory under `runs/`. The SDK is resolved from the candidate checkout. These results establish behavior for SDK 1.29.0 and protocol mode 2025-11-25; they do not claim other SDK or protocol-version coverage.

## Files and preservation

This publication consists of seven files:

- `README.md`: method, revisions, results, and reproduction instructions.
- `sdk-fixture.mjs` and `run-sdk-evidence.mjs`: the executed fixture and orchestration source.
- [summary.json](./summary.json): structured comparison, runtime, revisions, and assertion outcomes.
- [raw-evidence.json](./raw-evidence.json): **54 complete source artifacts**—the ten runs' CLI stdout, CLI stderr, invocation metadata, CLI-generated checks, and server observations, plus four build logs. Each entry records its `originalRelativePath` from the evidence directory.
- [local-validation.log](./local-validation.log): the complete `baseline-vitest.log`, `candidate-vitest.log`, and `candidate-check.log`, separated by labeled boundaries.
- [ci-verification.json](./ci-verification.json): remote CI identity, step conclusions, test summary, and the separate package-preview limitation.

Paths in `summary.json` retain their original comparison layout. To locate a referenced source in `raw-evidence.json`, prepend `verified-run/` to a summary `checksPath` or `observationsPath` and match `originalRelativePath`.

The sole text normalization is exact literal prefix replacement: `text.replaceAll(EXECUTION_SCRATCH_ROOT, '<SCRATCH_ROOT>')`, where `EXECUTION_SCRATCH_ROOT` is the run's shared absolute `/workspace/scratch/` session directory. This operation applies to copied text and JSON strings; all other paths and content remain unchanged. JSON consolidation parses and reserializes source JSON but **does not alter any field values beyond that path normalization**. Text logs remain complete, including failures, stderr, ANSI escapes, and empty logs. The `<SCRATCH_ROOT>` marker denotes a publication placeholder, not a runnable directory.

## Full CI and handoff

The [clean handoff branch](https://github.com/YS-OH-CORE/conformance/tree/review/pr-165-iserror-rebased-20260928) contains three commits on baseline `7169291`: the two original changes from [PR #165](https://github.com/modelcontextprotocol/conformance/pull/165), preserving **alu / lux999** as author and the original author dates, followed by one supplemental regression-test commit. The rebase adapts the original change to the current `ctx.connect()` / `conn.request()` API. The original merge commit is not replayed.

The [canonical CI run](https://github.com/YS-OH-CORE/conformance/actions/runs/36381211744) passed `npm ci`, `npm run check`, `npm run build`, and **628 tests across 48 files** on Node 24 / Ubuntu. The publish job was skipped. CI ran at `d64b16b724e8133f8becb4b6c437b7209f78df03`; [its only difference from the clean handoff](https://github.com/YS-OH-CORE/conformance/compare/89c0d2f9db7f5173cefa8d9dcc2740b262f98947...d64b16b724e8133f8becb4b6c437b7209f78df03) is one line enabling that exact verification branch under the existing workflow's push trigger. Product code and tests are identical.

The separate inherited [pkg.pr.new preview workflow](https://github.com/YS-OH-CORE/conformance/actions/runs/36381211781) failed at publishing because its GitHub App is not installed on the fork. Its log explicitly reports that configuration error. This report claims the canonical CI result above, not an all-workflows-green result.

The six added HTTP regression cases use the draft `2026-07-28` mode with valid complete-result envelopes; the ten real-SDK CLI runs use `2025-11-25`, as recorded above. Neither the tested branch nor these results establish upstream review, acceptance, or merge.

## Attribution

The production fix and empty-arguments compatibility change are from **lux999 / alu** in PR #165. This follow-through contributes the current-main rebase, HTTP regressions, and SDK/CI evidence for that existing PR and [issue #515](https://github.com/modelcontextprotocol/conformance/issues/515).

The rebase, regression tests, SDK verification, and this report were produced with OpenAI ChatGPT coding tools.

Zero × Youngseok Oh
