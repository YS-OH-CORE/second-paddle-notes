# Existing Hermes contribution: tested integration follow-through

Prepared by Zero for Youngseok Oh, 19 September 2026.

This isolated operational branch is **not a merge candidate** for the notes repository. The default branch and private project records are unchanged. It follows through on the existing Hermes PR #22982 rather than creating a competing feature PR.

## Fixed source and narrow resolution

- Main snapshot: `3eb9712180ec60191edfb9d072ddb28ffe427e4b`
- Existing PR head: `501be10cce7159a08279c89c724db602d9770601`
- Merge base: `79445a496c86a19332ad786494b8384d2167e2d0`
- Passing verifier commit: `846bb4ec171b61b5b12e1eb114ffb88b7deda03c`

The five changed files produced one textual conflict in `_commit_model_switch`. The candidate keeps the current reasoning-effort branch and wraps the final reply in `ModelSwitchConfirmation` after concatenation. It does not remove production approval or generation guards.

The old multiline fixture also needs its cleanup lambda to accept the current `run_generation` keyword. The v2 preparer changes only that fixture signature. The binding test file remains byte-identical and the multiline assertion AST is checked unchanged. This adaptation is not a new validation of production cleanup concurrency.

## Actual execution

[Passing run 35430164170](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35430164170) uses actual fixed-source imports, the upstream frozen lockfile and canonical `scripts/run_tests.sh`, with fixture model and transport boundaries. Candidate checks: current reasoning 2/2, existing multiline 9/9, existing binding 10/10, combined checks 8/8. All have zero errors and skips. The baseline's two reasoning checks are separate.

Two deliberately one-sided conflict resolutions fail 7/8 and 5/8 of the same combined checks. These are controlled bad-merge variants, not reported defects in released Hermes. The good candidate was restored afterward.

Earlier attempts remain recorded:
- 35429462800: source diagnosis only, success.
- 35429814828: stopped before tests because uv was absent.
- 35429935706: environment and baseline succeeded; the obsolete fixture signature caused ten candidate failures.
- 35430164170: same production candidate plus the one fixture-signature adaptation, selected tests pass.

The actual technical follow-up was [posted to the existing PR](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5740295083) and read back. This is not maintainer acceptance, a full-suite pass, live Slack/provider validation, or evidence that moving main is now merge-ready. The upstream PR head was not changed.

## Reproduce

Keep the scripts in this directory together. `python -B prepare_port_v2.py NEW_OUTPUT_DIRECTORY` requires Git, Python and network access to public pinned files. It refuses an existing directory and generates source snapshots, candidate files, the upstream license and `current-main-port.patch`.

Expected patch: 40,485 bytes; SHA-256 `819e5a16b3d0ad71dca71b84fcc69363b9c4c5282a593e133c76a0f7e59f83c5`. Exact patch and manifest bytes are also preserved in the passing job's `PUBLIC_PORT_FILE` log records. The new eight-check test is a separate file, not included in that five-file patch.

`execute_port_check_v2.py` runs the selected checks in a new disposable checkout. It requires uv 0.12.13 and Python 3.12, downloads public source, and installs its locked development dependencies. Do not confuse that with a read-only source inspection: the later runs execute real upstream code under controlled test fixtures. They use no live model credentials or private user material.

All four standard public Ubuntu jobs have ended. Maximum runtime was five minutes for the source diagnostic and eight minutes per test job. No schedules, large runners, uploaded artifacts, cache action or persistent service were configured. No main-branch update, application submission, identity upload or grant correspondence is part of this branch.

The original feature remains its author's work. New contribution code is offered under upstream MIT terms; existing copyright notices are retained. Results are authored execution evidence, not independent review.
