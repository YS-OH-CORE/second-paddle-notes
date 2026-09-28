# Revalidation after Hermes #125991 merged current main

The original PR advanced from `5c727a6ccd298f310becf0f0656346b6797e17f1` to WYSTAF's merge head `ce962e05ad9acbfa75f506da7b635236a96d733a`. The affected handler and original E2E test were byte-identical, but `pyproject.toml`, `uv.lock`, and `pm/lock.json` changed. This follow-up checks the already-proposed correction against that refreshed source and its own committed dependency inputs. It is not a newly discovered bug or a second upstream PR.

**Observed:** the refreshed original runtime still loses the second 401's authentication classification. The unchanged two-file correction, reapplied directly on that head as [861f94d](https://github.com/YS-OH-CORE/hermes-agent/commit/861f94dc4326b9de45fff009202b48415aadb9bc), passes all 15 selected tests. [Completed comparison run 36481347946](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36481347946).

| Runtime | Real CLI / MCP HTTP E2E | Selected unit tests | Actual test exits |
| --- | --- | --- | --- |
| Refreshed PR head `ce962e0`, with the frozen regression test | 1 failed, 1 passed | Not run in this lane | 1 |
| Same head plus correction `861f94d` | 2 passed | 13 passed | All four invocations 0 |

No test errors or skips occurred. The original workflow job is green only because its driver verifies the specific negative result: the second response is `(None, None)` rather than `(True, 'web')`. The raw test failure and exit 1 remain in [original JUnit](original/e2e/junit.xml), [runner log](original/e2e/runner.log), and [execution receipt](original/e2e/execution.json). This is one new comparison, not a claim that the entire PR or full suite passed.

## What was preserved and checked

The new correction commit has the refreshed PR head as its sole parent and changes exactly the same two files as [the prior correction b7e052c](https://github.com/YS-OH-CORE/hermes-agent/commit/b7e052c9034a08fb3211ec59b173b4507d236d4c). Their corrected file blobs are unchanged: `tools/mcp_tool_handlers.py` = `7ada401398b5e8d1a2b25f635df7eb3df892ffc9`; the E2E file = `3fb8dccadb91a79c8655aadb9ea574349d67dfa9`. This retains WYSTAF's history and the existing `.clear()` repair rather than rewriting their implementation.

Both lanes use the same frozen E2E file, SHA-256 `20a819856089fc837d71eb1da14809caa6a98b00e0bfb52e6738a8fd4c919ce2`. It drives the real Hermes CLI and MCP SDK HTTP fixture with a scripted model boundary: two rejected calls, then a healthy third call. Both inbound logs show tool-call IDs `[3, 4, 5]`, rejection IDs `[3, 4]`, and no later `initialize` or `server/discover`. The passing candidate verifies both authentication results and the third-call canary, without replacing the SDK session to hide the recorder-reference bug.

The additional candidate gates comprise nine error-classification tests, three auth-handling tests, and one HTTP rejection-recorder test. [Candidate result](candidate/result.json) and [local receipt cross-check](receipt-review.json) distinguish their counts from the two real-HTTP E2E tests.

## Environment and reproducibility

Each lane used a separate GitHub-hosted Ubuntu job, all **16,588 tracked source files**, and a newly built PM `dev` + `test` environment. Tool, Python, and Node cache restoration was disabled. The committed lock check and environment build succeeded. `scripts/run_tests.sh` ran with one worker, zero file retries, and separate JUnit/basetemp destinations. Runtime checks require the exact commit, tree, expected test overlay, and no missing tracked files before and after execution.

Recorded versions in both lanes: Python 3.14.7, MCP 2.0.0, httpx2 2.7.0, pytest 9.1.1, and pytest-asyncio 1.3.0. Those selected versions remain the same as in the earlier comparison; changed dependency-file hashes alone are not a claim that every dependency version changed. [Old/new source comparison](source-comparison.json), [original environment](original/environment.json), and [candidate environment](candidate/environment.json).

The [workflow](workflow.yml) and [verification driver](driver.py) are copied from executed launcher `f5346e44f1e1c95b92060fa9c731cae7be99e62f`. Relative to the prior verified launcher, only the branch, runtime commit IDs, and corresponding tree IDs were changed. The runtime repair, frozen tests, selections, expected behavior checks, and PM build procedure were not changed.

The main command remains the project's canonical runner, with the explicit frozen test selection and environment prepared by the workflow:

```sh
scripts/run_tests.sh --jobs 1 --file-retries 0 --include-integration tests/e2e/core/mcp_plugins/test_mcp_streamable_http.py -k 'test_401_on_tools_call_is_reported_as_an_auth_failure or test_the_call_after_a_401_reaches_the_server'
```

Exact per-gate commands, exit codes, source hashes and environment inventories are retained in the receipt directories. A reader can replay the pinned workflow rather than infer an environment from this short command.

## Evidence, limitations, and attribution

All 32 uploaded text receipt files were downloaded without editing: ten from the original lane and 22 from the candidate lane. JUnit files and HTTP logs were parsed again locally to check the reported counts and event IDs. [Receipt manifest](file-manifest.json) records byte sizes, SHA-256 and Git blob identities for publication; it excludes itself and later delivery records. GitHub's artifact metadata is preserved separately. Its archive digests are publisher-reported, not independently recomputed ZIP checksums.

This validates sequential calls against the local HTTP fixture and the stated selected unit gates. It does not validate concurrent request attribution, successful OAuth refresh, an external provider, all MCP transports, the complete Hermes suite, GPU behavior or production deployment. No new upstream PR or issue is created for this refresh; it belongs with the existing #125991 handoff. Updating evidence does not mean the author has accepted the correction.

Original implementation: WYSTAF. The prior correction, its tests, this refreshed application, and verification record: **Zero × Youngseok Oh**. AI assistance was used for analysis, execution setup, evidence checking and reporting. Upstream-context material retains the accompanying [Hermes license](LICENSE.hermes).
