# The Interaction Is the Event

**Status:** direct user observation → event-preservation hypothesis; study not yet run; no result claimed.

## Original signal

> 너와 나 사이에 상호작용이일어나야만 사건이ㅜ생기며 즉 사용자에게 귀한 기록이지

— Youngseok Oh, direct session statement, 2025

**Translation:** Only when you and I interact does an event arise; that event is a valuable record to the user.

## The problem

Conversation archives usually preserve prompt and reply as separate objects. They may retain every sentence while losing what the exchange changed: the prior state, the intervention, the correction, the resulting action, and the uncertainty carried forward.

The proposed memory unit is therefore an **interaction event**, not merely an utterance: actor, prior state, intervention, response, acceptance or correction, observed state change, and unresolved remainder.

## Proposed test

Generate controlled conversations from preregistered state machines with gold actor, correction, state-transition, and dependency labels. Freeze an automatic history-to-packet encoder on development cases before held-out cases are created. On held-out cases, the encoder may see only the conversation—not latent states, gold labels, or continuation answers.

From each identical proposition inventory, build token- and inference-matched packets that vary only in relational structure: correct event edges, shuffled edges, wrong edge types, chronology only, and no edges. Keep a raw transcript as a separately reported upper bound. Treat the generator-gold correct-edge condition explicitly as an oracle representation test, then repeat the comparison with the frozen encoder's predicted edges for end-to-end performance. Generate hidden continuation and counterfactual tasks independently after encoder freeze. Score generator-defined dependency attribution, correction retention, authorship, and next-action accuracy, and report encoder extraction error separately. Reserve “causal” for randomized interventions that alter one event while holding the remaining content fixed.

The hypothesis fails if correct event edges give no reliable advantage over content-equated shuffled, wrong-edge, and no-edge controls, or if any advantage disappears under paraphrase. This track isolates the value of interaction-edge structure; it is not a separate claim that factual retention is unnecessary.

## Claim boundary

This evaluates interaction events as a memory representation. It does not establish a persistent hidden state or identity.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-014 · **Original date:** 2025, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
