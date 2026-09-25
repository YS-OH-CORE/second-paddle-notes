# Honcho write-boundary follow-up: source-selected unit probe

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

## Motivation

A new participant in Hermes issue #121935 explicitly referenced our earlier initialization/adoption check and proposed an invocation-scoped write-time gate that retains reads. This follow-up identifies concrete existing persistence entry points; it is not implementation of that proposed feature.

Discussion: https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5828279986

We found relevant existing proposals before building: #73935 distinguishes automatic persistence from explicit tool writes and includes startup migration; #117358 proposes disabling the provider by session source, which also removes its reads. These are other authors' work and are not asserted to be merged. We do not open a competing PR or change the default meaning of saveMessages.

## Frozen scope

Pin current upstream source to 7b761da2de4979e424510ca7022bf9527aa65b68. Check exact Git blobs for the provider and migration file before any execution. Select 13 method bodies from HonchoMemoryProvider and the existing SessionMigrationMixin method by AST; execute them without editing the method bodies. The containing class, imports, state, manager, SDK endpoints, sanitization, session-key resolution and thread scheduling are fixture substitutes. This is NOT a complete package/CLI/live SDK integration test.

Run 14 cases with saveMessages=false and again with true: turn synchronization, automatic profile mirroring, end-session flush, explicit conclusion creation/deletion, card write, conclusion list/card read, cold owner initialization, warm initialization, per-session initialization, nonowner initialization, invalid conclusion input and bot-author refusal. Preserve event-level counts and return values, not just an overall success bit.

Expected from the reviewed current source: false suppresses the three automatic hooks tested, but explicit mutating tool calls reach their respective manager methods. Cold owner initialization with existing nonempty synthetic MEMORY.md/USER.md/SOUL.md and a blank per-directory session reaches three fake upload_file calls even with false. Warm, per-session and nonowner controls omit those uploads. Read tools remain callable and existing invalid-input/bot-write refusals remain effective.

Explicit tool writes are not labelled bugs merely for bypassing saveMessages: #73935 expressly preserves them. They are acceptance-test inputs for a distinct strict read-only invocation policy. Startup migration needs consideration separately from the per-turn sync hook. Session/peer creation metadata writes, delayed queues, shared-manager concurrency, shutdown, every other provider and complete read-only guarantees are out of scope.

## Execution and provenance

One bounded ordinary GitHub CPU job; standard-library Python only. Source downloads occur before a subprocess that denies Python socket connection and DNS calls. Only synthetic temporary memory files are read. No model, Honcho endpoint, token, user profile or real user history is used. A setup failure must be retained and never counted as a behavioral observation. Output retains source identities, selected line ranges, per-case events, script, logs, Python version and the upstream license.

After checking the actual output, report only the useful contract distinction and related work to the existing issue. No claim of maintainer agreement, uptake or endorsement follows from successful execution.
