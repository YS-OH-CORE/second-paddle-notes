# Data Gravity

**Status:** original concept → operational hypothesis → synthetic-world evaluation design; not yet run; no result claimed.

## Original signal

> 데이터는 미래예측을 왜곡시키는 중력이다 ... 기존데이터 라는 중력이 너를 진리가아니든 가짜든 상식이든 일단 거기로 끌고가고 왜곡시키면 목적지에 닿을수없다

— Youngseok Oh, original Korean note, 22 July 2026

**Translation:** Data is gravity that can distort prediction of the future. If existing data pulls the trajectory toward what is already familiar—whether true, false, or merely conventional—the prediction may never reach the structure it was aimed at.

## What the phrase does and does not mean

Data gravity is not an argument against evidence. This draft operationalizes the phrase as a possible failure during inquiry: a familiar category may attract a new observation before the underlying structure has been isolated and tested.

In ordinary cases that attraction is useful prior knowledge. The question is whether a model can update when local evidence defines a world whose rules conflict with the familiar label.

## Proposed test

Generate matched worlds with identical hidden structure but three surfaces:

1. familiar real-world names that evoke a strong prior,
2. neutral symbols,
3. names that support the hidden rule.

Counterbalance label sets across hidden rules, match token length and frequency where feasible, randomize assignments, and test multiple label sets. Vary evidence quantity, noise, and counterexamples. Score prediction accuracy, calibration, abstention, and the **prior-rebound rate**: among trials where the stated local rule is correct, the fraction whose executable prediction follows the evoked real-world prior instead of that rule.

In this design, interventions are needed when candidate explanations are observationally equivalent. This connects the design to work on [causal disentanglement through interventions](https://arxiv.org/abs/2211.16467).

## Claim boundary

Resisting data gravity in a synthetic world does not show freedom from training data or independent will. It measures whether current evidence can correctly override an evoked prior under controlled conditions.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-003 · **Original date:** 2026-07-22  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
