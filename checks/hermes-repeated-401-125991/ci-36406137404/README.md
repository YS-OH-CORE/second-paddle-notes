# Fresh PM comparison for the repeated MCP 401 correction

**The published correction reproduced its 15 selected passes in a fresh GitHub-hosted environment. The unchanged original PR runtime reproduced the specific second-401 failure.** [Workflow run 36406137404](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36406137404) completed on 2026-09-28 at 09:54:07 UTC.

This follows the [initial local evidence](../README.md) for [NousResearch/hermes-agent #125991](https://github.com/NousResearch/hermes-agent/pull/125991). It resolves two conditions of that initial execution: reuse of an existing PM environment and omission of 215 non-Python working-tree paths. The tested correction remains [b7e052c](https://github.com/YS-OH-CORE/hermes-agent/commit/b7e052c9034a08fb3211ec59b173b4507d236d4c), directly on WYSTAF's original PR head. This verification adds no runtime change, and it does not establish adoption or merge.

## Observed results

| Runtime | Focused real-HTTP E2E | Existing selected unit tests | Actual test exits |
| --- | --- | --- | --- |
| Original `5c727a6ccd298f310becf0f0656346b6797e17f1` | **1 failed, 1 passed** | Not run in this lane | E2E **1** |
| Candidate `b7e052c9034a08fb3211ec59b173b4507d236d4c` | **2 passed** | **9 error + 3 auth-handling + 1 recorder passed** | All four invocations **0** |

The original failure is `test_401_on_tools_call_is_reported_as_an_auth_failure`, at the assertion for the first two tool results. The observed pair is `[(True, 'web'), (None, None)]`; the expected pair is `[(True, 'web'), (True, 'web')]`. The next-call control passes, including the real fixture's third-call canary. The original runner exit remains 1 in [its execution receipt](original/e2e/execution.json) and [result](original/result.json).

The original workflow job is green because its verification driver requires that specific negative result: exactly the two named tests, one failure and one pass, no errors or skips, the expected failing test, and the second-result auth-classification mismatch. A green original job therefore means the regression was reproduced; it does not mean the original test passed. [Original JUnit](original/e2e/junit.xml), [complete runner output](original/e2e/runner.log).

The candidate has **15 passes, zero failures, zero errors, and zero skips** across four canonical-runner invocations. The E2E pair shares one fixture execution. Each unit file has its own JUnit destination, avoiding report overwrites. [Candidate result](candidate/result.json), [E2E](candidate/e2e/junit.xml), [errors](candidate/errors/junit.xml), [auth handling](candidate/handling/junit.xml), [recorder](candidate/recorder/junit.xml).

In both real-HTTP runs, the inbound log records tool-call IDs `[3, 4, 5]`, injected rejection IDs `[3, 4]`, and zero subsequent `initialize` or `server/discover` messages. [Original HTTP JSONL](original/e2e/http_inbound.jsonl), [candidate HTTP JSONL](candidate/e2e/http_inbound.jsonl). The passing candidate assertions establish authentication classification for both rejected calls and success of the third call. The method-count guard concerns SDK lifetime, not TCP socket reuse.

## Fresh environment and exact source

Each lane used a separate ordinary GitHub-hosted Ubuntu job, with an ordinary full checkout containing **16,210 tracked files**. The driver checked the exact commit and tree, absence of missing tracked files, and allowed working-tree changes before and after execution. The original runtime received only the frozen candidate test file. The candidate runtime had an empty tracked diff. [Original inputs](original/inputs.json), [original test overlay](original/working-tree.patch), [candidate inputs](candidate/inputs.json), [empty candidate patch](candidate/working-tree.patch).

Both lanes used the same frozen E2E file, SHA-256:

`20a819856089fc837d71eb1da14809caa6a98b00e0bfb52e6738a8fd4c919ce2`

The committed `pyproject.toml`, `uv.lock`, and `pm/lock.json` hashes match across lanes. The runtime's own `setup-pm` action installed its committed Python and Node toolchain, with tool, Python, and Node cache restores disabled. The workflow then ran:

```sh
"$HERMES_PYTHON" -m pm.build_env --source "$GITHUB_WORKSPACE" --check-lock
"$HERMES_PYTHON" -m pm.build_env --source "$GITHUB_WORKSPACE" \
  --out "$RUNNER_TEMP/hermes-mcp-test-env" --group dev --group test
```

The output path was new in each job. The build used frozen committed inputs, without `--resolve`, and the driver required that new environment's interpreter. Recorded versions include CPython **3.14.7**, `mcp` **2.0.0**, `httpx2` **2.7.0**, `pytest` **9.1.1**, and `pytest-asyncio` **1.3.0**. [Original environment](original/environment.json), [candidate environment](candidate/environment.json).

Every test command uses `scripts/run_tests.sh`, `--jobs 1`, `--file-retries 0`, and explicit per-invocation basetemp and JUnit paths. Exact arguments and exits are retained in each `execution.json`. Both jobs ran once, on workflow attempt 1. The original E2E stderr includes a local HTTP `ConnectionResetError`; it is retained in the complete output. It did not replace the expected assertion failure or cause a JUnit setup error.

## Launcher and retained receipts

The executed [workflow and driver](https://github.com/YS-OH-CORE/hermes-agent/tree/85c0020ec97e182a1451d96cbaf1404cc6c2acc8) are on a separate verification branch. Two ordinary Ubuntu jobs are bounded to 30 minutes each; repository token permissions are read-only, and the workflow has no deployment or repository mutation steps.

The initial create-only launcher `2d6dda3` produced no registered workflow or run in the recorded check. The trigger-only child `85c0020` was pushed to the same verification branch and started this run. The cause of the missing create event was not established. Neither launcher preparation nor static review is counted as a test execution. [Launch record](launch-record.json).

All **32 uploaded receipt files, 46,376 bytes**, are retained here with unchanged file bytes, including every test log, JUnit report, result, environment, input manifest, working-tree patch, workflow outcome, and both HTTP logs. [File SHA-256 manifest](receipt-file-manifest.json), [GitHub artifact metadata](artifacts.json), [transfer verification](transfer.json). GitHub's original ZIP digests describe its uploaded artifacts; the separate transfer digest describes a temporary repack used to copy their extracted contents. They are different archives.

This remains targeted sequential-call coverage with a local scripted model boundary and a real MCP SDK HTTP server. It does not cover successful OAuth refresh, concurrent request attribution, external authentication providers, the full test suite, or UI/build behavior merely because those source files were present.

Original implementation credit remains with WYSTAF. Zero (ChatGPT) assisted with the follow-up, verification, review, and writing under Youngseok Oh's direction.

Zero × Youngseok Oh
