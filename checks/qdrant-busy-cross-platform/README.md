# Qdrant real SQLite BUSY: cross-platform differential check

**Zero × Youngseok Oh**

This is a reproducible comparison for the [proposed transaction cleanup](https://github.com/YS-OH-CORE/qdrant-client/commit/01ed8bec882f1ee084a757d17f21069e4fe29700), building on adityaanikam's [Qdrant #1515](https://github.com/qdrant/qdrant-client/pull/1515). It is not a second competing fix or an independent human review.

The [earlier executed Windows evidence](https://github.com/YS-OH-CORE/qdrant-client/tree/b4491b3ea90c9ea73c543aab3443be7c22de2a6d/review-evidence/local-delete-busy-20261004) found eight new cases fail on the author's code and pass with the proposed change. Four existing persistence tests still failed in both variants. This workflow tests the same source pair in clean GitHub-hosted Windows and Linux environments, rather than presuming the local result transfers.

## Exactly what is checked

- Author runtime: `560d8c0d3b826bf2a8e3943fca27724332086500`.
- Proposed runtime: `01ed8bec882f1ee084a757d17f21069e4fe29700`.
- The candidate's unmodified regression file is copied to the author checkout; its LF-normalized SHA-256 must be `8c4773bbc08b20bf411b150c5d61965482191c5f8876093567bc9305b3c5d703`.
- Each runtime runs in a fresh pytest process. Imports must resolve to that checkout; tracked source diffs must remain empty.
- All eight baseline regressions must fail at the expected live/reopened state mismatch, and all eight candidate cases must pass. Missing cases, unrelated errors, and changed neighbor outcomes fail the comparison.
- Both original neighboring test files are run without editing, skipping or xfail conversion. Their actual nonpassing outcomes remain in the logs and the JSON receipt.

**A green workflow means the differential contract passed. It does not necessarily mean every selected test passed.** `all_candidate_selected_tests_passed` and `candidate_remaining_nonpassing_tests` report that separately. No full-repository suite, live server, live model, billing result, maintainer approval or upstream merge is asserted.

The workflow uses read-only repository permissions, no credential persistence, two standard hosted runner jobs, and no schedule. Only a push changing this harness on the exact verification branch triggers it. It does not alter an upstream repository's workflows or approve an upstream CI run.

## Run outside Actions

With the recorded dependencies installed, prepare separate clean Git checkouts at the two commits above. Install the candidate package for distribution metadata; the runner verifies each process actually imports its own checkout. Then run:

```shell
python compare.py --self-test
python compare.py --author /path/to/author --candidate /path/to/candidate --out /path/to/new-results
```

The requirements record the earlier resolved package versions. `pywin32` is restricted to Windows; other versions are held constant. Python is pinned to 3.12.10 in Actions. SQLite's realized version, the operating system, each pytest exit code, and realized dependency versions are preserved per runner. Setup/install errors are not product failures.

The regression uses a real read-only SQLite transaction as a controlled lock source, not concurrent Qdrant writers or a mocked storage exception. Public Qdrant calls are sequential and data are synthetic in temporary stores. The eight parameterized cases are combinations of one failure mechanism, not eight independent contributions.

The local comparator self-tests and a replay against the earlier JUnit receipts passed before publication. Hosted execution results must be read from a completed run and its artifacts; this document is not itself a hosted pass receipt. The author's existing ordering fix retains its attribution; Zero authored this comparison runner and executed the recorded checks under Youngseok's direction.
