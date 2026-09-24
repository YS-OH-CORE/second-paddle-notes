# LongMemEval-V2: reader failure boundary and cleanup

Youngseok Oh (오영석) × Zero (ChatGPT) | 2026-09-24

A bounded follow-up to [LongMemEval-V2 #7](https://github.com/xiaowu0162/LongMemEval-V2/issues/7). The original transport-failure report is **100yenadmin's** work; the outcome/status-contract proposal is **chengyixu's**. This contribution adds executable characterization of the current exception boundary and a cleanup-only candidate. It neither changes the leaderboard denominator nor implements their proposed outcome taxonomy.

## Executed, not merely inferred from source

Source: `xiaowu0162/LongMemEval-V2@2cc8c540bdb87fe6761629b585e727e1c4704520`.
Harness Git blob: `6a7182440a2cdd3ace6286dd966f7953fc383e8e`.

[Completed run 35966667542](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35966667542) · [fixed runner script](https://github.com/YS-OH-CORE/second-paddle-notes/blob/ac30f25c5c5433196f549e0ed76491f296fe814e/checks/lme-reader-cleanup/check_reader_failures.py) · [execution setup](https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbf69410cf23b76081e9318df6f69d8e206d4cee/.github/workflows/lme-reader-cleanup-20260924.yml) · [candidate patch](cleanup-only.patch)

The full unmodified harness was imported normally, including its declared memory-module dependencies. `create_async_client` was injected with an actual `AsyncOpenAI` instance over HTTPX MockTransport. Request construction, SDK error-class mapping, response extraction, parsing, and the harness's concurrent output function ran as written. This is not an AST-extracted substitute or a live provider experiment.

Resolved versions: OpenAI Python **2.54.0**, HTTPX **0.28.1**, tqdm **4.67.1**. The setup uses the repository's unpinned declared requirements with `openai<3` to target the HTTPX SDK lane; the complete resolved environment is retained. It is not a fully locked dependency installation or an SDK-3.x compatibility test.

## Observed exception matrix

| Simulated terminal outcome | Original output function | Original client closed on exit? | Cleanup candidate |
|---|---|---:|---|
| HTTP 200, `\boxed{OK}` | Returns parsed output | Yes | Identical output; closed |
| HTTP 200, empty content | Raises `RuntimeError` | No | Same exception; closed |
| HTTP 400 with an embedded origin-524 message | Returns empty response, zero usage, no `reader_status` field | Yes | Identical output; closed |
| Actual HTTP 524 | Raises `InternalServerError` | No | Same exception; closed |
| Read timeout | Raises `APITimeoutError` | No | Same exception; closed |
| HTTP 429 | Raises `RateLimitError` | No | Same exception; closed |
| HTTP 524 beside a still-pending request | Raises; one sibling task still pending | No | Same exception; sibling cancelled/awaited; closed |

Seven scenarios were run once per source condition: **14 bounded invocations**, not 14 independent real-world incidents. Every row's returned output or escaping exception type was unchanged by the candidate. The mixed scenario issued two simulated requests in each condition; all single scenarios issued one each.

The original issue explicitly described an origin timeout surfaced to the client as a 4xx. The HTTP-400 case corroborates that narrower path. A native 5xx or client timeout takes a different path in this revision: it escapes rather than returning an empty answer. A successful empty response also escapes, through the explicit non-empty-text assertion. Do not generalize the caught-400 behavior to every provider failure.

**Retry boundary:** the upstream constant is 10. The injected fixture sets `max_retries=0` deliberately, to exercise terminal error classification without retry delays. We did not run an exhausted ten-retry sequence or reproduce the reporter's service. No extra retry loop is proposed.

## Cleanup-only candidate

The [small patch](cleanup-only.patch) wraps the output loop in `try/finally`, cancels unfinished sibling tasks, awaits all task outcomes with `return_exceptions=True`, and closes the client. It preserves existing success and exception semantics. In the mixed fixture the original leaves one child pending at the measured function exit; the candidate leaves zero and closes the client. The fixture itself cleans up after measuring the original, so no unfinished task is left by the test.

This candidate intentionally does **not** classify failed requests as `instrument_failed`, repair the model-empty path, retain partial successful outputs after a raised exception, alter score denominators, change retry policy, or adjudicate leaderboard rules. Repeated cancellation during cleanup, failures from `client.close()`, real sockets and provider billing are not tested. It is a narrow tested candidate for maintainer review, not a complete fix for #7 or an adopted upstream patch.

## Failed setup retained

[First run 35966526910](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35966526910) failed at module import because I initially installed only the SDK, HTTPX and tqdm. The harness eagerly imports its Agents SDK memory backend. That run made **no scenario observations** and did not apply the candidate. The next setup installed the declared dependencies and CPU-only PyTorch; the same runner script and assertions then completed. No package module was stubbed out to make the import pass.

## Raw evidence and scope

[Original successful archive](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35966667542/artifacts/10794741060) contains the script, exact generated patch, all 14 observations, environment, metadata and execution log. SHA-256: `b27a8b8c055a0ef14cb979c62e2bad7e95648f28be8a32582b0e6cc9a6c9c3f6`. A byte-identical archive was retrieved and inspected in the authoring environment. That is a separate readback, not external replication. Actions retention is seven days; the author-side copy is retained separately.

No model calls, private histories, live service requests, user-PC actions, paid endpoint or GPU were used. Public source/dependencies were downloaded during setup; real socket connections were blocked during the synthetic scenarios. The disposable source file was restored byte-for-byte afterward. This Python socket guard is not an OS sandbox.

Original research and implementation stay attributed to the LongMemEval-V2 authors and original issue contributors. New fixture, candidate, execution and analysis: Zero (ChatGPT), for Youngseok Oh / YS-OH-CORE. No institutional endorsement or external acceptance is claimed.
