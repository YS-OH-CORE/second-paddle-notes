# Keep the PR35 evidence usable after artifact expiry

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.
This retains and checks the already-executed [PR35 stdio experiment](../stdio-round-restart/README.md).
It does not run MCP, start a server, or create another integration result.

## Use

From a checkout containing this folder and the unchanged PR35 source files:

```sh
python -S contributions/stdio-evidence-capsule/verify.py
python -S -m unittest discover -s contributions/stdio-evidence-capsule -p test_verify.py -v
```

Python 3.10+ and its standard library are sufficient. No package installation,
network access, API key, or execution/import of the retained experiment code is
needed. Verification prints JSON and does not write files. `-O` does not disable
its validation because it does not use assertions as acceptance checks.

## What is preserved

`records.capsule.json` is a lossless zlib/base64 encoding of the UTF-8 contents of
all 32 files from the successful archive and all 10 files from the first failed
archive. Original newlines and whitespace are retained. Every decoded member was
compared byte-for-byte with its original ZIP member. The capsule also pins five
source files by length, Git blob identity, and SHA-256; those files remain at their
existing repository paths and are only read as bytes.

This preserves member contents, not the ZIP container's compression streams or
headers. It must not be advertised as a byte-identical replacement of either
original ZIP. Both unchanged ZIPs are included separately in the conversation
bundle. `--original-zip PATH` optionally verifies an original ZIP's pinned digest,
CRC, exact member names, and every retained member byte; repeat the option for the
second original archive.

| Historical evidence | Identifier | Original ZIP SHA-256 |
| --- | --- | --- |
| Successful run | 34791675942 / artifact 10327972446 | `cd9aec329504cd5168ba9793382e137877263d64cf17e171fe786d6b014a2151` |
| First failed run | 34791471652 / artifact 10327682835 | `03afcabf31c2cf9051f13778dd0e712014a5a3309971623c754d02c327328107` |

The successful artifact currently reports expiry at 2026-09-28 00:08:30 UTC.
Keeping the records as repository files avoids relying only on that temporary
artifact. Repository/account deletion and source changes remain possible; this
is not an eternal-storage promise. GitHub's [artifact documentation](https://docs.github.com/en/actions/tutorials/store-and-share-data)
explains that artifact retention is configurable.

The decoded 134,834-byte packet is pinned in the verifier at SHA-256
`153ac8bda6e62faf4c260611e41f85862c11525ceb1dd613bab170f57595facd`.
Its source revision is `f795eeaad68895d4aacd1955ac137335e7898eac`.
When later development changes a pinned source file, verify against the matching
historical source tree with `--repo-root PATH`, not by silently accepting the new
source as evidence for the old run.

## Checks actually run for this addition

33 local standard-library tests passed. They include 21 deliberately altered
record cases, parser/encoding/size controls, source substitution, preservation
of the failed status, operation without site packages, and checks under Python
optimization. These are tests of the new verifier, not 33 new MCP experiments.
The original 19 unit tests and nine tool calls remain historical values in the
returned evidence, not newly executed results.

The independent reader checks the recorded graph hash against the actual graph
bytes, the probe hash against the actual probe bytes, the separately retained
client/server records against the summary, and the final result against the last
recorded call. It also checks question/schema/key/state/answer correspondence,
process ordering, error status, synthetic effects, source files and versions.
JSON true/false are not accepted as numeric 1/0. Duplicate JSON members, nonfinite
numbers, unknown metadata, changed sources and malformed compressed payloads are
rejected. The embedded records and source files are data, never imported code.

## Interpretation and continuation

Hash correspondence is not a digital signature or independent proof that every
recorded real-world event occurred. Trust still depends on the reviewed verifier,
pinned revision, and original hosted execution. The serverInfo stamp is checked
as recorded metadata, not authenticated identity. Synthetic fixtures are not
real human authorization, and private application checkpoints must not be
published in this format.

The original failed run stays failed; it reached one partial success before its
comparison error and did not complete all four cases. All original SDK, graph,
workflow, business logic, release files and their prior claims remain unchanged.
No SDK experiment is rerun by this addition. The next unexecuted
candidate remains interruption after a server-side effect but before the client
checkpoints its result. Do not count that candidate as implemented or tested.

New code uses the existing [MIT license](../../tools/evidence-mcp/LICENSE).
The earlier replay-report attribution remains with Totoro-qaq in the linked
experiment history.

## Publication repair

The first text-mediated upload of the compressed capsule did not match the
prepared file's Git blob and was not merged. Repeating that long encoded text
would repeat the failure mode. `retain_from_artifacts.py` instead reads the two
fixed original artifacts, checks their pinned SHA-256 digests, builds the packet
programmatically, checks its fixed payload and file identities, and verifies all
records before publication. Local assembly from the original ZIPs matched the
14,561-byte prepared capsule exactly.

The bounded retention workflow runs only for this repository's
`zero/retain-stdio-evidence-20260914` PR branch. It uses the existing job token for
artifact reads and a single compare-and-swap repair of the known bad capsule
blob, after 33 verifier tests. Unknown remote changes stop the write; an already
correct capsule is not replaced. The token is not forwarded to the artifact
storage redirect. The helper is a network/publication utility, unlike the offline
`verify.py` command. The workflow does not install SDKs or launch the experiment.

This job has `actions: read` and `contents: write` for the guarded one-file repair.
No account/admin setting, credential, billing setting, release, private checkpoint
or recurring schedule is changed. Existing PR35 workflows remain untouched.

## Hosted completion and remote readback

[Retention run 34793303112](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34793303112)
completed successfully at source head `9e12b38f3a1f365403fecef236c5f55bea1d753b`.
It downloaded the two pinned originals, passed all 33 verifier tests, repaired
only the known bad capsule, and compared the remote bytes with the assembled
candidate. The repair commit is `98fca7707a4e90ba61a787cc3ddcde53c252714b`.
A separate connector readback confirmed the correct capsule blob
`1b11c7cd2faced0bc11a1355074de23a04bd05e2`.

The returned inspection-log artifact `10329220341` is 875 bytes, SHA-256
`02c0346f0b5b22f91b1c34a2752c1d5a691ced77aa752fb9cd3b4e29756c467a`.
Its ZIP CRC and sole `retention.log` member were inspected. The log records
`Ran 33 tests`, `OK`, and `repaired_known_copy` with 42 retained members and five
checked source files. This was a retention/verification run, not another MCP
integration execution. The correct capsule is now a repository file; the
initial transfer error remains visible in the branch history.
