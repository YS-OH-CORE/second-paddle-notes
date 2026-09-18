# MCP #505: separately maintained Go SDK compatibility check

Research direction: Youngseok Oh. Test implementation: Zero (ChatGPT).

Status at creation: **not yet executed**. A published script is not a passing result.

This follows the already tested patch in ../mcp-request-state-505. Its bytes are
fixed by SHA-256 and will not be changed to obtain a passing Go result.

The verifier builds the official Go SDK conformance server at
fbd36cb7870176bfc3e8e423df697cf110d0f927, then runs the original conformance CLI at
7169291ec0b68eb370fddcd9947313ab0d5e4156 before and after that same patch.
The unmodified server is the positive control. Three explicitly synthetic
negative controls alter only its diagnostic request-state handler: missing
marker, tool-error result, and tool error retaining the marker. The Go SDK
library and its real HTTP transport are not replaced, extracted or mocked.
Two adjacent scenarios use the unchanged server. No model or user account is
called. These are authored cross-implementation tests, not an independent review
or observations of faults in an unmodified Go SDK.

Run on NEW disposable checkouts only:

```
python -B verify_go_sdk.py --conformance /tmp/conformance --go-sdk /tmp/go-sdk \
  --patch ../mcp-request-state-505/request-state-505.patch --out /tmp/go-sdk-evidence
```

Requires Node22.16.0, Go1.25.0, npm and git. Downloads public pinned dependencies.
The included workflow uses a public standard runner, contents:read, no persisted
checkout credentials or uploaded caches, and a15-minute ceiling. Only small
source/log artifacts are retained for1day; executables and dependencies stay out
of artifacts. Main, the prior executed patch and other research are unchanged.
No upstream submission is implied by this author's verification branch.

New authored verifier code is offered under Apache-2.0, following the existing
MCP contribution terms. Original Go SDK files retain their MIT notices; pinned
license texts are preserved with the results. Every source modification is a
synthetic test-fixture mutation recorded as such, not a proposed Go SDK repair.
