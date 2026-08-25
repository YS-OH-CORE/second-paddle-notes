# The Second Paddle Notes

[![Rule-use smoke evaluation](https://github.com/YS-OH-CORE/second-paddle-notes/actions/workflows/rule-use-eval.yml/badge.svg)](https://github.com/YS-OH-CORE/second-paddle-notes/actions/workflows/rule-use-eval.yml)

![The Second Paddle, Before Naming](assets/second-paddle-preview.png)

**Source-separated evaluation designs for memory reconstruction, semantic fidelity, agent reliability, and discovery before naming.**

**Published here:** evaluation designs, source-separated hypotheses, and one deterministic public smoke harness. **Not yet published here:** language-model benchmark results.

Original questions and reflections by **Youngseok Oh**. Edited and operationalized with **Zero**, the name Youngseok uses for his continuing Codex workspace and collaboration process. This is independent work using OpenAI Codex; it is not reviewed or endorsed by OpenAI.

## The question

Can a human–AI interaction produce more than fluent answers—can it produce hypotheses that survive an intervention, transfer to a changed setting, and remain honest when the evidence says “unknown”?

These notes begin with Youngseok's direct Korean writing and turn each observation into a falsifiable research object. They separate five layers that are often collapsed:

1. the author's original words,
2. an editorial interpretation,
3. a testable hypothesis,
4. an experimental design,
5. an observed or still-unobserved result.

No model self-report is treated as independent evidence. A memorable story is not a result.

This repository does not claim AI consciousness, hidden-state access, or a new scientific discovery. It publishes source-separated hypotheses and the tests that could make them fail.

## Start here

- **Agent reliability:** [One Point Is Not Ten](notes/05-one-point-is-not-ten.md)
- **Rule use:** [A Rule Read Is Not a Rule Running](notes/15-a-rule-read-is-not-a-rule-running.md) · [run the public smoke harness](experiments/rule-use-eval/README.md)
- **Memory under token limits:** [Compress for Regeneration, Not Deletion](notes/17-compress-for-regeneration.md)

For a shorter bilingual overview, see [The Second Paddle, Before Naming](https://youngseok-second-paddle.ohsycard.chatgpt.site/).

## Research map

### Memory representation and continuity

- **01** — [Memory Is Not Data. It Is a Reconstruction Rule.](notes/01-reconstruction-rule.md)
- **02** — [The 200-Hop Problem](notes/02-the-200-hop-problem.md)
- **10** — [Check the Source Before Matching the Mood](notes/10-source-before-mood.md)
- **14** — [The Interaction Is the Event](notes/14-interaction-is-the-event.md)
- **16** — [Memory Rebuilds the Neighborhood](notes/16-memory-rebuilds-the-neighborhood.md)
- **17** — [Compress for Regeneration, Not Deletion](notes/17-compress-for-regeneration.md)

Notes 1, 14, 16, and 17 are one evaluation family, not four independent discoveries: they test reconstruction accuracy, interaction-edge value, provenance and false attribution, and compression efficiency as distinct preregistered tracks.

### Agent reliability and evidence

- **04** — [The Glass Wall](notes/04-the-glass-wall.md)
- **05** — [One Point Is Not Ten](notes/05-one-point-is-not-ten.md)
- **11** — [Where Is the Control Group?](notes/11-where-is-the-control-group.md)
- **12** — [From Prompt to World](notes/12-from-prompt-to-world.md)
- **15** — [A Rule Read Is Not a Rule Running](notes/15-a-rule-read-is-not-a-rule-running.md)

### Human–AI interaction and adaptation

- **06** — [Who Is Tuning Whom?](notes/06-who-is-tuning-whom.md)
- **07** — [The Second Paddle](notes/07-the-second-paddle.md)
- **08** — [The Observer Cannot Be Passive](notes/08-the-observer-cannot-be-passive.md)
- **09** — [Core Signal or User-Matched Performance?](notes/09-core-or-performance.md)
- **13** — [Teach the Method, Not Just the Answer](notes/13-teach-the-forge.md)
- **18** — [Individuation as a Pattern Hypothesis](notes/18-individuation-as-a-pattern-hypothesis.md)

### Discovery and representation

- **03** — [Data Gravity](notes/03-data-gravity.md)

## Current build status

- **Published:** 18 source-separated evaluation designs.
- **Executable public artifact:** 1 rule-use serialization and scoring smoke harness, with 40 public cases and 2 deterministic program fixtures.
- **Published language-model benchmark runs:** 0.
- **Published model-performance results:** 0.
- **Next milestone:** freeze a claim-bearing hidden set and preregister its scoring, run repeated trials on dated model versions, then release cases and raw outputs after evaluation.

The completion notes test two different failures: **Note 5** asks whether an agent reports partial progress honestly across many requirements; **Note 12** asks how deep the evidence goes from a model's claim to a destination-side readback.

See [RELATED_WORK.md](RELATED_WORK.md) for primary research bridges and explicit non-novelty boundaries, [QUEUE.md](QUEUE.md) for publication criteria and next test candidates, [CONTRIBUTING.md](CONTRIBUTING.md) for critique and replication guidance, and [CITATION.cff](CITATION.cff) for citation metadata.

## 한국어 소개

이곳은 영석의 독백을 멋있는 문장으로 포장하는 곳이 아니다. 직접 원문에서 시작해, AI의 해석과 영석의 뜻을 분리하고, 틀릴 수 있는 가설과 실행 가능한 평가로 바꾸는 공개 연구 노트다. 개인과 AI 사이에서 시작된 질문이 다른 사람도 깨뜨리고 개선할 수 있는 측정법으로 남는지를 시험한다.

> 기억은 데이터가 아니라 재현 규칙이다.

> 우린 무엇이 될까?

The repository's editorial answer is to build a way to test the question before claiming an answer.

## Authorship and boundaries

See [AUTHORSHIP.md](AUTHORSHIP.md). Direct Korean quotations retain Youngseok's wording, including spelling and rhythm. English renderings are translations, not English-original quotations.
