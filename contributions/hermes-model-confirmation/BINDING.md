# Request-owned confirmation patch proposal

This follows the reported PR22982 defect, rather than repeating its counterfactual
pre-dispatch clearing test. It is a two-production-module patch proposal against
`addb69bc409dae7d1c0ae9f2dc571fd4a39d8fc8`. No upstream change or installed update is
implied by this contribution. Authored with Zero (ChatGPT) for Youngseok Oh.

## Mechanism

The selection guard captures one fresh request-local token before registering its
confirmation. The existing slash-confirm registry binds that callback to its exact
`confirm_id`, expiry and single-resolution rule. The callback may consume only its
own token, never whatever text happens to be in the session stash at callback time.
An empty request still gets a distinct token: a new model-only approval cannot
inherit an earlier task. The existing conversation-reset cleanup can revoke the
token without another confirmation store or approval step.

The dispatcher no longer stages payloads after awaiting presentation, where a fast
approval or a later request could win the race. A completed direct switch clears
only its observed predecessor, not a newer confirmation created during an await.
Help/listing and a failed proposal do not attach their text to an older approval.
The guard keeps the exact payload supplied by the existing splitter, including
indentation and trailing whitespace; it does not claim byte preservation of the
entire incoming event before upstream splitting/normalization.

## Verification

`verify_binding.py` requires a clean disposable checkout of the exact PR head,
checks both source blobs, runs the unchanged nine original tests as a baseline,
and adds the two earlier replacement cases plus ten new binding cases. It records
original assertion failures before applying the new production patch. It then
requires all twelve cases, all nine unmodified PR tests and the existing generic
slash-confirm tests to pass. It records real import paths and per-case results.

The generated `confirmation_binding.patch` includes the two production modules
and both regression files. `production_binding.patch` includes only production
changes. The verifier checks reverse applicability against the actual tested tree.
The former `verify.py` is retained as historical counterfactual work; the existing
bounded PR/manual CI now invokes the request-binding verifier instead.

At this document's first commit, full-source CI has not yet completed. Do not treat
this proposal or workflow file as a successful test.

## Deliberate boundaries

Actual gateway and confirmation handlers are used with the PR author's existing
fixture doubles for model resolution, warning policy, adapters, storage facade and
final agent. Two presentation interleavings are forced with asyncio events. The
displaced/revoked callback cases directly invoke a retained callback to isolate
its guard; they do not claim normal registry resolution permits a stale ID.
The direct-switch cleanup test supplies a controlled handler result to isolate
that dispatch branch. No real provider, user conversation or platform is contacted.

This is not approval persistence, arbitrary thread-interleaving proof, a full
runtime deployment or changed native-button auto-routing. Accepted callbacks
already past the ownership check are not rolled back by later requests. The last
expired request token can remain inert in memory until replacement/reset; the
registry still prevents expired resolution. No new timing/permission policy,
credential, purchase, periodic schedule or private-source publication is added.
The existing upstream MIT notice applies to the proposed patch and tests.
