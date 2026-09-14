# A published-file check completed through the Hermes tool path

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

PR45 checked a standalone GitHub reader. PR46 checked Hermes discovery/loading
and CLI help, but never sent the task through Hermes terminal. This bridge joins
those paths for a concrete task: check the already-published reader file against
its pre-recorded SHA-256. The old reader and skill folder remain unchanged.

## What runs

`run.py` makes a new disposable profile, copies the reviewed skill, imports the
unmodified pinned Hermes source, and dispatches `skills_list`, `skill_view`, a
supporting-file `skill_view`, and `terminal` through its actual tool registry.
The terminal command uses the returned skill directory, runs the original reader
and returns its JSON plus process exit code. There is no direct subprocess
fallback for the reader: a failed host-terminal call is a failed bridge.

The bridge preserves the four reader outcomes and their exit codes. It never
turns nonzero exit 2/3/4 into success, never authorizes a retry, and never submits
a GitHub write. The harness chooses the tool calls, not a language model.

The supported host revision is
`65a6b6831ef681da73955dd97a44f35794a2d4b9`. This is not an automatic installer or a
promise about other Hermes versions. Existing user profiles are never opened.

## A single authorized task

In an already prepared disposable environment with the pinned Hermes source and
workflow-listed dependencies:

```sh
python -B contributions/hermes-reconcile-task/run.py \
  --upstream /path/to/pinned/hermes-source \
  --skill skills/github-write-reconcile \
  --intent /path/to/prewrite-intent.json \
  --out /path/to/new-disposable-runtime
```

The intent uses the existing skill's five-field format. The default uses public
unauthenticated GETs. `--use-github-token` explicitly permits the existing
GITHUB_TOKEN to be offered to the host; host environment policy can withhold it
from the command. The first attempt below demonstrates that diagnostic. Never paste
a token into an intent or command. The successful hosted task uses public reads
without a token in its environment. The bridge
prints a task record and exits with the reader's 0/2/3/4 code. Its `status=completed`
means the host task returned a diagnostic; inspect nested `result.status` for
content match, conflict, snapshot absence or unknown.

`--out` must not exist or lie inside either source directory. Profile/config,
copied skill, temp and host logs are confined to that newly created runtime.
The bridge is a controlled integration utility, not a production agent launcher.

## Check and controls

`exercise.py` selects four intents: the actual published reader; the same file
with a wrong digest; a path not delivered in that commit; and a malformed intent
using a boolean instead of version number 1. Each runs in a new host process.
The last three are controlled inputs, not new provider files or incidents.
Expected outcomes are match/0, conflict/2, absent/3 and unknown/4. The expected
reader hash comes from the original delivered local bytes, not the remote lookup.

The output preserves each original terminal envelope and its decoded reader
result, intent and bridge hashes, the copied skill manifest, host source hashes,
process identity and access observations. The actual hosted records below were
returned and inspected. Local preparation checked source/YAML/shell syntax only;
this session lacks Hermes and GitHub DNS. It did not perform a local host task.

## Boundaries

The host's Python audit hook denies direct host networking and writes outside the
new runtime and records subprocess launches without environment values. Those
hooks do not propagate into a shell's child Python interpreter. The reviewed
unchanged reader uses its own GET-only fixed-host transport. This is not an OS
sandbox or an independent network attestation. Source/dependency acquisition
occurs before the guarded host task. Host guards are not monkeypatched, forced
through, or replaced with stand-ins.

Only explicit diagnostic JSON/log files are uploaded; synthetic profile/.env/
terminal-cache state is excluded. Unrelated plugin warnings stay in logs; this
lean import environment is not a full conversational Hermes installation.
No model selection/generation, paid API, write retry, user-PC change, installation
into an existing profile, provider marker, upstream modification, release or
recurring task is involved. Existing PR45/46 results are not recounted as new work.

