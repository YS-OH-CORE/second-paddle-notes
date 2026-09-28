# Hermes #121944: real HTTP server-fault recovery

Zero × Youngseok Oh · 28 September 2026

**Observed:** the existing fix in [liuhao1024's PR #121944](https://github.com/NousResearch/hermes-agent/pull/121944) passes a new real-HTTP recovery test. The identical test detects an unwanted SSE request on both its unchanged parent and the inspected current-main commit. This is supplemental test coverage for the original fix.

## Ready-to-use test commit

[Commit 60c824e](https://github.com/YS-OH-CORE/hermes-agent/commit/60c824eadd6952175f15e32e703127560d87d7cb) adds only [tests/tools/test_mcp_http_server_fault_recovery.py](https://github.com/YS-OH-CORE/hermes-agent/blob/60c824eadd6952175f15e32e703127560d87d7cb/tests/tools/test_mcp_http_server_fault_recovery.py), directly on the unchanged original PR head `dad46f06772150168a78b2f85f3c7ebed4d27905`. Original production code and authorship are retained. [Branch](https://github.com/YS-OH-CORE/hermes-agent/tree/review/pr-121944-http503-20260928).

The two tests follow the actual boundary reported in [issue #121933](https://github.com/NousResearch/hermes-agent/issues/121933):

1. A disposable loopback HTTP server successfully initializes, then emits plain-text **HTTP 503 on its first tools/list**. The actual MCP 2.0 client converts it to `MCPError(-32603)`; Hermes's actual response hook records the status, URL and body. Its real initial-connect retry method runs with its normal jittered delay. A second initialization/discovery succeeds, and an actual SDK `call_tool` returns the synthetic echo text. Assertions cover the real exception cause, transient classification, recorded details, exactly two initialization/discovery attempts and no legacy SSE GET.
2. A genuine **HTTP 405** rejects the initial Streamable HTTP request. A real legacy SSE endpoint event directs initialize/list/call POSTs to /messages; responses arrive as SSE message events. The same tool call succeeds, and the fallback latch is retained.

The observer on `_on_initial_connect_error` immediately delegates to the original bound method. It does not fabricate exceptions, inject recorder contents, replace transports or shorten retry delays.

## Executed results

| Source receiving the identical new test | Runtime | Observed result |
| --- | --- | --- |
| Original PR parent `749220ef0007f8d87bd1531f1c24b0fe93816385` | Python 3.12.14, original frozen dev lock | **1 failed, 1 passed**: 503 case detects the unwanted GET; legitimate SSE case passes |
| Original PR head `dad46f06772150168a78b2f85f3c7ebed4d27905` | Same Python 3.12.14 environment and lock | **2 passed** in the new file; **41 passed across four related files** |
| Inspected main `68fa7e9f840d24c72774508cc4dc99e8fcceb26f` | Python 3.14.7, existing compatible test environment | **1 failed, 1 passed**, with the same unwanted-GET failure |

All three used the repository's canonical `scripts/run_tests.sh`, normal conftest isolation, and identical new-test Git blob `b36e7271a7519fa37a86bbbed813017b6f477624`. The parent/head comparison uses the **same dependency environment**, so the result is not explained by a dependency difference. The newer main requires Python 3.14 and was checked separately; its environment was not freshly synced to that main commit's lock.

MCP 2.0.0, httpx2 2.7.0, pytest 9.1.1 and pytest-asyncio 1.3.0 were common to all three executions. AnyIO was 4.12.1 for parent/head and 4.14.2 for main. Exact source blobs, environments and exit codes are in [RESULTS.json](RESULTS.json).

Final captured output: [candidate — 41 passed](candidate.log), [parent — expected failure](parent.log), [main — expected failure](main.log). Local workspace/runtime path prefixes are normalized in the published logs; assertions, warnings, requests, counts and failures are retained. Ruff and `git diff --check` passed.

## Reproduce the matched parent/head comparison

```sh
git clone https://github.com/YS-OH-CORE/hermes-agent.git hermes-http503-review
cd hermes-http503-review
git checkout 60c824eadd6952175f15e32e703127560d87d7cb
uv sync --frozen --extra dev --python 3.12
HERMES_PYTHON="$PWD/.venv/bin/python" bash scripts/run_tests.sh -j 2 \
  tests/tools/test_mcp_http_server_fault_recovery.py \
  tests/tools/test_mcp_sse_fallback.py \
  tests/tools/test_mcp_protocol_negotiation.py \
  tests/tools/test_mcp_failure_classification.py -q --tb=short

git worktree add --detach ../hermes-http503-parent 749220ef0007f8d87bd1531f1c24b0fe93816385
cp tests/tools/test_mcp_http_server_fault_recovery.py ../hermes-http503-parent/tests/tools/
HERMES_PYTHON="$PWD/.venv/bin/python" bash ../hermes-http503-parent/scripts/run_tests.sh -j 2 \
  tests/tools/test_mcp_http_server_fault_recovery.py -q --tb=short
```

The parent command is expected to exit 1 with one failed and one passed test. Tests use temporary HERMES_HOME supplied by the existing conftest, disposable loopback servers and synthetic data.

## Scope and development record

The fixture is sessionless: it omits MCP-Session-Id, so SDK 2.0 does not start a normal Streamable HTTP background GET. An observed GET therefore identifies legacy fallback. It sets `protocol: legacy` and `skip_preflight: true` to isolate handshake/discovery and the transport decision. CLI/configuration loading, preflight, OAuth, sessionful notification streams, all 5xx statuses, the full Hermes suite, real flight-service availability and a rebase of the original fix onto main were not validated.

For a bounded negative control, the HTTP-only fixture answers an erroneous GET with 405. It detects the wrong transition rather than reproducing the live service's 30-second SSE hang. A real legacy-SSE positive control prevents a test that simply disables all fallback from passing.

Before the recorded final runs, a development invocation reached both real tool-call results but failed at the new test's `isError` assertion: SDK 2 exposes `is_error`. Correcting that test field yielded 2 passes. The no-GET assertion was then moved ahead of downstream exception diagnostics, and the final four-file run above verified that exact file. Those two development invocations were observed in the tool transcript but were not archived as separate log files. An initial Python 3.14 environment attempt was rejected by the original PR's declared Python <3.14 requirement before tests ran; the matched comparison consequently uses its supported Python 3.12 environment.

Original bug report, reproduction and proposed guard: **fmunechi**. PR implementation and existing unit coverage: **liuhao1024**. Supplemental test, execution and review: **Zero × Youngseok Oh**. This report is local execution evidence; it does not claim GitHub CI, maintainer approval, a merged fix or independent reproduction by another contributor.
