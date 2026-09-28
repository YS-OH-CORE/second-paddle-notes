**Revalidated after your main merge (`ce962e0`, September 28 UTC):** [Refreshed follow-up `861f94d`](https://github.com/YS-OH-CORE/hermes-agent/commit/861f94dc4326b9de45fff009202b48415aadb9bc) reapplies the exact same two corrected file blobs directly on your new head. Its committed dependency inputs changed, so I repeated the comparison in two fresh PM environments rather than assume the earlier result still held. [Run 36481347946](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36481347946) gives **1 failed / 1 passed on the refreshed original runtime**, and **15 selected passes on the correction** (2 real-HTTP E2E + 13 unit), with zero errors, skips, or file retries. The original job is green only because the driver confirms the specific second-401 failure; the test exit remains 1. No test behavior or runtime repair was changed for this refresh. [Full receipts, source/lock comparison, and limits](https://github.com/YS-OH-CORE/second-paddle-notes/blob/98bf85621db123f0b3a85403d6af734013ec137d/checks/hermes-repeated-401-125991/ci-36481347946/README.md). This revalidation was AI-assisted.

I reproduced a remaining repeated-401 case on `5c727a6`: the first call is correctly classified, but the second becomes a generic MCP error on the same SDK session.

`_make_http_rejection_recorder` closes over the dictionary supplied when the owned HTTP client is created. `_take_recorded_401` replaces `srv._http_rejection` with a new dictionary, leaving that live hook writing into the old one. This is observable on the URL-only fixture when authentication recovery cannot refresh credentials and does not reconnect. Clearing the existing dictionary preserves both consumption and later recordings.

[Follow-up commit `b7e052c`](https://github.com/YS-OH-CORE/hermes-agent/commit/b7e052c9034a08fb3211ec59b173b4507d236d4c) is directly on your original `5c727a6` head. It changes that one runtime line to `.clear()`, adds its rationale, and strengthens the existing two E2E tests; your original commits are preserved.

Using the same frozen test with the real CLI, real MCP SDK HTTP fixture, and scripted model boundary:

| Runtime | First 401 | Second 401 | Third, healthy call | E2E |
| --- | --- | --- | --- | --- |
| Main `188a1a5` | Generic error | Generic error | Success | 1 failed, 1 passed |
| Your head `5c727a6` | `needs_reauth` | Generic error | Success | 1 failed, 1 passed |
| Follow-up `b7e052c` | `needs_reauth` | `needs_reauth` | Success | 2 passed |

The strengthened test matches the two injected rejection IDs, requires exactly three calls/results, and excludes `initialize`/`server/discover` after the first call, so replacing the SDK session cannot hide the broken recorder reference.

```sh
scripts/run_tests.sh --include-integration tests/e2e/core/mcp_plugins/test_mcp_streamable_http.py -k 401
```

The 12 existing auth tests and selected response-recorder test also passed: **15 targeted candidate passes**, on Linux / Python 3.14.7 / `mcp==2.0.0` / `httpx2==2.7.0`. [Complete commands, failures, observations, source provenance, and environment limitations](https://github.com/YS-OH-CORE/second-paddle-notes/tree/8fdbd20689d2ca8c2b5475121795d4a1c3ff3593/checks/hermes-repeated-401-125991).

**Fresh CI follow-up (September 28):** [Run 36406137404](https://github.com/YS-OH-CORE/hermes-agent/actions/runs/36406137404) reproduced these results in separate GitHub-hosted jobs, each with a full checkout and a new PM `dev` + `test` environment built from the committed dependency inputs. The same frozen E2E test gives **1 failed / 1 passed on your unchanged runtime** and **2 passed on the follow-up**, with the 13 selected unit tests also passing: **15 candidate passes**, zero file retries, no errors or skips. The original job is green only because its strict check confirms the specific second-401 failure; the actual test exit remains 1. [Retained JUnit reports, raw HTTP logs, source/environment hashes, and full methods](https://github.com/YS-OH-CORE/second-paddle-notes/blob/6bc0b0b07187d8d326c874ee6c8a3338f87ec6b4/checks/hermes-repeated-401-125991/ci-36406137404/README.md).

This covers sequential calls on the existing SDK lifetime; concurrent request attribution remains outside this small correction.

Zero × Youngseok Oh
