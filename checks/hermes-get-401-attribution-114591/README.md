# Hermes #114591: a GET challenge is attributed to an unrelated tool failure

**Observed on the pinned PR revision:** a 401 on the optional background GET
stream causes a later tools/call HTTP500 to be labeled `needs_reauth`. The
surrounding healthy tool calls still succeed. The final regression has
**1 failure and 2 passes**, with no setup errors, skips, or outer timeout.

This supports [kvnloo's existing response-attribution review](https://github.com/NousResearch/hermes-agent/pull/114591#issuecomment-5851605557).
The implementation is teknium1's [PR #114591](https://github.com/NousResearch/hermes-agent/pull/114591),
which ports the runtime-auth behavior from kimi-code#3846. This contribution
adds a separate real-HTTP reproducer and its execution evidence.

## Final result

[Final workflow run 36412487458](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36412487458)
ran the full original source checkout at
`646031aa6c87f118e8c0a9b8d4feb79b32fba93c`, with only the new test copied in.
The workflow remains red because the correctness assertion actually fails;
there is no expected-failure wrapper changing it to success.

| Optional GET response | Rejected tool POST response | Observed tool result | Correctness test |
|---|---|---|---|
| 405 | 500 | Generic MCP error; no needs_reauth | Pass |
| 401 | 500 | needs_reauth=true; says the tool call returned 401 | **Fail** |
| 405 | 401 | needs_reauth=true; sign-in guidance | Pass |

Every row also has a healthy tool call before and after the rejected call.
Both return `witness-ok`. The recorded tool calls have IDs 3, 4, 5 and HTTP
statuses 200, the selected failure status, and 200. There is no new initialize
or tools/list after the first tool call. This checks for replays and session
rebuilding; it makes no claim about TCP socket reuse.

The decisive original output is in
[observation-get-401-call-500.json](runs/36412487458/observation-get-401-call-500.json).
The [JUnit report](runs/36412487458/junit.xml) places the sole failure at the
assertion that the500 call must not receive `needs_reauth`. The
[runner log](runs/36412487458/runner.log),
[inputs](runs/36412487458/inputs.json), and
[actual exit record](runs/36412487458/result.json) are retained unchanged.

## Why the final case is ordered

The first GET is Hermes' [connection preflight](https://github.com/NousResearch/hermes-agent/blob/646031aa6c87f118e8c0a9b8d4feb79b32fba93c/tools/mcp_tool_transport.py), before initialize. It has no
MCP session identifier. The corrected test explicitly excludes it from the
synchronization condition. It waits for **two GETs carrying the fixture's MCP
session identifier**. In the final wire record those requests occur at
indices 3 and 5; the first tool call is at index 6.

The pinned [SDK background reader](https://github.com/modelcontextprotocol/python-sdk/blob/6f69a3758ebf2ee55ce050f58b470ce11af71133/src/mcp/client/streamable_http.py)
retries only after handling the preceding GET failure. From that retry order,
we infer that the first session-bearing 401, including the real response hook,
has been processed before tool calls begin. This requires no timing sleep, private timestamp
inspection, or classifier/transport monkeypatch.

Hermes' RPC lock remains active. The test uses real discovery, registration,
registry dispatch, owned HTTP transport, MCP SDK, and error recovery. The
only simulated service is a loopback HTTP server. This is a background-GET
case; it does not reproduce two concurrent tools/call RPCs.

## Frozen inputs and environment

- Original runtime tree: `2a56e26e97845f2934760fbd5e332d5ebc27c283`;
  full checkout of 13,886 tracked files.
- Final [test file](https://github.com/YS-OH-CORE/hermes-agent/blob/951fd532d99a79504a096dae52d7280cf4e441e1/tests/tools/test_mcp_http_auth_witness.py):
  SHA256 `ea5e7aee7d5f43ef5dfc60a6e7c2e85dadc94906bce99a3c277a4bc118efc264`,
  identical before and after the run.
- Verification commit: `951fd532d99a79504a096dae52d7280cf4e441e1`.
  Tracked production diffs are empty before and after testing.
- Fresh Python 3.11.14 environment; uv 0.9.28;
  `uv sync --locked --python 3.11 --extra dev`; dependency cache disabled.
- MCP 2.0.0, httpx2 2.7.0, pytest 9.1.1, pytest-asyncio 1.3.0,
  openai 2.24.0. Exact interpreter/platform details are in
  [environment.json](runs/36412487458/environment.json).
- Canonical `scripts/run_tests.sh`, one worker, zero file retries,
  explicit `-m integration`, a 180-second file bound. The final canonical
  exit code is 1; the outer timeout flag is false.
- The canonical fixtures supply a temporary HERMES_HOME and remove
  credentials. No real accounts or remote MCP services are used by the test.

The [reproduction procedure](https://github.com/YS-OH-CORE/hermes-agent/blob/951fd532d99a79504a096dae52d7280cf4e441e1/scripts/review/http_auth_witness.md)
and [workflow](https://github.com/YS-OH-CORE/hermes-agent/blob/951fd532d99a79504a096dae52d7280cf4e441e1/.github/workflows/http-auth-witness.yml)
are committed alongside the test.

## Complete run history and correction

| Run | Test version | Result | Qualification |
|---|---|---|---|
| [36411636097](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36411636097) | Initial | 1 failure, 2 passes | GET counter included the connection preflight. Misclassification was observed, but the claimed retry synchronization was not established. |
| [36411912136](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36411912136) | Same initial test bytes | 1 failure, 2 passes | Same qualification; an incidental repeat during launch diagnosis, not a planned replication. |
| [36412487458](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36412487458) | Corrected session-bearing GET gate | 1 failure, 2 passes | Final evidence; gate, controls, source revision, and raw exit checked. |

An initial commit-specific workflow lookup returned an empty list. The raw
branch-filtered Actions endpoint later revealed both initial runs, including
the one triggered by the native branch update. All three runs and all 24 raw
receipt files are preserved; no result was discarded. The initial test SHA256
was `ec51050920cd982a5295587c12844b68068c4909755ab758859fe7c846f2a870`.

Each downloaded artifact ZIP was checked against GitHub's published SHA256
digest and CRC before extraction. Original receipt bytes, sizes, and SHA256s
are listed in [receipt-manifest.json](receipt-manifest.json). The
[workflow metadata](workflow-runs.json) records the three distinct runs and
their artifacts. The local source-reading cache was not published; its extra
terminal newline is separate from the exact checkout hashes in the receipts.

## Limits and contribution status

This is evidence for the pinned open PR revision. It does not establish the
same behavior on current main, validate successful OAuth login/refresh, test
the full suite, or supply a production repair. No author acceptance, adoption,
or merge is claimed. The original review and implementation retain their
respective authors' credit.

Zero × Youngseok Oh
