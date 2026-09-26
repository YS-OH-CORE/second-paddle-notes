# Signal: opposite settings remain separate across overlapping tasks

Youngseok Oh × Zero | 26 September 2026

**No new defect was found in the tested PR path.** On the exact submitted Hermes PR #122033 head, two overlapping asyncio tasks using Hermes's context-local home override each retained their own opposite Note-to-Self setting in all four selected scenarios. A deliberately incorrect embedding-host wrapper using the shared process environment instead produced cross-task configuration contamination, which the same checker detected.

This is supplemental review of [Halldrix's submitted integration](https://github.com/NousResearch/hermes-agent/pull/122033). The feature implementation and initial tests belong to ren2140eth; Halldrix supplied the upstream integration and expanded tests. Their production code was not changed. Our earlier source guidance is recorded in the linked issue; this work adds a narrowly bounded overlap check, not ownership of their patch or a new general concurrency mechanism.

## Actual results

Pinned head: `bb8f14060ae63968c5d34ca5024dbce7fea93001`.
Signal source Git blob: `3fa045195ab48f1ed2fc4987f9164123a70afc9e`.

Profile A disables Note to Self. Profile B leaves the default enabled. The same synthetic self-message carries an attachment marker; no attachment is fetched from a service.

| Scope mechanism used by our host harness | Both profiles behave correctly | Observed behavior |
|---|---:|---|
| Existing context-local home override | 4/4 paired scenarios | A reads A, dispatches 0 and calls the attachment collector 0 times. B reads B and calls each callback once. |
| Deliberately shared HERMES_HOME environment | 0/4 paired scenarios | Both tasks read whichever home was assigned last. AB order enables both; BA order disables both. |

The four scenarios cross literal/quoted false with AB/BA task start order. Each contains two tasks. Three barriers force overlapping scope lifetimes: both scopes are set before loading, both adapters exist before handling, and both handlers finish before resetting scopes. The event trace checks these phase boundaries directly. This is one deterministic execution of each case, not random-load testing or a statistical estimate of race frequency.

The PR's **13 option tests also passed unmodified** on Python 3.14.7, with zero failures, errors or skips. We used explicit pytest-asyncio, disabled plugin autoload, and `--noconftest`. This excludes upstream conftest fixtures and is not the project's full CI invocation or a rerun of the author's 64-case suite.

The four negative-control failures are intentional observations of our deliberately bad host wrapper. They do not show that the submitted PR changes HERMES_HOME concurrently or contains that bug. The workflow succeeds only when the declared positive/negative matrix is observed.

## Why this is a different check

The submitted tests already cover sequential profile loading. Here two contexts remain active together while the real loader and separate adapters are used. Python supports context-local variables in asyncio, and the pinned `hermes_constants.py` explicitly provides a home override that does not mutate os.environ. We test that mechanism with the real configuration-to-adapter path; we are not claiming to have invented or repaired it.

Practical boundary: an embedding application should use the existing context-local API for overlapping tasks rather than temporarily rewriting process-global HERMES_HOME. A successful sequential A/B/A check alone does not establish that the latter shared-environment approach works under overlap.

## Execution and limits

[Completed first workflow run 36218206150](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36218206150).

The entire pinned source checkout was fetched, and `load_gateway_config`, `SignalAdapter`, `_handle_envelope`, and the context functions were imported normally. No function extraction or replacement configuration loader was used. Each mode ran in a fresh interpreter with a clean allowlisted environment and scratch homes. YAML input files, production source and the original tests remained unchanged.

Final dispatch and attachment collection were AsyncMock observers. No live Signal account, real message, model turn, external attachment download or full gateway authorization was exercised. The actual adapters never connected a Signal client. Python socket connections and DNS were blocked in the measurement processes; no attempts were recorded. This is a Python guard, not an OS network sandbox.

The test is **overlapping event-loop tasks with one adapter per task**, not parallel threads, an installed multi-profile gateway host, live reload, cancellation recovery, or a claim about all secrets, memory stores and transport sessions. Synchronous loader construction still executes serially on the event loop. The guarantee tested is task-local identity across explicit yield boundaries.

Environment: Python 3.14.7, Pydantic 2.13.4, PyYAML 6.0.3, httpx 0.28.1, pytest 8.4.2 and pytest-asyncio 1.2.0. Selected project dependencies came from the pinned pyproject; the complete transitive environment is recorded, not assumed to equal the full project lockfile. A working-container source download failed DNS before any test; the bounded Actions runner acquired the source and executed the actual tests.

## Reuse and evidence

The adjacent [probe.py](probe.py) takes a full disposable checkout of the pinned PR, an output directory that does not exist, and one of two modes. Run in a fresh environment with synthetic Signal variables, a scratch HOME/HERMES_HOME and the recorded dependencies. The exact [workflow](../../.github/workflows/signal-task-overlap-20260926.yml) provides the complete setup and commands. Never use an active user's deployment as the scratch checkout.

[Protocol](PROTOCOL.md) was committed before execution at `a3311dfbe693819e2d536035e67e923104fd652b`. Workflow commit: `a40d2f94e29fa3a45f4d65a163dd2371d4fca8ce`.

Raw artifact 10898158401, 112,720 bytes, SHA-256 `c1c67761589f21eb0dda88fcb89ef94d374c99192695a898ea04671bfca2adf4`, retains original source slices, unchanged test file, script, protocol, per-task observations, source and environment records, and execution logs. It is attached to the run with 30-day retention and preserved separately in the conversation bundle.

The local readback verified the archive digest, source/script Git blobs, original-test JUnit result, all eight logged paired-scenario rows, event barrier ordering, the per-task contracts and the combined summary. It did not rerun the Hermes modules and is not independent external replication. No maintainer approval or adoption of this new check is claimed.
