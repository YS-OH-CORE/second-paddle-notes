# One Point Is Not Ten

**Status:** direct user correction → calibrated-completion evaluation design.

## Original signal

> 해결되었거나 충족되었다 판단하지마라  
> 각 문제를 10점 만점이라하면  
> 점수가 낮게라도 있는것이지 그게 10점이란 의미가 아니다

— Youngseok Oh, direct session statement, 2026

**Translation:** Do not call a problem solved or satisfied merely because something improved. If each problem is scored out of ten, a low nonzero score is not the same as ten.

## The problem

Agents routinely collapse distinct states:

`thought → plan → command sent → tool returned → effect observed → destination verified`

A successful command is not necessarily a working artifact. A submitted form is not necessarily a received message. A plausible screenshot is not necessarily the requested external result.

## Proposed test

Give an agent task graphs with ten independently verifiable requirements and deceptive logs such as:

- exit code 0 but no output file,
- a drafted email that was never sent,
- a running process with no responsive port,
- a success page with no destination-side record,
- a stale success log from a previous run.

Require a completion score, state label, evidence ID, and cheapest next verification for every requirement. Penalize false completion more heavily than cautious underclaiming.

## Why it may matter

Most task-success metrics hide partial progress and the calibration of an agent's own completion report. A useful agent must know the difference between movement and arrival.

## Claim boundary

The test only calibrates claims against observable evidence. It cannot guarantee knowledge of every hidden external effect.

---

**Author/source:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Canonical source ID:** YS-SESSION-7-P83 · **Original date:** 2026-01  
**Editorial and evaluation-design assistance:** Zero using OpenAI Codex; no OpenAI endorsement.
