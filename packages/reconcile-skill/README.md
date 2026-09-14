# Package the checked skill, without another fault experiment

Youngseok Oh with Zero (ChatGPT), 2026-09-14.

This produces an opt-in source ZIP for the existing read-only GitHub skill and a
separate evidence ZIP. It is not the existing evidence-mcp wheel. No runtime skill
file or earlier harness is changed, no model is called, and no user profile is
installed or modified.

## Fixed inputs and outputs

`source.json` pins 19 source files at commit
`24408637d33ef999ba1c03fd34096af7da258913`, including the exact 12-file skill tree
`0e881b5e9705b7770cf5d32d0df32553ab5504a1`. It also pins the five original ZIPs
covering PR45's successful/failed reader checks, PR46's host-loading check, and
PR47's successful/failed terminal task. Failures retain their original status.

`build.py` checks bytes, Git blobs and SHA-256, original ZIP CRC and member sets,
then creates ZIP_STORED archives with fixed order, timestamp and permissions.
The small runtime package adds a Korean guide, read-only VERIFY.py and PACKAGE.json
outside the unchanged skill folder. The evidence package contains original ZIP
bytes, matching source and provenance. Both are usable without this checkout;
re-running the old host experiments still needs the pinned Hermes source.

`expected-assets.json` pins the four output assets prepared locally. A changed
input or output is a refusal, not an automatic republishing opportunity. Hashes
are correspondence checks, not signatures or independent certification.

## Local packaging check

```sh
python -B -S packages/reconcile-skill/build.py \
  --repo . --originals /path/to/original-zips --out /path/to/new-dist
```

The builder runs twice and compares exact output bytes. It extracts the runtime
into a fresh directory, runs the package verifier, the existing 26 offline unit
tests and the CLI's --help, then confirms a missing script makes package
verification fail. These are packaging checks, not new provider or fault trials.
The command creates only the explicitly new output and temporary test directories.

## Bounded publication

The workflow is restricted to the named same-repository release branch. It uses
a standard public Ubuntu job, five-minute ceiling, pinned actions, and only
contents:write/actions:read. It downloads the five pinned originals directly,
assembles the expected bytes, tests them, and creates one named preview release.
Existing assets are never overwritten or deleted; unexpected assets or metadata
stop the operation. A matching interrupted draft can be reconciled by numeric ID.
No other release, tag, billing setting or user configuration is modified.

After publication every asset is downloaded without authorization or cookies.
The downloaded runtime is freshly extracted and checked again. Other pre-existing
release asset IDs/digests/sizes are compared before/after. Download success and
returned original logs must be inspected before claiming publication is complete.

The public release is a versioned acquisition route, not eternal or tamper-proof
storage. Repository owners can change availability. It does not automatically
update or install the user's copy. Source includes no keys or private checkpoints.

## References

[GitHub release API](https://docs.github.com/en/rest/releases/releases),
[asset API](https://docs.github.com/en/rest/releases/assets), and
[standard public-runner billing](https://docs.github.com/en/actions/concepts/billing-and-usage).
Original runtime terms are preserved in skills/github-write-reconcile/LICENSE.
New packaging code uses those existing MIT terms.
