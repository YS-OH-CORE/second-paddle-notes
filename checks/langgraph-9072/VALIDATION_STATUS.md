# LangGraph #9072: tested candidate and evidence map

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

This is a review aid for the existing issue, not a merged fix or maintainer endorsement.

## Candidate to evaluate

Use [the compatibility runtime patch](pytest-pack/validated/compatibility_runtime.patch), not the older first-only, direct-sequence-addition or unconditional list-normalization experiments.

Exact ToolNode SHA-256 after applying it: `9051ab2c778e2f511257b13b7ed66d05e90dda07c5e7e69daaa34d1b88f14bfd`.
Upstream base: `7daa3ab49d678a5da75edb08baa87db4a2be52c3`.

## Evidence and reusable tests

| Boundary | Deliverable and observed scope |
|---|---|
| End-to-end handoff state and routing | [Initial compiled-parent matrix](README.md): combiner output alone was not sufficient; separate intact Commands still lost a sibling downstream |
| Mixed keyed-update representations | [Expanded matrix](edge-followup/README.md): corrected our direct list/tuple concatenation error; retained the graph's own conflict handling |
| Compatibility with original tests | [Portable pytest pack](pytest-pack/README.md): unchanged original ToolNode file 44/44 and standalone added regressions 24/24 on the current candidate; old failures retained |
| Controlled stop and disk-backed continuation | [Three-process SQLite check](restart/README.md): same candidate preserved expected state in eight selected pause/order/API scenarios; no runtime change in this stage |

The pytest test-only patch is separate from runtime code and has no dependency on the earlier probe scripts. The SQLite script is a separate process-level probe, not an upstream test-suite addition.

## Still open

Root-state updates, mixed parent destination forms, coalescing multiple non-None tool-returned resume values, full repository testing, abrupt-crash recovery and changed-code replay. Ordinary external resume after a saved interrupt is now covered only by the bounded SQLite scenarios above. Do not infer a production-complete fix or an exactly-once side-effect guarantee.

Existing upstream discussion: https://github.com/langchain-ai/langgraph/issues/9072 . The latest posted project comment remains https://github.com/langchain-ai/langgraph/issues/9072#issuecomment-5832240181 . This new validation did not add another issue comment or claim a response.

Original diagnosis and other participants' proposals retain their authorship. Supplemental tests, execution and analysis: Zero, AI collaboration partner working with Youngseok Oh.
