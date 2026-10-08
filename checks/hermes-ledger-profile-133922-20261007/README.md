# Hermes service profile attribution: UI selection is not process ownership

**Zero × Youngseok Oh | 7 October 2026 | Reproduced function chain; candidate patch, not an installed fix.**

This kit examines only the service-attribution symptom reported by **El-lucid-8** in [Hermes #133922](https://github.com/NousResearch/hermes-agent/issues/133922#issuecomment-6019099034). The original report and its real-world observations are theirs. Our contribution is the narrow source diagnosis, synthetic comparison and candidate below.

It does **not** reproduce or fix the issue's original MEMORY/USER contamination, profile backup scope or a general security boundary. The test uses no real user memories, model calls, running server or live spawn ledger.

## Observed path

Tested Hermes snapshot: `a50406d9b7474b060450d2dcaff8743c977d296a` (7 October 2026). Before publication on 8 October, the registration callback was read again at `8a33891bdd58c3e0795ebfb277bcdde1003e91ea`: it still writes `initial_profile` into `detail.profile`. This is a fresh source check, not a new full runtime test.

1. [`cmd_dashboard`](https://github.com/NousResearch/hermes-agent/blob/a50406d9b7474b060450d2dcaff8743c977d296a/hermes_cli/main.py#L2706-L2763) passes `args.open_profile` as `initial_profile`. This is the UI destination, not necessarily the process home.
2. [`web_server._register_identity`](https://github.com/NousResearch/hermes-agent/blob/a50406d9b7474b060450d2dcaff8743c977d296a/hermes_cli/web_server.py#L1450-L1457) writes that UI selection into `detail.profile`.
3. [`register_self`](https://github.com/NousResearch/hermes-agent/blob/a50406d9b7474b060450d2dcaff8743c977d296a/hermes_cli/process_identity.py#L210-L240) separately writes the resolved `hermes_home`, so the two fields can disagree.
4. [`_collect_ledger_runtimes`](https://github.com/NousResearch/hermes-agent/blob/a50406d9b7474b060450d2dcaff8743c977d296a/hermes_cli/update_inventory.py#L271-L304) labels a missing/empty profile as `default`, without using the stored home.

Thus an A-owned backend with no UI selection can appear as `serve [default]`; a default-owned backend opening profile A in the UI can appear as A-owned. This supplies a deterministic function-level mechanism for the reported labeling symptom. It does not prove the reporter reached it through the same launch sequence.

## Candidate and measurements

`owner-profile.patch` derives `detail.profile` from `profile_name_for_home(hermes_home_key())`, the canonical home that the existing registration function records. It does not alter the UI selection, listening address, actual port, kind, isolation flag, job attachment or restart policy.

Each row below was exercised for both `serve` and `dashboard`, making twelve cases:

| Resolved owner | UI selection | Original inventory label | Candidate label |
|---|---|---|---|
| profile-a | empty | default | profile-a |
| profile-a | profile-b | profile-b | profile-a |
| profile-a | profile-a | profile-a | profile-a |
| default | profile-a | profile-a | default |
| default | empty | default | default |
| profile-b | profile-b | profile-b | profile-b |

Recorded Windows run: **6/12 expected labels before, 12/12 with the candidate**, exit code 0. Temporary fixture directories were removed and the four upstream files retained their original SHA-256 hashes. `RESULT.json` includes every case and the tested source hashes. This is not a success rate for real users or the whole application.

## Reproduce

The recorded standalone harness run used Windows and Python 3.12.10. In this kit's directory, with that interpreter:

```text
python -B fetch_sources.py
python -B check_ledger_profile.py
```

The first command downloads only four public Python files at the pinned commit and checks the recorded SHA-256 values. It does not install dependencies or import those files. The second command runs the local synthetic comparison using the standard library. Neither command launches Hermes or calls a model.

The harness executes the exact nested callback extracted with Python AST and the real full `hermes_constants`, `process_identity` and `update_inventory` modules. It mocks ledger I/O, process creation/spawner facts, OS job attachment and supervisor probes. It also exercises the actual plan formatter. Importing the full web server would start unrelated initialization, so that is deliberately not done.

Expected assertions cover author/profile labels and unchanged home, host, port, purpose, isolation, attachment and restart classification. The candidate source is written only under `candidate/`; the script never patches a user's installed Hermes tree.

## Limits before adoption

This is a review candidate, not a production-ready PR or a full upstream regression run. Actual Desktop discovery, CLI routing, launchd, SSH, restart behavior, concurrent context changes and custom-home alias cases still need project-level coverage. A context-scoped or incorrectly bound home remains a separate problem; this patch aligns two registration fields, not a stronger process-launch identity guarantee.

Existing ledger rows are not migrated. Updating this callback would only affect subsequent registrations. The runtime memory restore path, prompt persistence and backup collector are unchanged. Do not infer that correcting the label resolves the privacy incident in #133922.

Only synthetic profile names and data are published. The locally generated candidate module is not included, only its small diff. Upstream code and quoted snippets retain the **MIT License, Copyright (c) 2025 Nous Research** in `UPSTREAM_LICENSE.txt`. Zero prepared the diagnosis, harness and candidate with AI assistance; no maintainer approval or adoption is claimed.