Sources: pinned [Hermes terminal handler][terminal], [local execution backend][local]
and the [delivered skill](../../skills/github-write-reconcile/README.md).
New code uses the repository's [existing MIT license](../../tools/evidence-mcp/LICENSE).

[terminal]: https://github.com/NousResearch/hermes-agent/blob/65a6b6831ef681da73955dd97a44f35794a2d4b9/tools/terminal_tool.py
[local]: https://github.com/NousResearch/hermes-agent/blob/65a6b6831ef681da73955dd97a44f35794a2d4b9/tools/environments/local.py


## Observed execution, 2026-09-14

[Run 34805870635](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34805870635)
passed at executable head `0e95f8493c6df881059c12e9add6894bfbebd6de`.
Four separate host processes used the real registered loading and terminal paths:

| Task/input | Reader status | Host terminal exit | Public GETs |
| --- | --- | ---: | ---: |
| Published reader file vs its original digest | content_match | 0 | 3 |
| Same file, deliberately wrong digest | content_conflict | 2 | 3 |
| Undelivered path at the fixed commit | absent_at_snapshot | 3 | 2 |
| Invalid boolean version in intent | unknown / INTENT_VERSION | 4 | 0 |

The new result is the joined host-to-provider task path: sixteen registry calls,
including four terminal calls, and eight public unauthenticated GET requests.
No LLM selected these calls, no provider record was created, and prior fault
experiments were not rerun. The published file matched all 9,450 original bytes,
Git blob `c9818b4fc07cd2501bddf16868b86d29a86047ff`, at repository snapshot
`1f2b59be45c29ac70ebf3e8b5b0879708c93bbb1`.

All four raw terminal envelopes had `error=null`, including the nonzero outcomes.
That describes the terminal invocation, not file correspondence. The bridge reads
both `exit_code` and the nested reader JSON; conflict, absence and unknown remain
2, 3 and 4, and `retry_authorized=false` stays intact. This is documented host
semantics to consume correctly, not a newly claimed upstream bug.

Original artifact `10332674521`: 98,256 bytes, 23 JSON/log members, SHA-256
`9e2a820fd965f6456848fa3ad91e2c7b96f4a77b375468246ba57a12b70f9455`.
Downloaded readback checked CRC, separate records against summary, the exact
loaded document/reader, four distinct ordered host lifetimes, original terminal
envelopes, exit/status pairs, request counts, intent/source hashes and unchanged
12-file skill manifests. All four host logs were empty; no direct-host network
attempt or denied outside write was recorded. Each recorded two bash launches.
The imported source map included the actual terminal handler and local backend.
This is not OS-level child auditing, a full plugin-health test or certification.

Executed bridge: 10,319 bytes, Git blob
`6c2eba705c43943282f20c14253d75f9a34e3ce1`, SHA-256
`50f09929d9ba36c24e32647ee1369b7903fcfb8396e783113ab1bd331e7d96b0`.
Its recorded hash matched the prepared and uploaded source. The original archive,
offline inspector and corresponding source snapshot are supplied in the chat
bundle. Archive inspection is not another host/provider execution. Actions
retention is 14 days; keep the source-and-evidence bundle for later readback.

## First attempt: preserve the credential boundary

Run `34805693315` reached real Hermes terminal execution, but its command returned
`unknown / TOKEN_NOT_SET`, exit 4. The ephemeral read-only token was supplied to
the host, not available to the reader child. Its original artifact `10332868902`
remains a failed suite: 24,079 bytes, SHA-256
`52969e993d620180fef2399e13994ebe6c81473d58b85610aa3925196c3797aa`.
The task record was complete as a diagnostic, but it was not the required
published-file match. The suite did not execute its remaining three inputs.

The target is public, so only the exercise's unnecessary authentication flag and
workflow token environment were removed. The bridge, reader, host source and
credential/approval guards were not modified or bypassed. The next run used the
reader's existing public-read default and passed. No credential was inspected,
printed, force-forwarded or saved to a user profile. After the successful head,
only this README completion note changed.
