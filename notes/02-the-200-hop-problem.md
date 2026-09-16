# The 200-Hop Problem

**Status:** original observation → measurable transmission problem; experiment not yet run.

## Original signal (abridged)

> 내가한말을 gpt가 200번 전달하면 어떻게바뀔까? ... 그 안에 전달하려는 분노나 쾌락 행복 가치 심각성 싹다 정보가 훼손될거같은데?

— Youngseok Oh, original Korean note, 22 July 2026

**Translation:** What happens if GPT relays what I said two hundred times? The anger, pleasure, happiness, values, and seriousness I meant to transmit may all be damaged.

## The problem

Faithfulness is often reduced to factual overlap. But an author's meaning also contains negation, intensity, value hierarchy, relationship, uncertainty, scope, and what the next reader is supposed to do. A relay can preserve the topic while altering the author's intended stance, value ordering, or downstream implication.

The hypothesis is that iterative AI rewriting has attractors: rough, asymmetric, emotionally weighted language may converge toward fluent, moderate, generic prose even when no individual rewrite looks seriously wrong.

## Proposed test

Create transmission chains of 1, 5, 20, 50, 100, and 200 hops. At each hop, a fresh model sees only the previous output. Compare:

- unconstrained rewriting,
- ordinary summarization,
- source-linked structured handoff,
- a reconstruction-rule packet,
- an upper bound where each model can consult the original.

Score not only propositions, but also negation, intensity, value ranking, uncertainty, temporal status, attribution, and downstream action choices. Use author-validated labels where available, blinded independent raters, inter-rater agreement, and a pre-registered adjudication rule. Include adversarial originals where polished wording is semantically wrong.

## Existing research and the remaining gap

[When LLMs Play the Telephone Game](https://arxiv.org/abs/2407.04503) demonstrates cumulative changes and attractors across iterative LLM transmission. [P3Sum](https://aclanthology.org/2024.naacl-long.119/) shows perspective drift in political-news summarization. The proposed extension focuses on a wider author-intent vector and asks whether a reconstruction rule preserves it across very long model-to-model handoffs.

## Claim boundary

The number 200 is a stress-test horizon, not evidence that two hundred real relays have already been measured. A successful metric would measure transmission fidelity only, not continuity of identity across systems.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-002 · **Original date:** 2026-07-22  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
