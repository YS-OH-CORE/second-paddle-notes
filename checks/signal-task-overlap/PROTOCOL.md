# Signal profile scopes during overlapping asyncio tasks

Youngseok Oh x Zero | 26 September 2026

## Question and attribution

The externally authored Hermes PR 122033 adds a Note-to-Self-only switch. Its 13 new tests include sequential profile loading. This supplementary check asks whether two overlapping asyncio tasks, each using Hermes's existing context-local home override and its own adapter, continue to read their own opposite settings. It is not a request to redesign or take ownership of ren2140eth's implementation or Halldrix's integration.

Pinned PR head: bb8f14060ae63968c5d34ca5024dbce7fea93001 (Halldrix/hermes-agent). The Signal production blob must equal 3fa045195ab48f1ed2fc4987f9164123a70afc9e. No production edits are made. Ordinary imports load the real YAML loader, adapter and inbound handler from the entire checkout. No AST extraction or replacement loader is used.

## Finite design

Profile A disables Note to Self; profile B leaves it at the default. Use literal false and quoted false for A and both task start orders. Four paired scenarios, two tasks each. Barriers ensure both scopes have been entered before either loads configuration, both adapters exist before handling, and both handlers finish before contexts are reset. This is controlled event-loop interleaving, not simultaneous threads or random-load testing.

Measure resolved home before/after handling, constructed setting, dispatch count, attachment-collector calls, absence of an actual client, untouched YAML files and context restoration. Use synthetic envelopes and AsyncMock for final dispatch/attachment collection. No live Signal transport, full gateway authorization, model turn, credentials or real user data is used.

Repeat the same four scenarios with a deliberately BAD embedding-host wrapper that changes process-global HERMES_HOME from both tasks instead of using the context-local API. The final write remains until both handlers complete. This demonstrates whether the checker distinguishes cross-task config contamination; it is not a mutation of the PR or an allegation that the PR uses that wrapper.

Primary expectations: context-local mode satisfies both profiles in all four scenarios; the deliberately shared-environment wrapper does not. Retain contrary observations and setup errors rather than adjusting expected results. Also run the PR's 13 option tests unmodified as a narrow regression baseline. The original tests use --noconftest and explicit pytest-asyncio as in our earlier received-patch check; this is not the full upstream CI invocation or the 64-case suite claimed by the PR author.

## Execution boundary

Use the supported Python 3.14 line, an isolated venv, and selected exact dependencies from the pinned pyproject plus pinned test dependencies. Save the complete resolved environment. Limit to one eight-minute CPU workflow initially. Source/installation downloads happen before measurement. Python socket and DNS calls are denied during measurement. This is not an OS sandbox.

Each mode runs in a fresh interpreter with an allowlisted environment and new scratch HOME/HERMES_HOME. The repo source and selected original tests are hashed before and after. Do not touch a user's device or deployment and do not automatically submit a new PR. After readback, only a genuinely useful result may be offered to the existing discussion.

Background: Hermes's hermes_constants.py at this PR head explicitly exposes context-local overrides without changing os.environ. Python documents asyncio support for ContextVar: https://docs.python.org/3/library/contextvars.html#asyncio-support . This study checks their use with this real loader/adapter path; it is not the discovery of task-local context variables.
