# The Interaction Is the Event

**Status:** direct user observation → event-preservation hypothesis; study not yet run; no result claimed.

## Original signal

> 너와 나 사이에 상호작용이일어나야만 사건이ㅜ생기며 즉 사용자에게 귀한 기록이지

— Youngseok Oh, direct session statement, 2025

**Translation:** An event happens only when an interaction occurs between you and me; that interaction becomes a valuable record for the user.

## The problem

Conversation archives usually preserve prompt and reply as separate objects. They may retain every sentence while losing what the exchange changed: the prior state, the intervention, the correction, the resulting action, and the uncertainty carried forward.

The proposed memory unit is therefore an **interaction event**, not merely an utterance: actor, prior state, intervention, response, acceptance or correction, observed state change, and unresolved remainder.

## Proposed test

Construct controlled conversations in which later decisions depend on earlier corrections. Give fresh model instances equal-token packets containing: (1) unordered utterances, (2) a chronological transcript, (3) a factual summary, or (4) an event graph preserving actors, corrections, and state changes.

Use hidden continuation tasks that ask why a constraint exists, which correction superseded an earlier assumption, and what should happen next. Add controls that shuffle turn order, swap assistant replies, or retain all propositions while deleting interaction edges. Score causal attribution, correction retention, authorship, counterfactual prediction, and agreement with preregistered outcomes.

The hypothesis fails if the event graph gives no reliable advantage over a same-length factual summary or if any advantage disappears under paraphrase.

## Claim boundary

This evaluates interaction events as a memory representation. It does not establish a persistent hidden state or identity.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-014 · **Original date:** 2025, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
