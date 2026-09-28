# Repeated HTTP 401 evidence for Hermes PR #125991

**The follow-up preserves authentication classification for a second rejected tool call on the same SDK lifetime.** It is available as [commit b7e052c](https://github.com/YS-OH-CORE/hermes-agent/commit/b7e052c9034a08fb3211ec59b173b4507d236d4c), directly on WYSTAF's original head `5c727a6ccd298f310becf0f0656346b6797e17f1` for [PR #125991](https://github.com/NousResearch/hermes-agent/pull/125991). Original implementation credit remains with WYSTAF. The branch is prepared for review; adoption or merge is not established by this record.

## Problem and change

The PR routes a recorded HTTP 401 into authentication recovery when the SDK presents an opaque MCP error. Consuming that record previously assigned a new dictionary to `srv._http_rejection`. The live HTTP response hook still held the original dictionary, so another response could update an object the handler no longer read. This becomes visible when the anonymous fixture cannot refresh credentials and the SDK connection remains established.

The follow-up changes that assignment to `srv._http_rejection.clear()` and documents why dictionary identity matters. It also strengthens the existing two 401 E2E tests: three sequential calls, two injected rejections, authentication classification for both, and a successful third call. No new fixture or dependency is introduced. The complete addition is **two files, +26/−21 lines**. [Recorded candidate source and diff scope](candidate-source.json).

## What the experiment exercises

The existing test harness starts the real Hermes CLI, a fake model provider, and the repository's real MCP SDK server subprocess on loopback HTTP. The existing ASGI fixture records inbound JSON-RPC messages and injects HTTP 401 for the first two `tools/call` requests. Its third call reaches the SDK tool implementation and returns the fixture canary. The model provider supplies a deterministic three-call plan; no live model or external service participates. The recorded runtime is Python **3.14.7**, `mcp` **2.0.0**, and `httpx2` **2.7.0**. [Environment](environment.json), [frozen test](test_mcp_streamable_http.py).

The test requires exactly three server-observed calls and three tool results, matches the rejected request IDs to the first two calls, and rejects any later `initialize` or `server/discover`. That method-count guard protects the SDK connection lifetime being exercised; it does **not** measure TCP socket reuse. Successful OAuth refresh, concurrent requests, and remote authentication providers are outside this experiment.

## Initial local identical-test results

The same frozen test file was applied to inspected main, the unchanged PR runtime, and the candidate. Its SHA256 is `20a819856089fc837d71eb1da14809caa6a98b00e0bfb52e6738a8fd4c919ce2`, recorded before every run.

| Runtime | First / second rejected call | Third call | Pytest result |
| --- | --- | --- | --- |
| Inspected main `188a1a5efd098f067638032fea6e24c42d06178f` | Generic error / generic error | Canary success | **1 failed, 1 passed** |
| Original PR `5c727a6ccd298f310becf0f0656346b6797e17f1` | `needs_reauth` / generic error | Canary success | **1 failed, 1 passed** |
| Candidate published as `b7e052c9034a08fb3211ec59b173b4507d236d4c` | `needs_reauth` / `needs_reauth` | Canary success | **2 passed** |

Both candidate authentication payloads identify server `web`. Across all three runs, tool-call IDs were `[3, 4, 5]`, injected 401 IDs were `[3, 4]`, and subsequent initialization/discovery count was **0**. Full logs and observations: [main](main-red-02/), [original PR](original-pr-red-01/), [candidate](candidate-green-01/).

A later source-only check at main `d9d122a003633250d22f786bf3d2fa1b63d99e1d` found `mcp_tool_handlers.py`, `mcp_tool_errors.py`, and `mcp_tool_transport.py` text-identical to tested main `188a1a5`. That later revision was not rerun. [Relevance check](later-main-relevance.json).

The candidate additionally passed **12 existing authentication unit tests** and **one selected response-recorder test**, totaling **15 candidate passes** across the three runs. These initial runs were targeted local results; the fresh CI comparison is recorded separately below. [Authentication log](candidate-auth-unit-01/runner.log), [recorder log](candidate-recorder-01/runner.log).

An initial preparation attempt, [main-red-01](main-red-01/), exited 2 because the runner rejected the split `--basetemp` argument. Only the evidence driver's argument syntax was corrected to `--basetemp=...`; that attempt supplies no behavioral result. It remains alongside all five valid runs, including both expected failures.

## Fresh GitHub-hosted comparison

A subsequent [fresh PM CI run](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36406137404), completed on 2026-09-28 at 09:54:07 UTC, reproduced the original PR's **1 failed / 1 passed** E2E result and the unchanged candidate's **15 selected passes**. Both lanes used full checkouts with 16,210 tracked files and newly built environments from their committed PM dependency inputs, with caches disabled and zero file retries. This resolves the initial environment-reuse and omitted-working-path conditions for these selected tests.

The original job's green status means its strict negative-result check detected the specific second-401 failure; its actual test exit is still 1. [Complete fresh-CI methods, 32 retained receipt files, JUnit reports, HTTP logs, and launcher history](ci-36406137404/README.md).

## Initial local provenance and practical limits

Each run retains its command, exit status, timestamps, source hashes, working-tree patch, and complete runner output. Candidate tests ran on the original PR HEAD plus the recorded overlay. Publication verification confirms the published commit's parent, both file blobs, and complete candidate tree `c34aaae949e52215febdcf23dfabc8f34db382bd` match that tested state. [Publication verification](publication-verification.json).

Exact Git commits and tree identities were reconstructed and verified. Inspected main was fully materialized. Original-head and candidate working directories explicitly omitted **215 non-Python UI, build/install, documentation, and icon paths**; all Python files, the test runner, and `pm/lock.json` were present. This was sufficient for the executed Python checks, not complete UI/build validation. [Source provenance](source/exact-source-provenance.json), [omission manifest](source/omitted-paths.json).

The existing immutable PM-built virtual environment was reused through `HERMES_PYTHON`, without package installation or modification. This record does not claim a fresh installation from each revision's lockfile. Runs used the canonical `scripts/run_tests.sh`, one worker, and zero file retries. Exact invocations are in each run's `execution.json`; [run_validation.py](run_validation.py) records them. Its interpreter path is specific to the recorded workspace and must be adapted when reproducing elsewhere.

Full raw HTTP records and extracted SQLite tool rows are included. Pytest itself asserts the tool contents in the fake provider's **final real main request**. SQLite rows only corroborate those assertions; they are neither a reconstructed provider request nor a raw database archive. [The extractor](extract_observations.py) copies retained DB/WAL/SHM files to a temporary directory, queries that copy with SQLite URI `mode=ro`, and verifies original input hashes remain unchanged. It preserves raw rows, parses payloads with the existing helper's regex semantics, and states these limits in every `observations.json`.

AI-assisted analysis, code, verification, and writing were performed by Zero (ChatGPT) under Youngseok Oh's direction.

Zero × Youngseok Oh
