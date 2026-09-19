# Bounded public-form observations

Isolated operational snapshot, **not a merge candidate**. The default branch,
research, private notes and user records are unchanged. This branch intentionally
contains only the public-reader workload, not a copy of the main project tree.

The workload used anonymous browser sessions to inspect the public Foresight call
and its application form. It did not log in, type personal information, upload
applicant materials, accept consent terms, or submit a form. Later probes opened
public dropdowns and selected generic application-type/funding options locally.
Non-read network methods were blocked. Only public observations went to logs.

## Observed runs

1. [35417628420](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35417628420):
   official call, current linked grant form, and separate xNode interest form read.
   The current grant form differs from the historical candidate. No input actions.
2. [35417868644](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35417868644):
   dropdown options read. The requested Funding label did not match Funding (Grant),
   and the physical Yes-option click timed out. Job success is not selection success.
3. [35418116675](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35418116675):
   Individual selection confirmed. Funding (Grant) appeared as a chip in the body,
   but the inspector checked the empty combobox text and stopped before funding Yes.
   This was an inspector-observation mismatch, not evidence of a denied application.
4. [35418234888](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35418234888):
   the independent funding Yes selection confirmed; three conditional funding
   questions became visible. No amount or personal value was entered.

The observed current grant form is:
https://airtable.com/appyVXc5SMPAvIKpP/pagp7takV26cG6JY1/form

Visible labels/ARIA markers are observations, not server-side validation.
Funding-only treatment of the physical-node fields and unvisited branches remain
unresolved. No application, reference permission, award or access exception was obtained.

A standard public Ubuntu runner was used, at most five minutes per job. Workflows
configure no uploaded artifacts, cache action, external AI API, large runner,
schedule or persistent service. Each is restricted to its own request-file push
on this branch. Source files were checksum-verified in the runs. No credentials
or secrets were passed to the browser scripts.

Prepared by Zero for Youngseok Oh, 19 September 2026.
