# Does Hermes actually load the delivered skill?

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

PR45 checked the standalone reader. This addition tests a different boundary:
the existing skill folder enters the real Hermes skill discovery and tool-registry
load path. It does not call a language model, write to GitHub through the skill,
repeat the response-loss experiment, or install into the user's profile.

## Host and scope

Pinned upstream: NousResearch/hermes-agent at
`65a6b6831ef681da73955dd97a44f35794a2d4b9`.
The probe imports the unmodified `tools.skills_tool` from that checkout and invokes
`registry.dispatch('skills_list', ...)` and `registry.dispatch('skill_view', ...)`.
It does not replace the discovery functions, frontmatter parser or tool handlers.
This is the real host skill subsystem, not a full running conversational agent.

Five separate Python processes check: an empty profile; the complete skill in a
fresh profile; that same profile reopened in another process; SKILL.md alone
without its supporting code; and an explicitly disabled copy in another profile.
All processes use one disposable HOME and four synthetic HERMES_HOME profiles
under the output directory, not the operator's profile. The reopened case reuses
only the full test profile. Environment variables are allowlisted
without tokens or model keys. The source skill and copied complete folders must
remain byte-identical.

The full/reopened cases must discover one matching skill, return its exact document,
list and return the unchanged reader script, and launch that copied script's
`--help` command successfully from the host-reported location. The empty/disabled
controls must not load it. The markdown-only control tests an important distinction:
a discoverable instruction document is not proof that its supporting command exists.

The harness chooses the calls and the `--help` command; no model chooses or executes
the skill. There is no external file reconciliation in this new test. PR45's
separate existing provider-read evidence remains where it is.

## Reproduce

Use Python 3.12 and a disposable environment with the pinned upstream checkout.
The five direct dependencies below use the versions in that checkout's project
metadata. This narrow import environment is not a full Hermes installation.

```sh
python -m venv /path/to/new-venv
/path/to/new-venv/bin/python -m pip install PyYAML==6.0.3 python-dotenv==1.2.2 rich==14.3.3 prompt_toolkit==3.0.52 Jinja2==3.1.6
/path/to/new-venv/bin/python -B contributions/hermes-skill-load/probe.py \
  --upstream /path/to/pinned/hermes-agent \
  --skill skills/github-write-reconcile --out /path/to/new-output
```

The output path must not already exist. The probe creates synthetic profiles and
leaves them there for inspection; the workflow artifact includes only explicit
JSON/log files outside those profiles. It does not upload .env files, usage state
or copied profile contents. The host may write its normal usage/cache metadata
inside the disposable profile.

Python audit hooks refuse network access during host loading, unexpected child
processes, and writes outside the sandbox (apart from the single observation
file). This is a test-process guard, not an OS-level isolation certificate.
Source downloads and dependency installation precede the guarded child exercises.
The CI job has contents:read, a six-minute limit, and a three-minute probe ceiling.
It has no schedule and no changes to the previous workflows or skill files.

At preparation, Python compilation and YAML/bash syntax checks passed. Local
DNS cannot reach GitHub and Hermes is not locally installed, so actual host-loader
results must come from the hosted run and its returned records, not local syntax
checks. The observed results and inspected original artifact are recorded below.

Sources: [Hermes skills documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills),
[pinned skill handlers](https://github.com/NousResearch/hermes-agent/blob/65a6b6831ef681da73955dd97a44f35794a2d4b9/tools/skills_tool.py),
[pinned registry](https://github.com/NousResearch/hermes-agent/blob/65a6b6831ef681da73955dd97a44f35794a2d4b9/tools/registry.py),
and the unchanged [skill package](../../skills/github-write-reconcile/README.md).
New harness code uses the repository's [MIT terms](../../tools/evidence-mcp/LICENSE).


## Observed host-loader result

[Run 34804656732](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34804656732)
completed successfully on its first hosted attempt at source head
`69d973b45de9bfaa9484367b16f5574cb3abe200`.
The run used the pinned unmodified Hermes sources, not a hand-written host double.
The five child processes produced these results:

| Case | Listed | Main document loaded | Supporting reader loaded | Copied CLI --help |
| --- | --- | --- | --- | --- |
| Empty profile | No | No | No | Not run |
| Complete skill folder | Yes | Yes | Yes | Exit 0 |
| Same full profile in a new process | Yes | Yes | Yes | Exit 0 |
| SKILL.md without supporting files | Yes | Yes | No | Not run |
| Complete folder disabled by profile config | No | No | No | Not run |

There were 15 programmatically chosen skill-registry calls and two --help child
launches. These are five loader scenarios, not 15 model decisions or five user
installations. No external file lookup, network attempt or denied out-of-sandbox
write was recorded in the guarded children. The full original and copied skill
folders retained the exact 12-file manifest. The upstream checkout was unchanged.

The markdown-only case returned readiness_status=available for its document but
failed to return scripts/reconcile.py. This distinguishes document availability
from runnable package completeness in this concrete case; it is not a claim that
the host promised a complete executable installation. The disabled case remained
unavailable even though the full files were physically present.

## Original artifact and readback

Artifact `10332817474`: 55,768 bytes, 13 JSON/log members, SHA-256
`61584d39d83ff56b0de0076eaea7caf3f82f8e19d89e7c4ce281c7768d621eba`.
The returned archive was downloaded and opened. A separate standard-library reader
checked its digest/CRC, five individual records against the summary, distinct PIDs
and ordered lifetimes, the same reopened profile, exact loaded SKILL.md/script
bytes, source hashes, the empty/disabled/missing-script outcomes, and both help
exit codes. The executing probe hash matched the local 11,329-byte prepared source:
`a72e5a3be4b2b943fd0dc12c10e764b6c5ce09983177d0f1525eab0887e3874e`.

The original archive, offline reader, unchanged skill folder and matching harness
are supplied in the conversation bundle. This readback is not a second host run
or an independent certification. Hosted artifact retention is 14 days.

The lean environment intentionally lacks dependencies for unrelated browser,
web and other plugins. The preserved logs report those plugin import failures
(missing requests/httpx), while the tested local skill-registry path passed. Do
not call this an entirely healthy/full Hermes installation or erase those warnings.
The full conversational loop, model-selected invocation, external tool execution
and the user's live profile remain untested and unchanged.

A premature PR creation request before the branch existed was rejected with 422;
it created no PR. The eventual three-file branch and its first hosted run are the
actual work recorded here. After that run, only this README was updated; the
executed harness, workflow, upstream sources and existing skill were unchanged.
