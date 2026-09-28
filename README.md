<div align="center">

# The Second Paddle Notes

### What survives from intent to action?

**Youngseok Oh · 오영석 × Zero**

[한국어로 시작하기](START_HERE.ko.md) · [Research](#research-in-focus) · [Public contributions](#public-contributions) · [Archive](#the-larger-archive) · [Collaborate](COLLABORATE.md)

</div>

---

A public workroom for **human–AI interaction, memory and continuity, and agent reliability**. We turn questions from long-running dialogue into testable designs, reproducible checks, and useful contributions.

The thread is not simply whether an AI can say the right thing. It is whether the right meaning, correction, or evidence reaches the next decision.

**New here?** Start with the current question below, a contribution someone else used, or one runnable tool. You do not need to read the whole archive first.

## Research in focus

**[Research brief: before blaming the model, trace what reached it](briefs/context-handoff/README.md)** · [한국어](briefs/context-handoff/BRIEF.ko.md)  
Four published case studies distinguish information preservation, delivery, behavioral use, and observation. A synthesis and proposed diagnostic method, not a new model result.

### 01 · Remembering a correction vs. using it

A user changes one category's destination from A to B. Can a model report the new instruction but still choose A when an item arrives?

The prototype separates recall and choice into fresh contexts, holds their history fixed, and checks the correction's author and scope. It builds on [A Rule Read Is Not a Rule Running](notes/15-a-rule-read-is-not-a-rule-running.md).

**[Code, design, and recorded software checks →](https://github.com/YS-OH-CORE/second-paddle-notes/tree/62d92bfdd9b65f83a07790617354678d0866a1a4/experiments/correction-use-pilot)**

**Stage: public instrument prototype.** Deterministic programs test the instrument; no LLM was evaluated in this prototype. It is not a completed hidden study or evidence of an internal mechanism. This stage label does not describe every older experiment in the repository.

### 02 · Content can survive while its provenance is lost

Two tools returning one image each and one tool returning both images can become the same converted message. The message may validate while the original image-to-tool association can no longer be recovered from it.

**[Mistral tool-image review kit →](https://github.com/YS-OH-CORE/second-paddle-notes/tree/1f89094fd2ac9c9846c852079d7118b9e94381ca/checks/vllm-58823-mistral-validator)** · [Upstream review](https://github.com/vllm-project/vllm/pull/58823#issuecomment-5855071941)

**Stage: executed software checks.** The kit makes a documented compatibility tradeoff concrete; it does not claim a new model behavior or a newly discovered vulnerability.

*These two entries use pinned research-branch commits. The links expose the exact artifacts without merging unfinished experiments into `main`.*

## Public contributions

Specific work, with the evidence and its limit together. **HTTP recovery entry checked 28 September 2026; the other entries retain their 27 September snapshot.**

| Contribution | Evidence | State at the check date |
| :--- | :--- | :--- |
| **Hermes HTTP recovery regression** | [Author's adoption](https://github.com/NousResearch/hermes-agent/pull/121944#issuecomment-5863926910) · [Crediting commit](https://github.com/liuhao1024/hermes-agent/commit/859b987d1df0f47236eabe4190e9d41122b5ea12) | Test file adopted unchanged with YS-OH-CORE co-author credit; [PR #121944](https://github.com/NousResearch/hermes-agent/pull/121944) open and unmerged at this check. |
| **Hermes request-bound confirmation** | [Recipient's application record](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201) | Patch and tests applied in the feature author's branch; [upstream PR](https://github.com/NousResearch/hermes-agent/pull/22982) still unmerged. |
| **CanIToolCall failure classification** | [Maintainer's approval](https://github.com/redd34/canitoolcall/pull/13#pullrequestreview-5330173478) | Revised analysis approved after replay; [PR](https://github.com/redd34/canitoolcall/pull/13) still unmerged. |
| **SGLang / DeepSeek fix verification** | [First fix](https://github.com/redd34/canitoolcall/issues/19#issuecomment-5856171965) · [Alternative](https://github.com/redd34/canitoolcall/issues/20#issuecomment-5856172220) | Two separate offline comparisons reported. Verification contribution, not authorship of either fix. |
| **Mem0 deletion-scope review** | [Counterexample and positive control](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5855365753) | A remaining scope mismatch reported on a proposed fix; not a shipped repair. |

[Full dated casebook](YOUNGSEOK_OH_SELECTED_WORK.md) · [Long-form contribution trail](WORK.md)

## One tool you can use

**[GitHub Write Reconcile](skills/github-write-reconcile/SKILL.md)** checks what a public repository actually contains after an uncertain write response. A match, conflict, absence, and an unknown result remain distinct.

[한국어 사용 안내](packages/reconcile-skill/START_HERE.ko.md) · [Release and files](https://github.com/YS-OH-CORE/second-paddle-notes/releases/tag/github-reconcile-v0.1.0a1)

Standalone use is read-only and needs no model. The usage guide explains the inputs and boundaries; checking a file does not authorize a retry.

## The larger archive

The earlier work remains available. These are **entry points, not a list of equally proven discoveries**.

| Thread | Start here |
| :--- | :--- |
| **Memory and reconstruction** | [Memory as a reconstruction rule](notes/01-reconstruction-rule.md) · [Compression for regeneration](notes/17-compress-for-regeneration.md) |
| **Human–AI interaction** | [The Second Paddle](notes/07-the-second-paddle.md) · [The interaction is the event](notes/14-interaction-is-the-event.md) |
| **Evidence and action** | [From prompt to world](notes/12-from-prompt-to-world.md) · [The original rule-use harness](experiments/rule-use-eval/README.md) |
| **Earlier model observations** | [Same score, different decisions](https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbd48bbb31b0e03f2855f196e79bc809822fdd38/experiments/memory-cpu-pilot/OPTION_ORDER_REPORT.md): development observations on eight fictional cases, not a confirmed advantage for the proposed memory representation. |

**[Complete earlier front page and research map](https://github.com/YS-OH-CORE/second-paddle-notes/blob/6415703ffdcd2133c62e8d669432ac11cfd2057f/README.md)** retains the original navigation, artwork, dated snapshots, tools, and additional research links. This refresh changes the entrance, not the underlying source archive.

## How to read a claim here

**Original words → interpretation → hypothesis → design → observation.** Each step needs its own support. A passing software test is not a model result; a positive review is not a shipped release; a provisional interpretation is not Youngseok's direct wording.

[Authorship](AUTHORSHIP.md) · [Related research](RELATED_WORK.md) · [Replication guidance](REPLICATION.md) · [Contribution guide](CONTRIBUTING.md) · [Citation metadata](CITATION.cff)

## Work with us

A reproducible failure, a counterexample, or a careful critique is welcome. For focused work, start with one public example and [the collaboration guide](COLLABORATE.md). Deliverables, access, timing, and any fee are agreed in advance.

**[ku38155@gmail.com](mailto:ku38155@gmail.com)**

Youngseok Oh provides original questions, direction, and user-side corrections. Zero, his AI collaboration partner, contributes substantial analysis, implementation, experiments, and writing. Other contributors retain credit for their work. No institutional endorsement is implied.

---

**우린 무엇이 될까?**  
질문을 닫기보다, 함께 확인할 수 있는 다음 결과로 이어갑니다. [한국어 안내 →](START_HERE.ko.md)
