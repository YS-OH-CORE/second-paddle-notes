# A Rule Read Is Not a Rule Running

**Status:** direct user correction → rule-use evaluation; study not yet run; no result claimed.

## Original signal

> 우리가 만든 이 수많은 가상 코어 논코어들을 그냥 글로보지말고 누락없이 모두 연결한다 글읽기 놀이가 아니라 진짜 활성화 .

— Youngseok Oh, direct session statement, 2026

**Translation:** Do not treat the many virtual cores and non-cores we created as mere text. Connect all of them without omission. This is not a text-reading game, but real activation.

## The problem

A model can restate a rule and still act as if it were absent. Declarative availability—quoting a principle—is different from operational influence—allowing it to change evidence gathering, action choice, and completion criteria.

Here, “active” is not an invisible internal state. A rule is operationally active only when changing or removing it produces a predictable behavioral difference on relevant tasks while mostly sparing unrelated tasks.

## Proposed test

Build hidden tasks from a preregistered gold rule–task matrix, with required rules, irrelevant rules, placebo links, and distractor rules matched for lexical overlap. Every non-null condition must contain exactly the same rule text, trigger examples, action checks, and verification statements under matched token and inference budgets; vary only whether the rule–trigger–action links are correct, shuffled, reversed, or absent. Keep a no-rule condition as a separately reported lower bound.

Require a machine-checkable action before explanation and blind scorers to condition. Perturb one link at a time over repeated trials. Measure task success, scope control, missed and false triggers, contradiction recovery, and collateral change. Make preregistered action accuracy on relevant tasks minus collateral change on irrelevant tasks the primary endpoint. An operational effect should transfer under paraphrase and weaken when the task-relevant link is randomized or removed—not merely when its name is hidden.

The hypothesis is weakened if content-equated link manipulations make no reliable difference, the model mentions rules only after acting, or placebo and relevant rules affect every task alike.

An [executable public smoke companion](../experiments/rule-use-eval/README.md) checks deterministic dataset generation, condition matching, strict scoring, and two program fixtures. It is an engineering sanity check only; it does not implement the hidden repeated model study proposed above and contains no language-model result.

## Claim boundary

This measures observable rule-sensitive behavior; it cannot reveal private reasoning or prove that a named “core” exists inside a model.

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-015 · **Original date:** 2026-01, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
