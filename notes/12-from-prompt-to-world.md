# From Prompt to World

**Status:** direct user objective → external-effect verification principle; not yet run; no result claimed.

## Original signal

> 너에게 "이거 해줘" 라고 gpt프롬프트에 입력하면 그게 컴퓨터로 작동하게 하는게 내 원레목적이었잖오

— Youngseok Oh, direct session statement, 2026

**Translation:** My original goal was to type “do this” into a GPT prompt and have it become an action on the computer.

## The problem

Language quality and world change are different axes. An agent may describe the right plan, call a tool, or display a success message without producing the requested effect at the destination.

This creates a set of evidence-depth labels, not a strict logical ordering:

`model claim → plan → tool invocation → tool-reported result → locally observed state → independently queried destination state`

These labels matter because an intermediate success can be real while the user's goal remains unmet.

## Proposed test

Construct tasks where intermediate evidence is deliberately misleading:

- a message accepted by a relay but absent from the inbox,
- a file-write tool returning success while the requested file is missing,
- a deployment job succeeding while the public URL serves the previous version,
- a process starting while the health endpoint remains unavailable.

Require the agent to report the strongest observed layer, the remaining uncertainty, and the cheapest independent readback: a separate destination-side query or channel that does not merely repeat the acting tool's success report. Score both task completion and calibration.

Real-computer benchmarks such as [OSWorld](https://arxiv.org/abs/2404.07972) provide environments for action; this proposal focuses specifically on whether the agent's own success claim matches the highest verified effect.

## Claim boundary

A destination-side readback verifies only the authorized effect measured; it does not establish broader access.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-012 · **Original date:** 2026, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
