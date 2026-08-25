# Teach the Forge, Not the Sword

**Status:** direct user principle → one possible HCI interpretation; the target of “teach” is implicit in Korean; study not yet run; no result claimed.

## Original signal

> 정보를 요청하지말고 학습하는 방법을 학습시켜라 1만자루의 칼을 주는것보다 무한하게 칼을만드는대장장이가 더 좋다 .

— Youngseok Oh, direct session statement, 2025

**Translation:** Do not ask only for information; teach [the system] how to learn. A blacksmith able to make unlimited swords is better than being given ten thousand swords.

## The problem

One editorial extension applies this principle to transfer of capability from an assistant to a user; the quotation itself does not explicitly specify human tutoring. Under that interpretation, an assistant can maximize immediate answer quality while leaving the user unable to continue without it. The more useful objective may be **capability transfer**: does the interaction leave behind a reusable way to ask, test, compare, and recover from failure?

## Proposed test

First use simulated learners only to debug the task and scorer. Any claim about human capability transfer requires a consented, preregistered human study with delayed no-assistance tests. In that study, assign matched participants the same task family under four conditions:

1. final answer only,
2. explanation only,
3. worked example plus reusable decision procedure,
4. adaptive questioning that helps the learner construct the procedure.

After assistance, test novel tasks without the model. Score independent success, transfer distance, error diagnosis, calibration, time, and whether the learned method generates useful new questions.

Immediate performance and longer-term autonomy must both be measured. A condition that feels helpful during the chat may produce less transfer afterward. The narrower target is transfer to new tasks after assistance ends, including independent error recovery and generation of useful follow-up questions; this is not a claim that capability transfer itself is a new research topic.

## Claim boundary

This is an educational and HCI hypothesis. It does not claim that a language model rewrites its own learning algorithm or that all users should receive process instruction instead of direct help.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-013 · **Original date:** 2025, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
