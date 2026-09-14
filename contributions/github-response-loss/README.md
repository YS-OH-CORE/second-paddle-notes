# Lose a real provider response, then recover from provider state

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

PR38 stopped the generic branch and required a real work system with a stable
provider-side state primitive. This experiment uses **GitHub itself**. It does not
pretend that a local receipt makes an unrelated remote effect atomic.

## Provider operation

The workflow creates one deterministic JSON marker through GitHub's Contents API
on a dedicated same-repository fixture branch. The sender writes the complete
HTTPS request body and then exits with code 73 **without calling `getresponse()`**.
The parent therefore has no HTTP status, response body, or commit SHA from that
request.

A fresh recovery path asks GitHub for the marker and its commit history. If the
marker exists, its exact bytes and Git blob identity must match. If it stays absent
for the bounded observation window, recovery may issue the same create-only
operation once and then read provider state again. A late first request cannot
create a second file at the same path; GitHub will either expose the one marker or
reject the colliding create. The final evidence requires one matching provider
commit and exact marker bytes.

This is a provider-specific recovery recipe, not a proof of general exactly-once
remote effects. The primitive here is a unique repository path plus authoritative
GET/commit history. Another provider needs its own documented idempotency key or
operation-status lookup.

## Why a separate fixture branch

The provider effect is intentionally not written to the pull-request head. The
workflow targets `zero/github-response-loss-provider-20260914`, so its own test
write cannot recursively retrigger the PR workflow or change the reviewed source
while it is executing. The marker contains only synthetic identifiers, repository
name, branch, run IDs and the branch head observed before the request. No user
content or private checkpoint is stored.

## Reproduce in this repository

The hosted job is the integration test because it needs a short-lived GitHub job
token with `contents: write` on this repository. Local checks need only Python:

```sh
(cd contributions/github-response-loss && python -S -m unittest -v test_probe)
```

The integration workflow is bounded to this same repository and named PR branch.
It does not install MCP, LangGraph or other packages. Evidence files record the
sender exit point, the provider lookups, the recovered remote blob and commit SHA,
and whether a retry was needed. The token is never emitted to logs or artifacts.

## Claim boundary

A successful run establishes only this narrower statement: **after the client
fully handed a create request to TLS and deliberately read no HTTP response, a
new process could determine the outcome from GitHub's authoritative state and
recover one exact synthetic marker without trusting a client-side success flag.**

It does not establish packet-level delivery timing, GitHub's internal commit point,
power-loss behavior, arbitrary API idempotency, external payment/message safety,
human authorization, or exactly-once semantics for providers without a comparable
state primitive. The sender's pre-exit record proves the local request-send point,
not that GitHub had committed before that instant.

The generic receipt contract remains at [`receipt-contract`](../receipt-contract/README.md).
New code uses the repository's [existing MIT terms](../../tools/evidence-mcp/LICENSE).
