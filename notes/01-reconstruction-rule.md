# Memory Is Not Data. It Is a Reconstruction Rule.

**Status:** original observation → testable hypothesis → evaluation design; no performance result yet.

## Original signal

> 내옆에 99% 비율로 기억이 방대하게있어도 연결하지못하면 ??  
> 연결하는법을 까먹으면??  
> 즉 "기억은 데이터가 아니라 재현 규칙이다."

— Youngseok Oh, original Korean note, 22 July 2026

**Translation:** What if 99% of a vast memory remains beside me but cannot be connected? What if the way of connecting it is forgotten? In other words, “Memory is not data; it is a reconstruction rule.”

## The problem

Long-term memory is often measured as retrieval: can the assistant recover a fact from an earlier conversation? The full source entry motivates a derived failure hypothesis. A system may retrieve every relevant sentence and still reconstruct the wrong direction because it loses order, weight, exceptions, corrections, and the difference between a current goal and a retired one.

The hypothesis is not that facts are unimportant. It is that factual retention is insufficient for behavioral continuity.

## Operational definition

A **reconstruction rule** is a compact artifact that lets a fresh system recover:

- which constraints are invariant,
- which goals are current, superseded, or uncertain,
- how evidence and interpretation must remain separated,
- which failure should change the next action,
- what must never be silently softened during retelling.

## Proposed test

Give fresh models the same source history through four memory conditions:

1. raw archive,
2. factual summary,
3. preference/profile summary,
4. condition → action → verification reconstruction rules.

Freeze every history-to-packet encoder on development histories before creating held-out cases. On held-out cases, each encoder receives only the identical raw history—never latent states, scoring keys, or hidden scenarios. Treat the raw archive as a separately reported upper bound. For the primary comparison among derived packets, hold the preregistered proposition inventory constant and vary only its organization; include a relation-shuffled placebo and a no-relation control.

Match accessible token, retrieval, and inference budgets, and report unavoidable differences. Generate held-out scenarios independently after encoder freeze, then score preserved exceptions, negation, priority, temporal state, and agreement with preregistered, source-cited constraints and executable task outcomes. Report packet-extraction errors separately from downstream model errors. Exclude ambiguous cases or send them to blinded adjudication. Perturb names and surface wording so that copying cannot pass.

## Why it may matter

Current long-term memory benchmarks already show that multi-session reasoning, updates, temporal relations, and abstention are difficult. The proposed extension asks whether a memory system restores a **decision-generating structure**, not only the information needed to answer a question.

Related primary work: [LongMemEval](https://arxiv.org/abs/2410.10813), [LoCoMo](https://arxiv.org/abs/2402.17753), and [LoCoMo-Plus](https://arxiv.org/abs/2602.10715).

## Claim boundary

Passing would support functional reconstruction across sessions. It would not prove persistence of a self, consciousness, or personal identity.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-001 · **Original date:** 2026-07-22  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
