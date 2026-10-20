# MCP conformance issue 505: actual-module and CLI verification

Research direction: Youngseok Oh; implementation and analysis with Zero (ChatGPT).

This is a focused follow-up to https://github.com/modelcontextprotocol/conformance/issues/505 . It is initially an unexecuted verification attempt, not a passing patch or maintainer approval.

`verify_upstream.py` requires a clean disposable checkout of upstream commit `7169291ec0b68eb370fddcd9947313ab0d5e4156` and checks four exact Git blob identities before modifying any checkout file. It adds eight cases to the existing negative-MRTR test and broken fixture, expects four targeted assertion failures before the source fix and zero after it, and drives the existing built CLI over loopback HTTP. It tests the unchanged bundled everything-server and three erroneous completion modes. It retains command logs, exact versions, check JSON, original and changed sources, and a candidate patch. No mock replaces sendRpc or the scenario/helper imports.

Important scope: the bundled everything-server loads the pinned SDK dependency, but MRTR follows its explicit stateless HTTP handler. This is not an independently supplied SDK implementation or real user traffic. Full-suite/typecheck/lint outcomes are reported separately. No whole-suite green claim follows merely from targeted success.

The candidate only changes the named request-state-complete predicate: tool `isError: true` cannot count as successful validation, and the fixture's documented `state-ok` text must be present. The marker is fixture-specific, not a normative requirement on all MCP servers, and does not prove genuine state validation by itself.

Execution is confined to a standard public Ubuntu runner, with contents:read, credential persistence disabled, no inference API, no billing settings, no cache upload, a15-minute job cap and small1-day evidence artifacts. Npm uses upstream's lockfile with lifecycle scripts disabled. Any process cleanup targets only process groups created for these disposable fixture runs. Existing main and Lean/threshold work are unchanged. The remote action is not an alternative route for earlier denied changes; it concerns this separately reported issue.

Local syntax validation was performed before upload. Only observed workflow results can establish further execution. Do not call this independent external review: the workflow and tests are authored in this collaboration.
