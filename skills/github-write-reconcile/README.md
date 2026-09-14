# A read-only recovery skill for an agent, not another fault experiment

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

PR44 supplied a real-provider case: a GitHub write could be committed even when a
later client check failed. This folder turns the readback portion into a small
standalone command and an opt-in Hermes-compatible Agent Skill. It neither
imports the earlier probe nor creates a new marker. Existing releases, MCP tools,
Hermes configuration and the user's installed skills are unchanged.

## Use without installing a skill

From this directory, with Python 3.10+:

```sh
python -B -S scripts/reconcile.py --intent examples/completed-retry.json
```

The example checks the already-existing PR44 marker at its recorded commit. It
uses public GETs and sends no file content. No pip install or API key is needed
for public reads, subject to GitHub's rate limits. Authenticated reads require the
explicit --use-github-token flag and an existing GITHUB_TOKEN; the flag is not an
instruction to create credentials or change permissions.

To use another file, provide an intent containing exactly version=1, repository,
ref, path and expected_sha256. The expected digest must come from the intended
pre-write bytes, not from the remote file being checked. Only branch names or
40-character lowercase commit SHAs are supported, not tags or arbitrary URLs.

## Optional Hermes use

SKILL.md and its scripts form a self-contained skill folder. After review and
explicit installation approval, the whole github-write-reconcile directory can
be placed in the chosen Hermes profile's skills directory. Do not copy just
SKILL.md without scripts. The default profile uses ~/.hermes/skills/ according to
the pinned [Hermes skills guide][hermes]. No installation is performed by this
repository change. Skill selection by a model and the user's live Hermes
installation have not been tested here. The command itself is independently usable.

## Four outcomes

| JSON status | Exit | What was established |
| --- | ---: | --- |
| content_match | 0 | Expected bytes exist at the pinned snapshot. |
| content_conflict | 2 | Different bytes are present. No overwrite is attempted. |
| absent_at_snapshot | 3 | The complete tree has no such path at that snapshot. |
| unknown | 4 | Provider access, network, limit, shape or identity could not be verified. |

Every outcome contains retry_authorized=false. In particular, a 404 from an API
is unknown, not an assertion that the original write failed. Even an absent path
in a complete historical tree cannot rule out an in-flight request, a later
commit or a subsequent deletion. PR44's 12-second observation window was a bounded
observation, not proof of non-execution. This reader never authorizes a retry.

## Mechanism

Resolve a branch once, then read the Git commit, complete recursive tree and
referenced blob. All post-resolution requests use immutable object identities.
Verify the regular-file mode, declared size, strict base64 representation, Git
blob hash and SHA-256 of the actual bytes. A newer unrelated branch commit does
not cause a false mismatch with an earlier matched file.

Only GET exists in the transport, with no request body, no redirect following,
no automatic retry and a four-request budget. Public unauthenticated reads are
the default. Optional authentication is sent only to api.github.com. The output
contains fixed diagnostics and hashes/identifiers, not remote file content or
response error bodies. This is not a secret classifier; the caller still chooses
a repository and file it is authorized to inspect.

Limits: a 64 KiB file, 2 MB API response, at most 5,000 complete-tree entries and
10 seconds per HTTP request. Truncated trees, symlinks, submodules, noncanonical
base64, duplicate JSON keys and nonfinite JSON values fail closed. Large
repositories may return unknown rather than a partial answer. No signed attestation,
HTTP-outcome recovery, operation-uniqueness guarantee or general exactly-once claim.

## Checks and live readback

```sh
python -B -S -m unittest discover -s tests -p 'test_*.py' -v
```

26 offline unit tests passed locally and in the hosted run. They use controlled
records; they are not 26 external writes. Local DNS cannot reach GitHub in this
session, so the bounded hosted read-only workflow checked the live CLI against:

- the marker from PR44's earlier failed checker, using its current provider branch;
- the successful retry marker at its immutable commit;
- a deliberately wrong expected digest for that same existing file;
- a nonexistent path in the same immutable tree.

All four fresh CLI checks passed in run 34803598911 using twelve GET requests.
The last two are read-only diagnostic controls, not new provider objects.
The returned seven-member artifact was inspected, including the matching source
hash. See [VERIFIED.md](VERIFIED.md) for IDs, exact outcomes, the retained initial
configuration failure, and scope. Earlier loss experiments were not rerun.
No model/API generation or new dependency was used.

## Sources and provenance

GitHub documents [reference reads][refs], [commit reads][commits], [tree reads and
truncation][trees], and [base64 blob reads][blobs]. These define the provider data
used here. The earlier measured fault harness is
[github-response-loss](../../contributions/github-response-loss/README.md).
The new reader is a narrow application of those primitives, not a new protocol.

[hermes]: https://github.com/NousResearch/hermes-agent/blob/dd497c3d5925323ae3e60613befe0f4509b2d0d8/website/docs/user-guide/features/skills.md
[refs]: https://docs.github.com/en/rest/git/refs#get-a-reference
[commits]: https://docs.github.com/en/rest/git/commits#get-a-commit
[trees]: https://docs.github.com/en/rest/git/trees#get-a-tree
[blobs]: https://docs.github.com/en/rest/git/blobs#get-a-blob

MIT license, included as LICENSE. Prepared by Youngseok Oh with Zero (ChatGPT).
