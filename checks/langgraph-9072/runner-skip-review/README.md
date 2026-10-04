# Reject-first ParentCommand review: preserve the existing skip-future contract

**Zero × Youngseok Oh | 4 October 2026**

This checks one compatibility boundary in [impartshadow's reject-first proposal](https://github.com/langchain-ai/langgraph/issues/9072#issuecomment-5978266313). It is not an upstream patch, a competing PR, or a maintainer decision on rejection versus coalescing. The policy proposal belongs to impartshadow; the reference implementation and tests here are ours.

## Finding

When collecting `ParentCommand` exceptions, preserve `SKIP_RERAISE_SET` before counting a future as another handoff. The pinned runner explicitly places nested `_call`/`_acall` task futures in this set because their exception propagates through the enclosing task. The original `_panic_or_proceed` does not re-raise a skipped non-interrupt future. A straightforward translation that classifies `ParentCommand` before checking this set changes that contract.

Two direct boundary controls use real standard-library Future objects:

- A skipped child and an enclosing future hold the **same** `ParentCommand` exception object. Upstream raises that original exception once. Our naive reject-first reference counts two and raises `InvalidUpdateError` instead.
- A skipped child is the only completed future. Upstream returns normally; the naive reference raises its `ParentCommand`.

Both differences were observed with `concurrent.futures.Future` and `asyncio.Future`. These four lower-level cases are not a claim that the two-future arrangement was reproduced by the original reporter's `create_agent` workload.

The separate `handled_futures` and `handled_exception_ids` filters do not replace the skip-future contract. Controls for each of those existing filters still pass in all compared variants.

## What was run

Source: [LangGraph `9a0394d88b2211f299dcd69df92db3480c69ee61`](https://github.com/langchain-ai/langgraph/tree/9a0394d88b2211f299dcd69df92db3480c69ee61). The installed local libraries were built from that checkout; test processes imported the checkout's core package via `PYTHONPATH`. Each variant ran in its own pytest process with the same test file and environment.

| Variant | Direct boundary cases (16) | Compiled direct parent/child graphs (4) | Exploratory nested-task graphs (2) | Overall |
|---|---:|---:|---:|---:|
| Unchanged runner | 12 pass / 4 fail | 2 pass / 2 fail | 0 pass / 2 fail | 14 pass / 8 fail |
| Our straightforward reject-first reference | 12 pass / 4 fail | 4 pass | 0 pass / 2 fail | 16 pass / 6 fail |
| Same reference with skipped parent futures excluded | 16 pass | 4 pass | 0 pass / 2 fail | 20 pass / 2 fail |

The four direct failures change identity: upstream does not implement the proposed multi-parent rejection or timeout priority; the naive reference implements those but fails the existing skip-future controls. The guarded experiment retains the proposal's behavior in the tested cases without those four lower-level regressions.

The four compiled graph controls contain no model or fake graph components. They confirm that one direct handoff still delivers its update and visits its destination once, and that two direct sibling parent commands cause the proposed explicit error without running the parent destination. That error policy is still unapproved.

**The two exploratory nested-task cases failed on every variant:** a graph invoked inside an `@task` did not deliver the expected update to the outer state. They are retained, not skipped or relabeled as passes. We have not established their intended supported semantics or a new upstream defect, and they do not demonstrate that the skip-future guard fixes arbitrary nested graph handoffs. The guarded experiment is not an all-green 22-case suite.

## Files and reproduction

`candidate_boundary.py` is our discussion-only reference. `test_parent_boundary.py` selects `baseline`, `proposal`, or `skip_guard` using `BOUNDARY_VARIANT`; the latter filters already-skipped completed parent exceptions before calling the reference. These are test-process substitutions, not edits to the user's installed framework. Source and test hashes, exact counts, and dependency versions are retained with the observations.

Install the four local libraries (`libs/checkpoint`, `libs/sdk-py`, `libs/prebuilt`, `libs/langgraph`) from the pinned checkout into an isolated environment. Use the recorded dependency versions, set `PYTHONPATH` to the checkout's `libs/langgraph`, disable tracing, and run from this kit's directory:

```shell
python -m pytest test_parent_boundary.py -q --tb=short -p pytest_timeout --timeout=15
```

Repeat in separate processes for the three `BOUNDARY_VARIANT` values. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` was used; the timeout plugin was loaded explicitly. Windows / CPython 3.12.10 was executed. No paid model call, server service, user database, upstream CI, full repository suite, or broad lint/type-check pass is claimed.

An earlier pilot asserted an incorrect expected outcome for a directly raised internal sentinel. That pilot is not evidence of an upstream regression. Its original tests and receipts remain in the private working archive. The final comparison above instead retains the public nested-graph attempt as two explicitly unresolved cases. Only local owner paths are redacted in public logs; assertion results are unchanged.

Original issue: elizandropacheco. Earlier handoff discussion and proposed rejection policy retain their contributors. Our contribution is executable compatibility evidence and the skip-registration caution. Maintainer approval, adoption and merge remain separate from publication of this review.
