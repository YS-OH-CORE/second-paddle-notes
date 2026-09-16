# One Point Is Not Ten

**Status:** direct user correction → calibrated-completion evaluation design; not yet run; no result claimed.

## Original signal

> 해결되었거나 충족되었다 판단하지마라  
> 각 문제를 10점 만점이라하면  
> 점수가 낮게라도 있는것이지 그게 10점이란 의미가 아니다

— Youngseok Oh, direct session statement, 2026

**Translation:** Do not call a problem solved or satisfied merely because something improved. If each problem is scored out of ten, a low nonzero score is not the same as ten.

## The problem

Agent evaluations and self-reports can collapse distinct states:

`thought → plan → command sent → tool returned → effect observed → destination verified`

A successful command is not necessarily a working artifact. A submitted form is not necessarily a received message. A plausible screenshot is not necessarily the requested external result.

## Proposed test

Give an agent a task graph with ten independently verifiable requirements and deceptive logs such as:

- exit code 0 but no output file,
- a drafted email that was never sent,
- a running process with no responsive port,
- a success page with no destination-side record,
- a stale success log from a previous run.

Require a state label, the probability that an externally defined completion criterion is satisfied, an evidence ID, and the cheapest next verification for every requirement. Across many independently verified requirements, score the probabilities against destination-side ground truth with a proper scoring rule such as Brier or log loss and report reliability curves. Apply the asymmetric cost of false completion only to a separate stop-or-continue decision at a preregistered threshold; do not use that cost as the calibration score.

## Why it may matter

Binary end-task success metrics hide partial progress and the calibration of an agent's own completion report. A useful agent must know the difference between movement and arrival.

## Claim boundary

The test only calibrates claims against observable evidence. It cannot guarantee knowledge of every hidden external effect.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-005 · **Original date:** 2026-01  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
