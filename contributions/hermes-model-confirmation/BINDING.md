# Proposed confirmation-owned inline requests

A follow-up implementation to the reviewed stale-request defect in Hermes
PR22982 at `addb69bc409dae7d1c0ae9f2dc571fd4a39d8fc8`.
This is a proposal in our contribution repository, not an upstream merge or an
installed Hermes update. Prepared with Zero (ChatGPT) for YS-OH-CORE.

## Mechanism

The proposal removes the separate session-keyed inline-payload stash. The
request's payload is passed as an optional keyword through the model handler
into the guard callback. The existing slash-confirm registry already binds that
callback to a confirmation ID, supersedes old entries, checks expiry and pops
before resolving. The callback captures only its own immutable request text.
It cannot retrieve a later request's text from a shared session slot.

A successful direct model switch retires its previously pending model
confirmation by exact ID. `slash_confirm.clear` gains an optional ID checked
under its existing lock, while its original one-argument behavior is retained.
A different confirmation registered meanwhile is not cleared. Merely opening
model help does not discard an existing pending task. Whitespace within an
inline task is not stripped again when it passes through approval.

The reset funnel already clears the real slash-confirm registry. The proposal
removes the now-unused stash entry from the conversation-scope list. Existing
nine test scenarios remain, but representation-specific stash assertions are
replaced; the reset test now uses actual pending registry entries and callbacks
rather than a manually populated shadow dictionary.

## Execution and publication status

`build_binding_patch.py` prepares the production/test diff only in the disposable
checkout selected and verified by `verify_binding.py`. Do not run the builder
standalone on an installed Hermes or a worktree with user edits.

The verifier requires the exact PR head and original source blob identities,
first runs the original nine tests, then fourteen new behavioral cases on the
original source. These must reach assertions rather than fail collection. It
then applies the proposal, reruns the same cases and adapted existing cases,
checks the original slash-confirm suite, and separately verifies ID-conditional
clear. It writes the actual six-file patch and per-case observations into its
returned artifact. Results are pending until a completed run is inspected.

This uses the original PR's fixture doubles for model resolution, policy-warning
responses, storage facade, transports and final agent. Dispatch, confirmation
registration/resolution and lifecycle methods are the imported PR code. Two
controlled same-event-loop interleavings delay an old handler's return until a
new confirmation exists. They are not an exhaustive cross-thread proof or a
running messaging gateway. No real model, platform send, private profile,
remote command, installed application or persistent approval store is involved.

Expiry/cancellation/reset prevent later registry resolution. This does not
revoke an already resolved callback or undo work already in flight. Native
button delivery remains at the original PR's scope. Full provider/platform and
private-subclass compatibility remain for the maintainer to assess.

The original reproduction and narrow counterfactual verifier remain unchanged
as historical evidence. The existing read-only workflow is redirected to this
follow-up, with the same five-minute limit and no periodic schedule. The
existing upstream MIT notice applies to the proposed patch and tests.

Reference for the controlled coroutine tests:
https://docs.python.org/3/library/asyncio-sync.html#event
