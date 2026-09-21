# Workroom v3: isolated native storage verification

This branch is development/test staging, not an application release or a production deployment.

`store.js` is the unchanged persistence module from the neutral offline Workroom v3. Its SHA-256 must be `a76ab457f4a83a1109235b8f92afc4458f3f99ec15de3b3350bde3a7dfb518e3` before testing.

`native_store_check.py` serves that module on a temporary loopback server, with real Chromium `localStorage`, real `navigator.locks`, two pages, and a persistent profile reopened after closing the browser process. The engine argument is an explicitly reduced synthetic contract fixture. This is NOT the application's full validation engine or UI, and does not establish iPhone, Safari, file-URL, operating-system-reboot, or deployed-service behavior. A passing module check must not be reported as a passing full-application check.

The three `neutral.part*.b64` files are an earlier attempt to stage the neutral whole-app HTML. Their transfer has NOT been verified. Do not execute or distribute their decoded output. The test reports their decode/hash status separately and never executes that output. The intended neutral HTML SHA-256 is `d77842b2c229c75d3a47bc6c90a6a23e17b35733c26dc7f9ac4a433b48c2a7bd`.

Only neutral program material and newly authored synthetic test data are in these added files. No private core, conversation, identity information, private HTML, or user backup is included.

The one-shot workflow uses a standard public-repository Ubuntu runner, a short timeout, no repository token permissions, no secrets, no model calls, no deployment, no uploaded artifacts or caches, and no recurring trigger. Its test result is printed to the job log. A workflow being queued or completed is not evidence of success; inspect the result and source digest.

Problem direction: Youngseok Oh. Implementation and verification assistance: Zero (ChatGPT). This is author-run software testing, not independent expert review.
