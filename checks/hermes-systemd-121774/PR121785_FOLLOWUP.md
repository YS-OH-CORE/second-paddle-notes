# Following the current fix, not asking for another copy

Youngseok Oh × Zero | 25 September 2026 KST

## Why this follow-up exists

In [Hermes issue #121774](https://github.com/NousResearch/hermes-agent/issues/121774#issuecomment-5818325634), contributor **686f6c61** clarified that [PR #121785](https://github.com/NousResearch/hermes-agent/pull/121785) carries the older not-found-unit guard onto current main. Its description credits kokhlo's earlier #103086/#103062. The implementation and decision to port it are the contributor's work; this review does not claim to have caused the PR or authored its repair.

The earlier check in this directory used an old candidate and a substituted duration parser. This follow-up selects the actual current candidate's unmodified probe, its helper and its actual duration parser from a verified source file. Only the systemctl subprocess is simulated. This remains a function-level check, not a full-module or systemd integration test.

## Source and execution

[Exact executed checker](https://github.com/YS-OH-CORE/second-paddle-notes/blob/700dd2a66b63928afd5bcc838fa66dba34683143/checks/hermes-systemd-121774/check_current_pr_121785.py)

- Base: `NousResearch/hermes-agent@d350422b15863fc4c0b7962b122b625a0271516c`, `gateway/shutdown_forensics.py`, Git blob `c7d337d47f233b599028488c78603a32c1aa964a`.
- Candidate: `686f6c61/hermes-agent@2c6f77434a6a0e54bea6861901cb3adc98478936`, same file, Git blob `9944cc1b88356bdb10c9273f45c9c7795193bb42`.
- Both blobs were retrieved through read-only GitHub API requests and their byte identities checked before AST selection.
- Run: Windows, Python 3.12.10, standard library only. UTC start recorded `2026-09-24T20:33:45.471800+00:00`.
- Executed script SHA-256: `580a0da95329c9f38f56c8352504ff9c479efc8a7b5133ef08de06d33dfa5e89`.
- Original structured `report.json` SHA-256: `a054d5b86827d2f7ae809abea78b13b4ed850b354d306d6f2509b207f990ecd5`.

The checker uses an already authenticated `gh` to fetch public source. It does not read or print tokens. It creates a fresh temporary output directory and retains the downloaded sources and report there. It does not install packages, run Hermes, invoke systemctl, restart services, change the live user's configuration or call a model. Check `success` in the structured output; this script is not a CI runner with failure-exit semantics.

## Observations

| Synthetic case | Base value | Candidate value | Candidate query order |
|---|---:|---:|---|
| Missing user unit, loaded system unit | 90 s | 210 s | user, system |
| Missing in both managers | 90 s | unknown (`None`) | user, system |
| Loaded user unit takes precedence | 240 s | 240 s | user |
| Genuinely short loaded user timeout | 90 s | 90 s | user |
| User query returns nonzero | 210 s | 210 s | user, system |
| User query times out | 210 s | 210 s | user, system |
| Loaded unit with empty FragmentPath, fractional duration | 90.5 s | 90.5 s | user |
| Unparseable user duration | 210 s | 210 s | user, system |

**Eight candidate cases passed.** In each case both the value and query sequence were checked. Two cases changed as intended; six controls retained their values and query sequences. The fake systemctl returns only requested properties, so the old probe cannot accidentally see LoadState it never requested. The fractional-duration and invalid-duration cases call the real source-selected parser, not a table of precomputed answers.

## Limits and operational notes

This is one author-side fixture execution, 16 function evaluations across eight paired cases. It is not eight independent deployments, a live Linux reproduction, a complete PR test suite, a maintainer approval, or independent human review. AST selection omits module initialization and package integration. The subprocess exceptions and properties are synthetic. The check does not settle which manager owns a process when both have loaded same-name units, nor masked/bad-setting/error-state policies. It tests no real service and disables no safeguards.

An earlier attempt to download the source in the assistant's separate working container failed due to DNS resolution. It did not run a test. The successful execution used the user's already-authorized remote PC and read-only GitHub API requests. After the check, `exit()` was unavailable in the `python -S` REPL; `sys.exit(0)` was then used to end that test process. Neither issue is a finding against the candidate.

No competing PR or requested-change verdict is proposed. Existing reports and fixes retain their authorship. Supplemental source review, fixtures, execution and writing: **Zero, an AI assistant, for Youngseok Oh (@YS-OH-CORE)**. No external uptake or endorsement is claimed by this record.
