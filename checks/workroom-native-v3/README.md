# Workroom v3: isolated native storage verification

This branch is development/test staging, not an application release or a production deployment.

`store.js` is the unchanged persistence module from the neutral offline Workroom v3. Its SHA-256 must be `a76ab457f4a83a1109235b8f92afc4458f3f99ec15de3b3350bde3a7dfb518e3` before testing.

`native_store_check.py` serves that module on a temporary loopback server, with real Chromium `localStorage`, real `navigator.locks`, two pages, and a persistent profile reopened after closing the browser process. The engine argument is an explicitly reduced synthetic contract fixture. This is NOT the application's full validation engine or UI, and does not establish iPhone, Safari, file-URL, operating-system-reboot, or deployed-service behavior. A passing module check must not be reported as a passing full-application check.

The three `neutral.part*.b64` files are an earlier attempt to stage the neutral whole-app HTML. **Their combined transmission failed validation:** the completed run reported a zlib decompression error. They are retained as failed staging evidence, never used for execution. Do not execute or distribute their decoded output. The intended neutral HTML SHA-256 was `d77842b2c229c75d3a47bc6c90a6a23e17b35733c26dc7f9ac4a433b48c2a7bd`. The local original application was not changed. Full-application native testing remains unexecuted.

Only neutral program material and newly authored synthetic test data are in these added files. No private core, conversation, identity information, private HTML, or user backup is included.

The one-shot workflow uses a standard public-repository Ubuntu runner, a short timeout, no requested token write permissions, no referenced secrets, no model calls, no deployment, no artifact-upload or cache action, and no recurring trigger. Its test result is printed to the job log. A workflow being queued or completed is not evidence of success; inspect the result and source digest.

## Observed run, 22 September 2026 Korea time

[Run 35631599778](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35631599778), job `106438856893`, executed commit `f4697e6015926e2e8d564cbe83814d2cfb713564`. The job started at 2026-09-21T17:22:35Z and completed at 17:23:02Z. Its returned `ZERO_NATIVE_STORE_RESULT` has `success=true` and 24 passing SOFTWARE checks, including source identity and environment checks. This is one development execution, not 24 independent experiments.

The inspected log confirms the expected source hash, native Storage and Web Locks on the loopback origin, cross-page storage notification, stale-write rejection, rejection while a real lock is held, successful retry after release, a single committed winner from two concurrent writers, exact synthetic text after closing and reopening the browser with the same profile, isolation of a separate profile, deletion-tombstone behavior, read-only legacy handling, and preservation of a corrupt pre-existing value. No page errors or unexpected page requests were observed in this fixture. The browser identified as HeadlessChrome/152.0.0.0 on Linux.

The result explicitly records `full_app_ui_tested=false`, `full_engine_validation_tested=false`, `ios_tested=false`, `os_reboot_tested=false`, and `file_url_tested=false`. It also records the separate failed full-app transmission. These limits are part of the result, not exclusions from an advertised full-app pass.

Problem direction: Youngseok Oh. Implementation and verification assistance: Zero (ChatGPT). This is author-run software testing, not independent expert review.
