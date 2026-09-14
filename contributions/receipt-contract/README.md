# A minimal recoverable-effect contract

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

This is a small design artifact extracted from the measured
[`mcp-commit-gap`](../mcp-commit-gap/README.md) experiment. It does not rerun that
experiment and does not claim that MCP, LangGraph, or an arbitrary remote API
provides exactly-once effects.

## The boundary that matters

A client may know only that it sent a continuation. The server may already have
committed the effect even when the client has no checkpointed terminal result.
PR37 measured three application policies at that boundary:

* blind repeat duplicated the synthetic effect;
* a closed flag prevented duplication but could not recover the original success;
* a receipt bound to the original request returned the original result without
  another effect.

The reusable unit is therefore not "retry". It is **request identity + durable
outcome + replay rule**.

## Contract

For a recoverable operation, persist one record with these logical fields in the
same atomic commit as the effect whenever that is actually possible:

```text
operation_id      opaque stable identifier
request_digest    digest of canonical operation name + arguments + decision
status            committed | rejected
result            exact terminal result returned for committed operation
committed_at      server-side ordering/audit value
```

On continuation:

1. Look up `operation_id`.
2. If no record exists, validate the request and perform the operation.
3. Commit the effect and receipt atomically when they share a transaction domain.
4. If a record exists and `request_digest` matches, return the stored `result`.
5. If the identifier exists but the digest differs, reject the continuation.
6. The client checkpoints the returned result. If it dies before that checkpoint,
   it may repeat the continuation because the server replay rule is deterministic.

The digest is correspondence, not authorization. Authentication, expiry,
revocation, concurrency ownership and permission checks are separate requirements.
Canonicalization must be versioned and must not silently coerce values such as
JSON `true` and numeric `1` or strip meaningful whitespace.

## Failure matrix

| Server state after reconnect | Client action | Safe interpretation |
| --- | --- | --- |
| no receipt, operation known not to have happened | execute once | normal new execution |
| matching committed receipt | return stored result | recovery, not a new effect |
| same ID, different request digest | reject | possible stale/misbound continuation |
| closed marker but no stored result | do not invent success | effect may be known complete but result is unrecoverable |
| external effect status unknown | do not call this exactly-once | reconciliation or provider idempotency is required |

## Where this contract stops

If the actual effect occurs in another system and the local receipt is written
later, there is still a gap between those commits. The same is true when a remote
provider accepts a request but its response is lost. A production design then
needs a primitive from that system, such as an idempotency key with durable result
lookup, a transactional outbox/inbox, or explicit reconciliation against a stable
provider operation ID. Merely adding retries, a local `completed=true`, or a
client-side log does not close that gap.

This repository currently has measured evidence only for the local SQLite fixture
in PR37: three injected post-reply client exits, ten tool calls, and the three
policies above. Response loss before delivery, arbitrary power loss, machine
reboot, concurrent recovery, real authentication, and a separate external work
system remain unmeasured here. Keep those labels intact when reusing this pattern.

## Next useful experiment

Do not add another synthetic layer just to make the diagram larger. The next
meaningful test should attach this contract to a **specific real work system that
exposes a documented idempotency or operation-status primitive**, then inject a
response-loss/reconnect boundary and compare provider state with the client
checkpoint. Until such a target exists, this contract is the compact stopping
point for the generic branch.

New text uses the repository's [existing MIT terms](../../tools/evidence-mcp/LICENSE).
