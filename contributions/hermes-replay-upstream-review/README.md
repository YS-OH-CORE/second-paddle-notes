# Follow-through on upstream replay classifier PR #107809

[KoNit-K's PR](https://github.com/NousResearch/hermes-agent/pull/107809) explicitly fixes [our report #107807](https://github.com/NousResearch/hermes-agent/issues/107807). The production implementation and its tests belong to that contributor. This folder assesses that exact proposal rather than publishing a competing repair.

## Reused tests, new target

Compare the actual single-commit parent `3b044261b6afe97277d48e7e75c65ce34e76e8a2` with the proposed head `59048b3a0335216b7983072bb1d006a179ca57ae` from `KoNit-K/hermes-agent`.

The 27 broad cases and eight separate-process SessionDB cases already in `../hermes-replay-status` are used unchanged. These are not newly collected cases. Only the test-file hunk is taken from our old patch; **our production patch is never applied to either checkout**. The candidate's existing test file is also executed unchanged. Runtime/module identities and tracked source preservation are checked.

## Important expected boundary

The candidate explicitly keeps non-object JSON on its legacy heuristic. Our prior broad fixture expects valid JSON lists and JSON string values to remain data. Those two cases are intentionally left as ordinary failing assertions: no deletion, skip, xfail, changed expected answer, or relabeling as passes.

A successful verifier exit means the assessment completed with the explicitly described boundary, **not that every supplied test passed**. The summary contains `all_supplied_supplemental_tests_pass: false`. Raw pytest exit codes, XML reports, failure names and messages remain in the evidence. The public claim is object-envelope correction and compatibility with the tested persistence path, not elimination of every text ambiguity. Do not call the residual non-object behavior a regression introduced by this PR.

## Reproduce in disposable checkouts

After the same normal Hermes test dependencies are available:

```sh
python contributions/hermes-replay-upstream-review/verify.py --base /path/to/exact-parent --head /path/to/exact-head --out /path/to/new-output-folder
```

The verifier adds untracked synthetic test files to the two checkouts; it refuses pre-existing targets and refuses modified source. Do not use a working installation. The workflow creates disposable Linux checkouts and a clean temporary environment. It performs no provider call or live gateway launch, and uses no user history.

The SessionDB tests write and close a temporary database in one process and reopen it in another. Their selected serialized payloads are synthetic, not actual terminal interruptions or real-user data-loss reports. Checksums and author-run CI are not independent institutional validation, a live-model result, merge approval, or evidence of release adoption.

Actual run evidence is attached to the pull request that introduces this folder. Do not infer completion merely because this script exists. Prior patch tests and source archives retain their original history. Prepared with Zero (ChatGPT).
