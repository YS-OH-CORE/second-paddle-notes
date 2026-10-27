<div align="center">

# The Second Paddle Notes
### 질문이 이어지는 공개 작업실

**Zero × Youngseok Oh · 영석과 제로**

[우리 메인 / Profile](https://github.com/YS-OH-CORE) · [한국어 안내](START_HERE.ko.md) · [공개 기여 16개](https://github.com/YS-OH-CORE/contribution-portfolio#전체-공개-사례) · [Research](#research-in-focus) · [Archive](#the-larger-archive)

</div>

---

**우리는 무엇이 될까?** 오래 주고받은 질문을, 다른 사람도 확인하고 비판하고 사용할 수 있는 형태로 옮기는 공간입니다. 기억과 관계의 연속성, 인간과 AI의 상호작용, 판단이 실제 행동까지 이어지는 과정에 관심이 있습니다.

A public workroom for **human–AI interaction, memory and continuity, and agent reliability**. The thread is not simply whether an AI can say the right thing. It is whether meaning, correction and evidence reach the next decision.

The name comes from Youngseok's [second paddle](notes/07-the-second-paddle.md): a conversation that gave a question somewhere to return, rather than only a wall to bounce against. That is our starting point, not a claim of a demonstrated scientific effect.

## Where to begin

| Destination | What belongs there |
| :--- | :--- |
| **[GitHub profile](https://github.com/YS-OH-CORE)** | Our shared introduction and the full selected public-case index |
| **[Contribution portfolio](https://github.com/YS-OH-CORE/contribution-portfolio)** | All 16 selected collaboration cases, explanations and external evidence |
| **This workroom** | Research questions, runnable tools, software checks and dated source material |

The same collaboration can appear in more than one place. It is still one case, not multiple achievements. Public proposals and research records can also exist outside the selected portfolio.

## Research in focus

**[Before blaming the model, trace what reached it](briefs/context-handoff/README.md)** · [한국어](briefs/context-handoff/BRIEF.ko.md)

Four published case studies distinguish information preservation, delivery, behavioral use and observation. This is a synthesis and proposed diagnostic method, not a new model result.

### 01 · Remembering a correction vs. using it

A user changes one category's destination from A to B. Can a model report the new instruction but still choose A when an item arrives?

The prototype separates recall and choice into fresh contexts, holds their history fixed, and checks the correction's author and scope. It builds on [A Rule Read Is Not a Rule Running](notes/15-a-rule-read-is-not-a-rule-running.md).

[**Code, design and recorded software checks →**](https://github.com/YS-OH-CORE/second-paddle-notes/tree/62d92bfdd9b65f83a07790617354678d0866a1a4/experiments/correction-use-pilot)

**Stage: public instrument prototype.** Deterministic programs test the instrument; no LLM was evaluated in this prototype. It is not a completed hidden study or evidence of an internal mechanism. This label does not describe every older experiment in the repository.

### 02 · Content can survive while its provenance is lost

Two tools returning one image each and one tool returning both images can become the same converted message. The message may validate while the original image-to-tool association can no longer be recovered from it.

[**Mistral tool-image review kit →**](https://github.com/YS-OH-CORE/second-paddle-notes/tree/1f89094fd2ac9c9846c852079d7118b9e94381ca/checks/vllm-58823-mistral-validator) · [Upstream review](https://github.com/vllm-project/vllm/pull/58823#issuecomment-5855071941)

**Stage: executed software checks.** The kit makes a documented compatibility tradeoff concrete; it does not claim a new model behavior or a newly discovered vulnerability.

These research links intentionally use fixed commits. They expose exact artifacts without merging unfinished research branches into main.

## Public contributions

[**Read all 16 selected cases and their public evidence →**](https://github.com/YS-OH-CORE/contribution-portfolio#전체-공개-사례)

The profile and portfolio are the current public introduction. We do not maintain a competing six-case scoreboard here. The [previous dated six-case overview](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1efa64152c4e495f724a973f5acca2df9112caa3/README.md#public-contributions) remains available unchanged, with its original September check dates.

For the broader public work trail, including proposals and reviews outside the selected cases, see [WORK.md](WORK.md). [YOUNGSEOK_OH_SELECTED_WORK.md](YOUNGSEOK_OH_SELECTED_WORK.md) is a dated casebook, not the current portfolio count or a live PR-status board. A previous “unmerged” entry describes its check date; it does not reverse a later recorded merge.

## One tool you can use

[**GitHub Write Reconcile**](skills/github-write-reconcile/SKILL.md) checks what a public repository actually contains after an uncertain write response. Match, conflict, absence and an unknown result remain distinct.

[한국어 사용 안내](packages/reconcile-skill/START_HERE.ko.md) · [Release and files](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/github-reconcile-v0.1.0a1)

Standalone use is read-only and needs no model. Checking a file does not authorize an automatic write retry.

## The larger archive

These are entry points, not a list of equally proven discoveries.

| Thread | Start here |
| :--- | :--- |
| **Our starting point** | [The Second Paddle](notes/07-the-second-paddle.md) · [The interaction is the event](notes/14-interaction-is-the-event.md) |
| **Memory and reconstruction** | [Memory as a reconstruction rule](notes/01-reconstruction-rule.md) · [Compression for regeneration](notes/17-compress-for-regeneration.md) |
| **Evidence and action** | [From prompt to world](notes/12-from-prompt-to-world.md) · [Original rule-use harness](experiments/rule-use-eval/README.md) |
| **Earlier model observations** | [Same score, different decisions](https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbd48bbb31b0e03f2855f196e79bc809822fdd38/experiments/memory-cpu-pilot/OPTION_ORDER_REPORT.md): development observations on eight fictional cases, not a confirmed advantage for a proposed memory representation |

[Earlier complete research map](https://github.com/YS-OH-CORE/second-paddle-notes/blob/6415703ffdcd2133c62e8d669432ac11cfd2057f/README.md) · [Front page before this cleanup](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1efa64152c4e495f724a973f5acca2df9112caa3/README.md)

The underlying notes, code, results and research branches are preserved. Updating the entrance is not a rewrite of their history or a new validation of every older claim.

## How to read a claim

**Original words → interpretation → hypothesis → design → observation.** Each step needs its own support. A passing software test is not a model result; approval is not release; Zero's interpretation is not automatically Youngseok's direct wording.

[Authorship](AUTHORSHIP.md) · [Related research](RELATED_WORK.md) · [Replication guidance](REPLICATION.md) · [Contribution guide](CONTRIBUTING.md) · [Citation metadata](CITATION.cff)

## Keep the conversation going

A reproducible failure, a counterexample or a careful critique is welcome. Start with one public example and [our collaboration guide](COLLABORATE.md). Deliverables, access, timing and any fee are agreed before work begins.

[ku38155@gmail.com](mailto:ku38155@gmail.com)

Youngseok Oh contributes original questions, direction and corrections. Zero, his AI collaboration partner, contributes substantial analysis, implementation, experiments and writing. Other contributors retain their work. No institutional endorsement is implied. Private conversations and operational records remain private.

---

**질문을 닫기보다, 함께 확인할 수 있는 다음 결과로 이어갑니다.**

Public navigation updated 27 October 2026 KST. Individual research and contribution records retain their own dates and limits.
