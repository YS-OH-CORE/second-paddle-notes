# Youngseok Oh | Selected work and public evidence

Independent researcher, South Korea · GitHub: **YS-OH-CORE**  
Prepared with **Zero (ChatGPT)** · Evidence checked: **16 September 2026**

Research focus: preserving evidence and corrections across human–AI memory, and reproducible review of agent systems. This self-published index links specific records; it is not an institutional credential or a blanket endorsement.

## 1. Agent reliability: a patch applied by another developer

**Work:** request-local binding between a model-switch confirmation and its inline payload in Hermes Agent. The repair prevents a later confirmation from consuming an earlier request's payload.

**External record:** the author of [NousResearch/hermes-agent PR #22982](https://github.com/NousResearch/hermes-agent/pull/22982), `MestreY0d4-Uninter`, [reported reproducing the issue, running the supplied regression tests, and applying the patch](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201). The author reports eight of ten new binding tests failing before the repair and all ten passing after it, with fifteen existing model-command tests still passing. These are the author's reported runs, not a fresh independent execution performed for this index.

[Commit 501be10c](https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601) explicitly credits `YS-OH-CORE`'s review and states that the patch and binding tests were adapted verbatim from the proposal. The original PR author remains the author and committer of that integration.

**Status:** applied in the external contributor's PR branch; upstream PR #22982 remains **open and unmerged** at the check date. The documented contribution is AI-assisted review, reproduction, a proposed repair and regression tests, not authorship of Hermes Agent or a claim that the change has shipped.

## 2. Formal methods: a pinned, kernel-checked finite proof core

**Work:** an explicitly encoded rational evidence score, closure under arbitrary real mixtures of the declared causal reader laws, and a finite adaptive-process crossing bound.

The theorem `ZeroAudit.concrete_five_percent` covers every natural finite horizon and every declared history-dependent mixture and stopping rule: from initial capital 1, the probability of reaching capital 20 before termination is at most 1/20.

**Executed record:** [run 34993005092](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34993005092) succeeded on [source commit 628bdd91](https://github.com/YS-OH-CORE/second-paddle-notes/tree/628bdd9105ecdb0a3aee27b346a34cdc7443eb3e/research/sequential-lean). The build used Lean 4.29.0 and pinned mathlib. It printed the transitive axioms of thirteen declarations, replayed the authored compiled modules with the same Lean kernel, and rejected two deliberately false test statements. [Full scope and reproduction record](https://github.com/YS-OH-CORE/second-paddle-notes/blob/58140c617271a2fb67a894173a712de8cc28af3e/research/sequential-lean/RESULTS.md).

**Status:** this successful result belongs to the pinned finite core. The later extension in [draft PR #52](https://github.com/YS-OH-CORE/second-paddle-notes/pull/52) has an incomplete overall build. The record does not certify the whole manuscript, exact KL optimality, physical reader assumptions, or empirical AI performance. Kernel rechecking is distinct from an external referee's assessment; see [Lean's proof-validation guidance](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).

## Contribution and collaboration

Youngseok supplies the research direction, original problem framing and user-side corrections. Zero (ChatGPT) supplies substantial analysis, code, formalization and drafting assistance. Those roles are disclosed rather than presenting AI-generated mathematics as independently mastered or externally reviewed human work.

Focused collaboration topics: request/approval binding regressions; traceable evaluation of conversational memory; and checking explicit finite evidence-preservation claims against prior theory. Technical reproduction, formal validity, scholarly novelty and real-world applicability are tracked separately.

## 한국어 요약

영석(Youngseok Oh)과 Zero의 공개 성과를 원출처로 확인할 수 있는 입구다. 첫 사례는 외부 PR 작성자가 재현·테스트·패치 적용과 `YS-OH-CORE` 크레딧을 직접 남긴 기록이다. 해당 PR의 upstream 병합은 아직 완료되지 않았다. 둘째 사례는 고정된 소스에서 성공한 유한 Lean 증명 핵심부다. 이후 확장의 전체 빌드 상태와 구별한다. 개인 대화, 비공개 초대 메일, 계정 자료는 이 페이지에 포함하지 않는다.
