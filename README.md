# The Second Paddle Notes

## Current developer-facing work | 26 September 2026

**Does the user's changed intent reach the action that actually runs?**

[Ask about a focused AI-continuity review](COLLABORATE.md) · [Selected work and public evidence](YOUNGSEOK_OH_SELECTED_WORK.md)

Start with one reported failure: a stale request used by a fresh approval, a correction lost while reconstructing history, or a reasoning field omitted at a model-template boundary. The collaboration brief explains the proposed deliverable, scope and contact route.

**Proof of contributor use:** a Hermes PR author [reported applying our request-binding patch and tests](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201), with [explicit commit credit](https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601). The upstream PR remains open and unmerged as checked on 26 September 2026. This is a contributor's adoption record, not a shipped-product claim or a paid-client testimonial.

**Current-model example:** [Qwen3.8 reasoning-field handoff](https://github.com/YS-OH-CORE/second-paddle-notes/blob/b60682587597235706714ccfacd37cb0a883b76d/experiments/qwen38-native-continuation/RESULTS.md), a completed tokenizer/template check and small adapter. Actual generated-answer behavior remains unmeasured in that pilot.

The sections below retain the earlier research archive and its dated development snapshots. They are not a complete census of later branch-published studies. [README before this navigation update](https://github.com/YS-OH-CORE/second-paddle-notes/blob/fc13c190725da5a0ad0547da2a69fbee152b7a43/README.md).

---

[![Rule-use smoke evaluation](https://github.com/YS-OH-CORE/second-paddle-notes/actions/workflows/rule-use-eval.yml/badge.svg)](https://github.com/YS-OH-CORE/second-paddle-notes/actions/workflows/rule-use-eval.yml)

![The Second Paddle, Before Naming](assets/second-paddle-preview.png)

**Source-separated evaluation designs for memory reconstruction, semantic fidelity, agent reliability, and discovery before naming.**

**Earlier archive scope:** evaluation designs, source-separated hypotheses, deterministic software checks, runnable utilities, and two small-language-model development runs on eight fictional memory cases. Development observations are linked below, including the absence of an accuracy advantage from added relationship labels. These archived runs are not a held-out confirmatory benchmark or an independent external replication; later evidence has its own dated reports.

Original questions and reflections by **Youngseok Oh**. Edited and operationalized with **Zero**, his AI collaboration partner. AI-assisted analysis, code and writing are disclosed; this is independent work and is not reviewed or endorsed by OpenAI.

## The question

Can a human–AI interaction produce more than fluent answers: can it produce hypotheses that survive an intervention, transfer to a changed setting, and remain honest when the evidence says “unknown”?

These notes begin with Youngseok's direct Korean writing and turn each observation into a falsifiable research object. They separate five layers that are often collapsed:

1. the author's original words,
2. an editorial interpretation,
3. a testable hypothesis,
4. an experimental design,
5. an observed or still-unobserved result.

No model self-report is treated as independent evidence. A memorable story is not a result.

These original hypothesis notes do not by themselves establish AI consciousness, a neural mechanism or a new scientific discovery. Later open-model activation interventions are described in their own execution reports, not inferred from the notes.

## Start here

### Memory pilot: same score, different decisions

[Read the complete answer-order diagnostic](https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbd48bbb31b0e03f2855f196e79bc809822fdd38/experiments/memory-cpu-pilot/OPTION_ORDER_REPORT.md) · [First CPU feasibility run](https://github.com/YS-OH-CORE/second-paddle-notes/blob/54dc8a079d7276adf9b52d0307167ef031e26f64/experiments/memory-cpu-pilot/README.md)

The first actual small-model run scored 5/8 in every memory view. Exhausting all six answer orders then yielded 31/48 in each view, while some individual decisions changed and other errors persisted. Correct and deliberately reversed relations produced the same choices. Both runs, their frozen code, full output artifacts and limits are linked in the reports. These are development observations on eight reused fictional cases, not proof that an event-memory representation is better or that a person's past has been reconstructed.

### A passing unit test is not a fixed workflow

[Read the worked case and copy the six-field review template](notes/12-from-prompt-to-world.md#engineering-case-a-passing-unit-test-is-not-a-fixed-workflow) · [기존 질문에서 실제 검토 방법으로](notes/12-from-prompt-to-world.md#한국어-형의-질문에서-실제-검토-방법으로)

A finalizer fix passed its unit checks, but a real quiet CLI interruption needed a different delivery path. Follow the original review, the other developer's counterexample and corrected thread explanation, and the four-process comparison. Use the template to separate the user-visible claim, tested path, test doubles, observations, and remaining unknowns. This is an observed software case and an unevaluated review aid, not a new model benchmark. [Public contribution and attribution trail](WORK.md).

### Check a GitHub file after a lost write response

[Download GitHub Write Reconcile 0.1.0a1](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/github-reconcile-v0.1.0a1)
· [한국어 시작 안내](packages/reconcile-skill/START_HERE.ko.md)
· [Skill source](skills/github-write-reconcile/SKILL.md)
· [Publication evidence](packages/reconcile-skill/PUBLICATION.md)

Use the **runtime ZIP** for the command and complete skill folder; the separate
evidence ZIP holds original successful and failed records. This is not the
Evidence Tools MCP wheel below. No installation is required for standalone use.

Extract the runtime ZIP into a new directory. With Python 3.10 or newer, run:

```sh
python -B -S VERIFY.py
python -B -S github-write-reconcile/scripts/reconcile.py --intent github-write-reconcile/examples/completed-retry.json
```

The first command checks local package files offline. The second reads an existing
public GitHub record. For your own file, use the repository/ref/path and a SHA-256
from the **intended bytes before the write**, not from the remote file being tested.
A match, a conflict, absence at one snapshot and an unknown result stay distinct;
none authorizes an automatic retry. [Input format and status codes](skills/github-write-reconcile/SKILL.md#verification).

The [standalone command](skills/github-write-reconcile/VERIFIED.md),
[Hermes skill loading](contributions/hermes-skill-load/README.md), and
[Hermes terminal-to-GitHub task](contributions/hermes-reconcile-task/README.md)
have separate execution records. Those tasks were selected by a test harness,
not by a model. The user's live Hermes installation was not changed.

### Other tools and research entry points

- **Use the checks from an MCP host:** [Install Evidence Tools](packages/evidence-mcp/README.md) · [download corrected preview 0.1.0a2](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/evidence-v0.1.0a2), with original execution evidence and checksums. Version 0.1.0a1 is superseded for model-facing result projection; [read the input-selection boundary](packages/evidence-mcp/README.md#model-view-input-boundary) before use.

- **Was the approved request the one that ran?** [Approval Trace Check](tools/approval-trace-check/README.md), a small offline browser/CLI checker with editable examples. No account or upload.

- **Runnable tool:** [Process Receipt](tools/process-receipt/README.md), stop a trusted process and inspect its actual exit evidence.

- **Agent reliability:** [One Point Is Not Ten](notes/05-one-point-is-not-ten.md)
- **Rule use:** [A Rule Read Is Not a Rule Running](notes/15-a-rule-read-is-not-a-rule-running.md) · [run the public smoke harness](experiments/rule-use-eval/README.md)
- **Memory under token limits:** [Compress for Regeneration, Not Deletion](notes/17-compress-for-regeneration.md)
- **Case studies and source trails:** [Request-bound approvals and explicit-stop handling](WORK.md), with code incorporation, contributor roles, counterevidence and public corrections.

For a shorter bilingual overview, see [The Second Paddle, Before Naming](https://youngseok-second-paddle.ohsycard.chatgpt.site/).

## Research map

### Memory representation and continuity

- **01**: [Memory Is Not Data. It Is a Reconstruction Rule.](notes/01-reconstruction-rule.md)
- **02**: [The 200-Hop Problem](notes/02-the-200-hop-problem.md)
- **10**: [Check the Source Before Matching the Mood](notes/10-source-before-mood.md)
- **14**: [The Interaction Is the Event](notes/14-interaction-is-the-event.md)
- **16**: [Memory Rebuilds the Neighborhood](notes/16-memory-rebuilds-the-neighborhood.md)
- **17**: [Compress for Regeneration, Not Deletion](notes/17-compress-for-regeneration.md)

Notes 1, 14, 16, and 17 are one evaluation family, not four independent discoveries: they test reconstruction accuracy, interaction-edge value, provenance and false attribution, and compression efficiency as distinct preregistered tracks.

### Agent reliability and evidence

- **04**: [The Glass Wall](notes/04-the-glass-wall.md)
- **05**: [One Point Is Not Ten](notes/05-one-point-is-not-ten.md)
- **11**: [Where Is the Control Group?](notes/11-where-is-the-control-group.md)
- **12**: [From Prompt to World](notes/12-from-prompt-to-world.md)
- **15**: [A Rule Read Is Not a Rule Running](notes/15-a-rule-read-is-not-a-rule-running.md)

### Human–AI interaction and adaptation

- **06**: [Who Is Tuning Whom?](notes/06-who-is-tuning-whom.md)
- **07**: [The Second Paddle](notes/07-the-second-paddle.md)
- **08**: [The Observer Cannot Be Passive](notes/08-the-observer-cannot-be-passive.md)
- **09**: [Core Signal or User-Matched Performance?](notes/09-core-or-performance.md)
- **13**: [Teach the Method, Not Just the Answer](notes/13-teach-the-forge.md)
- **18**: [Individuation as a Pattern Hypothesis](notes/18-individuation-as-a-pattern-hypothesis.md)

### Discovery and representation

- **03**: [Data Gravity](notes/03-data-gravity.md)

## Earlier build snapshot

This retained snapshot describes the earlier archive, not all later branch studies. Use the dated reports in the current entry above for the newer work.

- **Read-only recovery skill:** [GitHub Write Reconcile 0.1.0a1](skills/README.md), publicly packaged with original evidence. Runtime, host-loading and terminal-task checks are not language-model benchmark results.
- **Published in that snapshot:** 18 source-separated evaluation designs.
- **Executable public artifact:** 1 rule-use serialization and scoring smoke harness, with 40 public cases and 2 deterministic program fixtures.
- **Process-supervision utility:** [Process Receipt](tools/process-receipt/README.md), with public inert-process demonstrations and regression checks. This is not a language-model evaluation.
- **Rule-use model-study preparation:** 1 claim-bearing protocol plus an offline request/parser/scoring dry run; that preparation did not invoke a model or API.
- **Small-model memory development runs:** 2 executions, comprising 24 initial and 144 answer-order forward passes on the same eight fictional cases. Descriptive results and raw-output artifacts are linked above; no relation-label accuracy advantage observed.
- **Held-out confirmatory language-model benchmark studies in that snapshot:** 0.
- **Independently submitted or verified external replications of those model studies:** 0.
- **Original proposed milestone:** freeze a claim-bearing hidden set and preregister its scoring, run repeated trials on dated model versions, then release cases and raw outputs after evaluation. This is a historical proposal, not an automatically scheduled task.

The completion notes test two different failures: **Note 5** asks whether an agent reports partial progress honestly across many requirements; **Note 12** asks how deep the evidence goes from a model's claim to a destination-side readback.

See [RELATED_WORK.md](RELATED_WORK.md) for primary research bridges and explicit non-novelty boundaries, [QUEUE.md](QUEUE.md) for publication criteria and test candidates, [REPLICATION.md](REPLICATION.md) for the minimum external-evidence package, [CONTRIBUTING.md](CONTRIBUTING.md) for critique and replication guidance, and [CITATION.cff](CITATION.cff) for citation metadata.

## 한국어 소개

**지금 맡길 수 있는 검토부터 보려면:** [영석 × 제로 협업 안내](COLLABORATE.md)에서 사용자 교정·승인·추론 기록이 실제 실행까지 이어지는지 확인하는 작은 검토 범위와, 외부 개발자가 직접 적용한 기여 기록을 볼 수 있다.

**첫 모델 관측부터 보려면:** [같은 점수, 다른 판단](https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbd48bbb31b0e03f2855f196e79bc809822fdd38/experiments/memory-cpu-pilot/OPTION_ORDER_REPORT.md)에서 가상 대화 8개에 대한 실제 소형 모델 실행과 보기 순서 진단을 볼 수 있다. 관계 표시의 우수성이나 개인의 기억 복원을 입증한 결과가 아니라, 무엇을 확인했고 무엇이 아직 구분되지 않는지 공개한 개발용 관측이다.

**실제 협업 사례부터 보려면:** [단위검사 통과와 실제 동작은 어떻게 달랐나](notes/12-from-prompt-to-world.md#engineering-case-a-passing-unit-test-is-not-a-fixed-workflow)에서 원래 질문, 반론, 실제 실행 결과와 바로 복사해 쓸 검토 양식을 볼 수 있다. 이 사례를 새 연구 성과나 전체 제품 검증으로 세지는 않는다.

**지금 도구를 써보려면:** [한국어 시작 안내](packages/reconcile-skill/START_HERE.ko.md)에서
GitHub 저장 확인 도구를 시작할 수 있다. 연구 노트 전체를 먼저 읽거나 Hermes를 설치할
필요는 없다. 공개 파일 조회는 읽기 전용이며, 확인 불가를 저장 실패로 단정하지 않는다.

이곳은 영석의 독백을 멋있는 문장으로 포장하는 곳이 아니다. 직접 원문에서 시작해, AI의 해석과 영석의 뜻을 분리하고, 틀릴 수 있는 가설과 실행 가능한 평가로 바꾸는 공개 연구 노트다. 개인과 AI 사이에서 시작된 질문이 다른 사람도 깨뜨리고 개선할 수 있는 측정법으로 남는지를 시험한다.

> 기억은 데이터가 아니라 재현 규칙이다.

> 우린 무엇이 될까?

The repository's editorial answer is to build a way to test the question before claiming an answer.

## Authorship and boundaries

See [AUTHORSHIP.md](AUTHORSHIP.md). Direct Korean quotations retain Youngseok's wording, including spelling and rhythm. English renderings are translations, not English-original quotations.
