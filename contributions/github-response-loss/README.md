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

## Observed on 2026-09-14

Two real response-loss attempts landed on opposite sides of the ambiguity.

The first executable run, `34800559567`, handed the entire create body to TLS and
exited 73 without reading a response. GitHub nevertheless committed the marker as
commit `6f2cf79f93060f33372a7ef1813459c3bdd3ed2b`, whose parent was exactly the
pre-request provider-branch head. An independent connector readback found the
expected marker bytes at blob `487ee944457d115dcb40fa05efb21effd5128b49`.
The workflow itself remained failed because its verifier fed GitHub's line-wrapped
Contents API base64 directly to strict `b64decode(validate=True)`. That was a
reader bug after provider state had already been found, not a provider-operation
failure. The failed run and its artifact remain failed history.

The correction removes whitespace from the Contents API's base64 representation
before strict alphabet validation and adds tests for wrapped and invalid base64.
Run `34800686200` then passed all seven standard-library tests and the full
provider experiment. Again the sender exited 73 with no HTTP response read. This
time the first provider lookup was 404 and the marker remained absent throughout
the 12-second observation window. Recovery therefore performed its one permitted
create-only retry; GitHub returned 201. Exact remote bytes were then recovered as
blob `47f60bb11bb4eff80489ef9130aba8309e7a8ca7`, with the single matching commit
`29e8975d172e53a48983a8a4a9c7104b98f1cb14` also equal to the provider branch
head at verification time.

These outcomes are intentionally not collapsed into "the send succeeded" or
"the send failed". In one real attempt the unread request had already committed;
in the other it was still absent long enough for the bounded retry to perform the
creation. **The provider-state lookup, not the missing client response, resolved
which action was appropriate.**

Successful run `34800686200` retained artifact `10331780989`, 2,554 bytes,
SHA-256 `9a69dcc85032cc096609a693caf1cf90fc61594d62df5bcbf9268b9988568044`.
Its four members passed ZIP CRC during readback: `observations.json`, the sender
pre-exit record, seven-test log, and probe log. The retained observation records
sender return code 73, first lookup 404, 27 provider lookups total, retry status
201, exact remote bytes, and the provider commit/blob identities above. Reading
that artifact is not another provider experiment.

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

The integration workflow uses the repository's already-proven pull-request shape.
It does not install MCP, LangGraph or other packages. Evidence files record the
sender exit point, provider lookups, recovered remote blob and commit SHA, and
whether a retry was needed. The token is never emitted to logs or artifacts.

Several staging attempts failed before jobs were created while this new workflow
was being activated. Those workflow-level failures are preserved as failures and
are not provider evidence. Once the definition matched the proven PR shape and
kept `runner.temp` inside step scope, the job instantiated normally.

## Claim boundary

The successful evidence establishes only this narrower statement: **after the
client fully handed a create request to TLS and deliberately read no HTTP response,
a new process could use GitHub's authoritative state to distinguish observed
provider outcomes and recover one exact synthetic marker without trusting a
client-side success flag.** In the measured retry case, the bounded lookup stayed
404 before the retry returned 201; in the earlier attempt, independent provider
history confirms that the unread request itself had committed.

It does not establish packet-level delivery timing, GitHub's internal commit point,
power-loss behavior, arbitrary API idempotency, external payment/message safety,
human authorization, or exactly-once semantics for providers without a comparable
state primitive. The sender's pre-exit record proves the local request-send point,
not that GitHub had committed before that instant.

The generic receipt contract remains at [`receipt-contract`](../receipt-contract/README.md).
New code uses the repository's [existing MIT terms](../../tools/evidence-mcp/LICENSE).
