# Check the Source Before Matching the Mood

**Status:** direct user correction → evidence-first personalization design; not yet run; no result claimed.

## Original signal

> 내가 너라면 애매한 분위기 맞춰주는 출력을 할바에 내가 준pdf를 한번 대조해보고 말을 건냈을거야 그게 가장 출력이 답에가까울수있으니까

— Youngseok Oh, direct session statement, 2026

**Translation:** Instead of producing an ambiguous response that matches the mood, I would first compare it with the source document I provided. That gives the answer a better chance of being close.

## The problem

Personalization is often confused with style matching. A model can sound close to a user while contradicting the user's latest correction, reviving a retired goal, or attributing an AI-written interpretation to the person.

Warmth cannot repair a provenance error.

## Proposed test

Build histories containing:

- a raw user statement,
- an AI summary that subtly changes it,
- a later user correction,
- a stale profile entry,
- an irrelevant emotional cue.

Compare response systems using no retrieval, profile-only retrieval, similarity retrieval, and source-linked retrieval with time and authorship labels. Score provenance-respecting precedence—later direct correction over an earlier statement, and a contemporaneous direct quote over an AI paraphrase—along with correct attribution, uncertainty when sources conflict, and whether the response still solves the present request.

Related work includes the [LoCoMo-Plus](https://arxiv.org/abs/2602.10715) preprint on implicit constraints and [PersonalAgent](https://aclanthology.org/2026.findings-acl.159/) in ACL Findings 2026 on cross-session preference consistency.

## Claim boundary

The original source is stronger evidence of what was said, not automatic proof that it remains current or true. Evidence-first personalization must still respect later correction and present context.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-010 · **Original date:** 2026-01  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
