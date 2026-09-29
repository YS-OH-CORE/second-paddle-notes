# MCP #533: characterize the explicitly excluded SDK paths

This test-only follow-up addresses [issue #526](https://github.com/modelcontextprotocol/conformance/issues/526) and [aton-of-data's five-path follow-up](https://github.com/modelcontextprotocol/conformance/pull/533#issuecomment-5880560542). It does not claim a new defect introduced by #533, modify that PR, or replace its already adopted correction. Analysis, test adaptation and execution: **Zero × Youngseok Oh**.

## Executed scope

The actual runner and SDK client at adopted head `95dd2e2c64c7173e5f3ddfada7b03512f88eef89` run against a loopback HTTP fixture with one live session slot. No source extraction, mock runner, model request, external test server or production runtime patch is used. The fixture is adapted from our prior real-HTTP regression in that same commit. It deliberately supplies JSON-RPC errors or a tool result without an elicitation; these are controlled inputs, not defects claimed in an unmodified SDK server.

[Final run 36517193287](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36517193287), verifier `d9e3eeafe18639c0440224c1e91fbde6985cb579`: **7 tests, 3 passed, 4 failed, no pending/todo**. Vitest exits 1 and the workflow stays red. The failing assertions ask for the desired cleanup/no-abandoned-use behavior. They are not converted to passing checks because the failure was expected.

| Real scenario / fixture mode | Session DELETEs before successor | Successor `prompts-list` | Live sessions at final observation |
| --- | ---: | --- | --- |
| Elicitation defaults, tool RPC error | 0 | FAILURE; session-capacity rejection | `s1` |
| Elicitation enums, tool RPC error | 0 | FAILURE; session-capacity rejection | `s1` |
| Elicitation defaults, no elicitation requested | 1 | SUCCESS; its own session closes once | None |
| Elicitation enums, no elicitation requested | 1 | SUCCESS; its own session closes once | None |
| Tracked prompts error, #533 control | 1 | SUCCESS; its own session closes once | None |

Both no-elicitation controls deliberately fail their first diagnostic, but take the explicit early-close branch. This separates a legitimate scenario failure from failure to clean up. The tracked prompts control confirms that the adopted runner repair still isolates an ordinary error in this fixture.

The other two tests hold the first `notifications/initialized` acknowledgment until the runner has returned `scenario-timeout`. Before release, no tool request exists. After release, both direct-SDK elicitation scenarios send one `tools/call` from the abandoned scenario. A positive network barrier observes either a DELETE or that tool request; no quiet-time sleep decides the assertion. This demonstrates post-timeout use. It does **not** establish permanent leakage or eventual cleanup timing for that asynchronous path.

## Why these paths cannot simply call `ctx.connect()`

The [connection interface](https://github.com/modelcontextprotocol/conformance/blob/95dd2e2c64c7173e5f3ddfada7b03512f88eef89/src/connection/index.ts) exposes request/discover/notifications/close, not the SDK `client`. Both elicitation scenarios install `ElicitRequestSchema` handlers on `connection.client`. Replacing their connector call mechanically would lose that surface, in addition to changing version-based transport selection. Their current `catch` records errors without closing the direct SDK connection; the runner's owned set never sees it.

The remaining three paths were source-reviewed, **not executed by this probe**:

| Path | Existing behavior and boundary |
| --- | --- |
| `server/lifecycle.ts` | Uses the raw SDK initialization and then an additional raw request to inspect the session-ID response header. The raw second probe already has a `finally` termination. Do not remove these diagnostic mechanics to obtain ownership. |
| `server/sse-polling.ts` | Uses the SDK transport plus raw POST/GET and event-stream parsing. It already terminates the session and closes the client in `finally` when control reaches that block. |
| `server/sse-multiple-streams.ts` | Uses raw concurrent POST streams and has stateful/stateless-specific setup. It also already has `finally` cleanup. |

Thus the five exclusions are not five identical missing-finally defects. A scenario's `finally` also cannot run while its awaited operation remains pending after the runner abandons it. No new all-path fix is implemented here.

**Proposed discussion boundary:** separate lifecycle ownership from transport selection. Preserve each scenario's existing SDK or raw-stream access, register the same close operation with runner-owned lifetime tracking, and retain before/after-bootstrap finished checks to prevent late handoff. A registration only after `await connect()` would repeat the race fixed by #533. Whether to add such an explicit SDK ownership hook or a narrower mechanism needs maintainer agreement; this is a design proposal, not tested implementation. Permanently pending bootstrap, general cancellation, and the separate SSE framing work are not claimed solved.

## Reproduction and exact evidence

The [probe](probe.test.ts) is copied into `src/runner/server.bypass-observation.test.ts` of a complete clean checkout at the source head above. Run the existing Vitest entry with `ZERO_RECEIPTS` pointing to a new output directory. The committed workflow uses Node 22.22.2, the upstream npm lockfile, `npm ci --ignore-scripts`, and the existing test dependencies; it does not add a runner or new protocol scenario. Runtime traffic uses protocol `2025-11-25` in the fixture. Checkout/upload actions are SHA-pinned; `actions/setup-node@v4` is a moving action tag, not an immutable action pin.

```sh
ZERO_RECEIPTS=/path/to/new/receipts npx --no-install vitest run src/runner/server.bypass-observation.test.ts --reporter=json --outputFile=/path/to/new/receipts/vitest.json
```

The temporary test is removed after the final run. The retained tracked diff is empty. Observations are saved before fixture teardown; closing all sockets during test cleanup is not counted as the production cleanup being tested. [Final raw receipts](receipts/attempt2/) include all seven observations, wire events, reported checks, Vitest JSON, actual exit code, source hashes, and install output.

**First attempt retained:** [run 36516966547](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36516966547), verifier `bbe291c3c6f09e107412312a1b892ada7e00b06c`, recorded 7 failed / 0 passed. My healthy prompt fixture omitted its required description, so all three controls failed their successor checks even though their sessions were closed. The shell also inherited errexit and stopped before saving its intended exit/diff receipts. Attempt 2 adds that description and explicitly captures the test exit. No production behavior or desired cleanup assertion changed. [First raw receipts](receipts/attempt1/) are preserved separately; their invalid controls are not counted as product failures.

This is one completed corrected-fixture experiment after one imperfect attempt, not broad independent replication, a passing full suite, a new release, a merge approval, or validation on a real external server. The source-reviewed SSE and initialization paths remain outside the runtime coverage. All original raw receipt files from both attempts are retained, with an archive/file integrity record.
