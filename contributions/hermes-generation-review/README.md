# Supplemental verification of Hermes PR107013

This is an additional check of another contributor's repair, **not a new implementation or a claim to have discovered its reported defects**. Production credit belongs to the PR author and the earlier reporters/reviewers in that thread. The checks were prepared with Zero (ChatGPT) for YS-OH-CORE.

Target: https://github.com/NousResearch/hermes-agent/pull/107013

- Parent: `2b1c0ae586e7bf4c51cc0cbe61eff4ec0190be03`
- Reviewed follow-up: `b2f009d4f289597a5eace6b9c7a169901c3a5af8`

## Actual question

Does delayed cleanup from an earlier generation preserve the successor's model choice and restore snapshot, while still releasing the old generation's own transcript lock? Does rotation retain the old lock-domain alias, and can a queued waiter then be cancelled without breaking ownership or future progress?

The displaced-lock case holds **two different real transcript leases at once**, then installs the successor in the same routing-key state. It tests old-lock release and successor preservation together, rather than merely releasing a single undisplaced token.

## Run

Provide two clean disposable checkouts of the exact revisions above and the ordinary Hermes test dependencies. Do not use a running installation or a private profile.

```sh
python verify.py --parent /path/to/parent --head /path/to/head --out /path/to/new-results
```

The verifier adds only the same new test file to each disposable checkout. It does not modify upstream implementation or the original author's test. It checks for source changes afterward. It records source hashes, assertion XML, stdout and eight per-case observation records. Only a completed verified report establishes the result; the presence of this directory does not.

The final comparison requires four deliberate assertion failures on the parent, four passes on the reviewed follow-up, and ten existing author tests passing. Import/setup errors or skipped tests do not satisfy the gate. These are selected regression cases, not observed production failure rates.

## First attempt and corrected test precondition

Run `34558532647` returned four parent failures, four follow-up passes and ten author-test passes. The verifier correctly refused completion because its original expected count was three parent failures and one pass. The fourth parent case raised `KeyError: parent` before running cancellation: the parent source's `rebind()` explicitly removed the old alias. That source was read and verified, not inferred from the failure alone.

The test now records and asserts old-alias retention **before** trying to queue/cancel its waiter. A parent failure at this point is an alias failure; it is not evidence that a cancelled waiter damaged the owner. The follow-up continues through actual asyncio cancellation and reacquisition. Existing production code, the first three assertions and original author tests were not changed. The first run is retained as an incomplete review attempt, not represented as a successful final verification.

## Boundaries

Real imported `GatewayRunner` state/restore/lease helpers and real single-event-loop asyncio locks; controlled in-memory state. Active-state persistence and cache eviction use recording functions. Restore calls follow each version's public signature. There is no actual gateway server, model, platform delivery, user database, OS-process interruption or complete outer-finalizer execution. No whole-PR approval, merge readiness, institutional independence or universal race-freedom is claimed.

The GitHub workflow is read-only, capped at five minutes, and triggered only by relevant pull requests or manual dispatch. It is not a standing agent or notification service. No private conversation or live account credential is part of the tests.

Reference for asyncio lock scope: https://docs.python.org/3/library/asyncio-sync.html#lock . Python's lock is single-event-loop, not an OS-thread lock; this test does not certify cross-thread ownership.
