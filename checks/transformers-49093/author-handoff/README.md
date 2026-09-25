# Transformers 49093: the requested regression, independent of the closed PR

Youngseok Oh and Zero, AI collaboration partners | 2026-09-25

This is the combined regression [requested by the original reporter, lucaluo925](https://github.com/huggingface/transformers/issues/49093#issuecomment-5827315466). The diagnosis and implementation priority remain theirs. The test is available for review and reuse; no competing implementation or PR is being opened.

## Use the existing test-only patch

[regression_test.patch](regression_test.patch) is byte-identical to the previously supplied test. It changes one test file by adding one test method and the tempfile/GenerationConfig imports. It contains no runtime fix and does not depend on the implementation or branch of PR 49099.

From a suitable Transformers checkout, in the project's test environment:

```bash
git apply --check regression_test.patch
git apply regression_test.patch
python -m pytest tests/generation/test_logits_process.py::LogitsProcessorTest::test_bias_dist_processor_zero_token_roundtrip_full_prefix -q
```

The test saves/reloads `GenerationConfig(sequence_bias=[[[0, 4], -2.5]])`, processes rows `[[0], [3]]`, checks all output scores, and checks that the input scores remain unchanged. It is intended to fail on the original bug, not to provide a runtime fix by itself.

Existing [runtime evidence](../pr49099/README.md) documents the original base, exact then-open PR head and the two single-fix-reverted controls. Those historical executions are not being claimed as new tests of current main.

## Why this handoff was made

PR 49099, authored by aniketkrs, was closed without merge on 2026-09-25 at 14:10:46 UTC. A project member [emphasized the original reporter's priority](https://github.com/huggingface/transformers/issues/49093#issuecomment-5833842979). Our contribution was a supplemental test and comparison, not that PR. Linking the requested test here keeps it accessible to the original reporter without asking anyone to revive or replace the closed PR.

The [current contribution guide](https://github.com/huggingface/transformers/blob/6e4bcc5db795e369f900a00da304bfdeaeee5ac5/CONTRIBUTING.md) asks autonomous agents not to open new issues or PRs and describes the review bottleneck. This handoff adds no new upstream issue or PR and does not imply maintainer endorsement of our test.

## New check: patch portability, not runtime correctness

[Completed run 36148769208](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36148769208) applied the unchanged patch to three immutable test-file snapshots:

| Snapshot | Commit | Patch application | Only requested method/imports added |
|---|---|---|---|
| Original tested base | `89b6b17574892ec0770551537a3fe69d6886703e` | Yes | Yes |
| Historical closed-PR head | `e435677fb9981b3f2bfc7abeaabcb394e47c29e2` | Yes | Yes |
| Main observed for this check | `6e4bcc5db795e369f900a00da304bfdeaeee5ac5` | Yes | Yes |

All three original test files are byte-identical, Git blob `baa9a5e5133f91fd9ec974d37b92df5af6071d56`; all three patched results are byte-identical, Git blob `3d7a4b22563fb0219b056a1e8f325123a5c4c9a9`. This only concerns that test file, not the entire repository, runtime implementation or dependency environment.

The check ran `git apply --check`, `git apply` and AST comparisons. **No new pytest run, package import or model inference was performed.** [PORTABILITY.json](PORTABILITY.json) records the checks; [AUDIT.json](AUDIT.json) records the readback. Reapplying the patch locally to the retained originals reproduced all three tested outputs exactly, with no network needed. That is a patch-application replay, not independent runtime replication.

Patch SHA-256: `1538319d621789142fd1f0bb450e4dec4a573bbfe18036b25840ec191a7c11ff`.
Script was committed before execution at `36573abbbe18f6e2de6f3ff6b5c1af2abe6a94d7`; workflow commit `6e6d387f99eef92c077b7c682b89d6a081cee989`.
Raw artifact 10870840373: 74,082 bytes; SHA-256 `eb4a3a31e96196750e55126cdbcbdb59d96bb08ebd5571d0156331e54c035e7c`. It retains original/applied files, application logs, the patch, script, run metadata and upstream license. Actions retention is 30 days. A local source-download attempt failed DNS resolution before the successful Actions check; it was not a test failure.

## Status boundary

The reporter's earlier positive response and request are confirmed. The third-party PR is closed, unmerged. The supplemental patch is still available and applicable to the observed main test file. A new PR from the original reporter, maintainer approval of this test, or a merge is not established here.

Original diagnoses and fix direction: lucaluo925. Supplemental test, portability check and handoff preparation: Zero, AI collaboration partner working with Youngseok Oh. AI participation is explicit; no human code review by Youngseok is claimed.
