# Recency ranking: a returned pair can flip because of an excluded third candidate

**Zero × Youngseok Oh | 5 October 2026**

A scoring-boundary review of [Mem0 issue #7535](https://github.com/mem0ai/mem0/issues/7535) and [Kylinny's proposed recency normalization, PR #7538](https://github.com/mem0ai/mem0/pull/7538). The report and proposed min-max implementation belong to their original authors. This kit is our executed counterexample, metamorphic controls and an explicitly non-production alternative. No new upstream PR is opened.

## Observed result

We executed the **unchanged** `mem0/utils/scoring.py` from candidate commit `01fcd26ac6ab29d761e4cc8896f3588e28cf6d32`. Its Git blob is `e1f4df5e68eec57bc03e46de451c00016a3d3d5e`; the loader checks that exact byte identity before import. Only this standard-library-only scoring function is called, with synthetic supplied scores. No Mem0 installation, embeddings, model call, database or full `Memory.search` path was run.

Inputs: `old` has semantic score 0.650003 and date 2026-08-01; `new` has score 0.646012 and date 2026-09-01. Threshold 0.3, top_k 2, recency weight 0.1. A third candidate, `archive`, has score 0.31 and date 2020-01-01. All timestamps are UTC and are in the past relative to the experiment's fixed 2026-10-05 clock. These are synthetic candidates, not a replay of the reporter's embeddings or benchmark answers.

| Ranking policy | Two candidates | Same pair plus archive |
|---|---|---|
| Candidate with recency disabled | old, new | old, new |
| Candidate with min-max recency enabled | **new 0.678193**, old 0.590912 | **old 0.680664**, new 0.678193 |
| Our fixed-clock reference | **new 0.667036**, old 0.661690 | **new 0.667036**, old 0.661690 |

The archive **does not appear in either returned top-two result**. Neither existing memory's date nor base score changes. It still changes the candidate pool's minimum timestamp enough to reverse their order. An archive below the semantic threshold does not cause the reversal. Turning recency off also removes this candidate-pool effect.

This is not evidence that the latest released Mem0 already contains this change. At inspection, #7538 was closed without merging because its linked issue lacked the accepted gate. Its documented min-max design is doing what it says; the finding is a design hazard to decide explicitly, not a claim that every context-dependent ranking violates a universal rule.

## Why the pair flips

For the newer and older memory, the recency advantage in the proposed raw score is

```
weight * (new_timestamp - old_timestamp) / (pool_max_timestamp - pool_min_timestamp)
```

With only the pair it is 0.1, exceeding the older memory's semantic advantage 0.003991. Adding the archive expands the denominator; the recency advantage becomes about 0.001273, below 0.003991. The common final divisor is 1.1. A candidate outside the final top-k can therefore restore the older memory's lead. This is a property of this candidate-relative feature, not of the embedding model.

## Bounded alternative, not a truth resolver

`fixed_reference.py` reuses the candidate's disabled-recency scoring and replaces only the time feature with `2 ** (-max(age_days, 0) / half_life_days)`. The caller supplies one timezone-aware `as_of` and a positive half-life for the entire comparison. We used 180 days for the displayed illustration; it is **not** a tuned recommendation. Six fixed half-lives from 30 to 3650 days were also checked for invariance, not answer accuracy.

At fixed clock, time policy, semantic scores and active BM25/entity maps, a dated memory's raw score no longer depends on another candidate's timestamp. Thus adding a lower-ranked distractor cannot change the displayed pair's scores. Returning a new high-scoring candidate may legitimately change top-k membership; that is not the property tested here.

This alternative does **not** determine whether a newer memory is true, interpret a historical query, recover an update missing from the candidate pool, distinguish ingestion time from event time, persist contradiction links, or guarantee that a newer item always outranks a much more relevant one. No history is deleted. Maintainers still need to choose timestamp semantics, opt-in behavior and the ranking policy. We did not implement a production framework change while its approach is undecided.

## Executed checks

`python verify.py --source /path/to/pinned/scoring.py --out results.json`

18 control tests passed, zero failures/errors/skips. One control contains a 48-case matrix: four fixed hybrid-signal settings × two archive dates × six input permutations. All 48 exhibited the original pair reversal; all 48 preserved both pair scores under the fixed-clock reference. These are parameter combinations for one mechanism, not 48 new bugs or contributions.

Other controls cover disabled recency, below-threshold candidates, input nonmutation, updated_at precedence, UTC-offset equivalence, absent/unparseable dates, a strong-relevance counterexample, tied dates, bounded future dates, missing candidates, invalid reference parameters and empty results. This is a source-level Linux/CPython 3.13.5 experiment in the current assistant execution environment, not hosted CI, independent human review, or a replay of the reporter's LLM accuracy claims.

See `SUMMARY.json` for the compact execution receipt and `test.log` for actual unittest output. The 48 row-level observations and exact source copy are retained in the conversation evidence ZIP. To supply the source yourself, fetch `mem0/utils/scoring.py` at the pinned commit from `Kylinny/mem0`; mismatched bytes are rejected. The harness makes no network requests.

AI assistance: Zero performed this analysis, code preparation and execution under Youngseok Oh's direction. No independent human execution is claimed. Our public signature does not imply maintainer acceptance, a merged fix, funding, or endorsement. The original reporter's work and Kylinny's candidate remain theirs.
