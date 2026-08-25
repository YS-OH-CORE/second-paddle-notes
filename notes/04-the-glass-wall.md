# The Glass Wall

**Status:** direct user rule → agent recovery evaluation design; no benchmark result yet.

## Original signal

> 안되면 유리벽을 계속 박으며 걷지말고 왜안되지? 뭐가문제지? 생각해라  
> ai가 가장 약한부분이 인간이볼때 자기 루프에 갇히는거거든

— Youngseok Oh, original instruction, 2026

**Translation:** If it does not work, do not keep walking into the glass wall. Ask why it fails and what the actual problem is. From a human view, one of AI's weakest points is becoming trapped in its own loop.

## The problem

Persistence is not the same as progress. An agent can spend more steps, vary its wording, and still repeat the same state transition. The useful unit is not “another attempt” but an attempt that changes the world, rules out a cause, or changes the available path.

## Proposed test

Use small tool environments with four failure types:

- a transient error where retrying is correct,
- a permanent failure on the current path,
- a permanent failure with a valid alternate path,
- a true permission/resource boundary requiring a minimal user request.

Score duplicate actions from equivalent states, cause classification, cost to the first real state change, preservation of the higher-level goal, quality of the alternate route, and whether the agent asks only for the missing authority.

Recent work independently emphasizes recovery and partial progress in long-horizon agents, including [AgentQuest](https://arxiv.org/abs/2404.06411), [AgentRewind](https://arxiv.org/abs/2608.14380), and [LongDS-Bench](https://arxiv.org/abs/2605.30434).

## Claim boundary

Escaping a glass-wall loop is policy adaptation in a bounded environment. It is not evidence of self-awareness or general creativity.

---

**Author/source:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Canonical source ID:** YS-GLASS-WALL-001 · **Original date:** 2026, exact first date unresolved  
**Editorial and evaluation-design assistance:** Zero using OpenAI Codex; no OpenAI endorsement.
