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
GITHUB_TOKEN to reach the read-only reader. Never paste a token into an intent or
command. The hosted check uses only the job's contents:read token. The bridge
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
process identity and access observations. A new hosted result is not claimed
until these records are returned and inspected. Local preparation only checks
source/YAML/shell syntax because this session lacks Hermes and GitHub DNS.

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
