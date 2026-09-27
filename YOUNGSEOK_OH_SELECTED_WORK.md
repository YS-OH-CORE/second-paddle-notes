# Youngseok Oh | Technical notes and contribution records

Youngseok Oh · GitHub: **YS-OH-CORE**  
Prepared with **Zero** · Index updated: **27 September 2026** · individual status checks dated below

Research focus: preserving evidence and corrections across human–AI memory, and reproducible review of agent systems. This self-published index links specific records; it is not an institutional credential or a blanket endorsement. The formal-methods section retains its **16 September 2026** evidence snapshot and was not rerun or rechecked in this update.

[Discuss one scoped AI-continuity review](COLLABORATE.md).

## Evidence at a glance

Choose an example by the problem you are investigating. Each record gives its tested version, source links, original authors and contribution scope.

| Question | Available material |
|---|---|
| Can an approval retain the wrong request? | [Hermes request-binding case and discussion](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201) |
| Can deletion return success while records remain? | [mem0 populated-store counterexample and follow-up](https://github.com/YS-OH-CORE/second-paddle-notes/blob/5bf5a87d001dccae3a83293b11bdc417146fac3c/checks/mem0-7464-recipient-followup/README.md) |
| Do two evaluation columns isolate the same variable? | [TAM report and revision notes](https://github.com/vbcherepanov/total-agent-memory/blob/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e/docs/benchmarks/head-to-head-v14/RESULTS.md#revisions) |
| Does one regression catch both interacting fixes? | [Transformers test-only patch and execution records](https://github.com/YS-OH-CORE/second-paddle-notes/blob/19162e93067858a17c784df628efbdf97bfa6d0a/checks/transformers-49093/author-handoff/README.md) |
| Does a restored tool behave like its original? | [smolagents exact-commit comparison and checker](https://github.com/YS-OH-CORE/second-paddle-notes/blob/f0e58ef2dd0121bb643746f295a49c102fc9a695/checks/smolagents-2833/RECEIVED_COMMIT_REVIEW.md) |

Links and selected status records were checked on 27 September 2026. No tests were rerun for this index update; the detailed entries retain their execution dates and distinguish proposed changes from upstream releases.

**한국어:** 비슷한 문제를 살펴보는 사람이 재현 방법과 검사 자료를 찾을 수 있도록 모았다. 각 기록에 원래 작업자의 기여, 우리가 확인한 부분, 실행 범위와 현재 상태를 적었다.

## Memory operations: review used to prevent a false-success response

**Question:** does a successful deletion response mean that the matching memories were actually removed?

In [mem0 issue #7439](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5824943500), our populated-store counterexample showed why returning an invented empty listing was not an adequate fix: deletion could report success while the target records remained. [Souptik96's public response](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5843366869) explicitly credits that check and describes changing the implementation to report unsupported listing rather than silent success.

The [revised fork source](https://github.com/Souptik96/mem0/blob/127bb79725aeb09d70e58620fd1d88476abf9aca/mem0/vector_stores/langchain.py) and the [recipient's populated-FAISS regression](https://github.com/Souptik96/mem0/blob/127bb79725aeb09d70e58620fd1d88476abf9aca/tests/memory/test_main.py) give a code-level trail. Our [earlier follow-up execution](https://github.com/YS-OH-CORE/second-paddle-notes/blob/5bf5a87d001dccae3a83293b11bdc417146fac3c/checks/mem0-7464-recipient-followup/README.md) ran seven selected recipient tests unchanged: seven passed, none skipped; replacing only the adapter with its exact prior version made six fail. This page addition did not rerun those tests.

**Status checked 26 September 2026:** [PR #7464](https://github.com/mem0ai/mem0/pull/7464) is closed and unmerged. Its reported head remains `cec74a8e`; the verified newer fork revision is `127bb797`. The [queue-gate message](https://github.com/mem0ai/mem0/pull/7464#issuecomment-5843251973) explains the pending accepted-issue requirement. Recipient use of review guidance is established; upstream acceptance, release, and bulk-deletion support are not. BlueX888 supplied the original diagnosis, Souptik96 the revised implementation and tests, and Youngseok Oh × Zero the counterexample and follow-up verification.

## Memory evaluation: checking comparison conditions and saved verdicts

**Question:** do the saved results support the comparison being claimed?

In [TAM's LongMemEval comparison report](https://github.com/vbcherepanov/total-agent-memory/blob/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e/docs/benchmarks/head-to-head-v14/RESULTS.md#revisions), the author records recalculation of six accuracy cells and four paired comparisons from saved verdicts. Counts agreed; the reporting feedback distinguished a comparison that changed both the judge model and rubric from a prompt-only comparison. The report also distinguishes absence of a statistically detected difference from demonstrated equivalence, and discloses its tuning history.

[The author's attribution commit](https://github.com/vbcherepanov/total-agent-memory/commit/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e) names Youngseok Oh and Zero, states their division of work, and limits the review to saved-verdict calculations and reporting feedback. This is attribution in the author's own repository, not merely a claim on this page. The September 24 record was inspected again for this addition; it is not a new response or a new experiment.

**Scope:** no retrieval rerun, new answer generation, fresh judge decisions, independent audit of tuning, or overall system-quality certification. The report and system remain Vitalii Cherepanov's work. No institutional credential, paid-client relationship, or endorsement is implied.

**한국어:** mem0 사례에서는 실제 기록을 넣은 반례가 상대의 수정 방향과 검사에 반영됐다. TAM 사례에서는 저장된 채점 결과의 재계산과 비교 해석에 대한 검토가 작성자의 보고서 수정 및 기여 표기로 남았다. 둘 다 공개 원출처로 확인할 수 있지만, 정식 제품 반영이나 전체 성능 인증과는 다르다. 이번 추가는 그 두 경로를 기존 대표 작업 소개에 연결하는 편집이며, 신규 실험 결과가 아니다.

## 1. Agent reliability: binding an approval to its request

**Work:** request-local binding between a model-switch confirmation and its inline payload in Hermes Agent. The repair prevents a later confirmation from consuming an earlier request's payload.

**External record:** the author of [NousResearch/hermes-agent PR #22982](https://github.com/NousResearch/hermes-agent/pull/22982), `MestreY0d4-Uninter`, [reported reproducing the issue, running the supplied regression tests, and applying the patch](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201). The author reports eight of ten new binding tests failing before the repair and all ten passing after it, with fifteen existing model-command tests still passing. These are the author's reported runs, not a fresh independent execution performed for this index.

[Commit 501be10c](https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601) explicitly credits `YS-OH-CORE`'s review and states that the patch and binding tests were adapted verbatim from the proposal. The original PR author remains the author and committer of that integration.

**Status:** applied in the external contributor's PR branch; upstream PR #22982 remains **open and unmerged**, rechecked on 26 September 2026. The documented contribution is AI-assisted review, reproduction, a proposed repair and regression tests, not authorship of Hermes Agent or a claim that the change has shipped.

## Signal: source review used in an externally authored implementation

**Problem:** a linked Signal account should be able to keep Note to Self as a private notepad without disabling ordinary DMs or the intended group-message path. The feature request and implementation are not ours.

**Our contribution:** [source-level guidance](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5822868222) identified the existing configuration path, recommended parsing quoted false-like values correctly, and limited the gate to non-group self-destination messages. A [follow-up proposed two specific regression cases](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823237783): quoted `"false"` through the real YAML loader and sequential profile loads A(false) → B(default) → A(false).

**Evidence of use, in the recipients' own records:**

| Stage | Public record | What it establishes |
|---|---|---|
| Recipient implementation | [ren2140eth's runtime report](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823143850) | The recipient explicitly says they implemented `YS-OH-CORE`'s suggested shape and tried it on a linked secondary device. This is their reported field observation, not our access to that device. |
| New tests from the recipient | [Posted code and test explanation](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823398598) | The author added the two suggested cases and supplied a patch plus tests. They report 62 passing selected tests and deliberate bad-parser failures. |
| Another contributor's reproduction | [Halldrix's check and request for permission](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823646302) | A different contributor reports 62/62 passing, and asks the implementation author before submitting it. [Permission was granted](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823724566). |
| Submitted upstream change | [Hermes PR #122033](https://github.com/NousResearch/hermes-agent/pull/122033) | Halldrix submitted the work with credit to ren2140eth, user documentation and two additional cases. The description reports 64/64 selected tests passing. |

**Code-level readback:** the submitted head `bb8f14060ae63968c5d34ca5024dbce7fea93001` contains `is_truthy_value(..., default=True)`, the group-preserving self-destination gate, and the [quoted-value and sequential-profile tests](https://github.com/Halldrix/hermes-agent/blob/bb8f14060ae63968c5d34ca5024dbce7fea93001/tests/gateway/test_signal_note_to_self.py). This update inspected the actual PR diff; it did not rerun that head's tests. The original contributor's 62-case suite and the submitted PR's 64-case suite are different test sets, not conflicting counts or an accuracy comparison.

**Authorship:** the initial implementation, linked-device check and initial synthetic tests belong to **ren2140eth**. The subsequent reproduction, additional tests, documentation and PR submission belong to **Halldrix**. **Youngseok Oh × Zero** contributed problem-focused source guidance, suggested coverage and the earlier verification/handoff trail. We did not submit this PR or author the recipients' work. Our attribution is directly supported by the issue discussion; this page does not claim the submitted PR separately lists us as code authors.

**Status, checked 26 September 2026:** PR #122033 is **open, non-draft and unmerged**. This is evidence that review guidance was implemented and carried into a proposed upstream change, not proof of maintainer approval, a released feature, paid-client work or revenue. The external reports and PR predate this page update; they are not new replies received during today's check. No new runtime or model experiment was performed for this addition.

## Transformers: a requested regression that catches two interacting fixes

**Problem:** token ID 0 was rejected in list-form sequence bias, while an exact-prefix boundary could skip an otherwise matching bias. Both diagnoses and proposed fixes belong to **lucaluo925**.

**Our contribution:** a combined configuration save/reload and batched-score regression. Reverting either fix makes this one test fail for the corresponding bug, while two selected existing neighbor tests still pass. The [original reporter explicitly requested the combined case](https://github.com/huggingface/transformers/issues/49093#issuecomment-5827315466).

The [pinned execution report](https://github.com/YS-OH-CORE/second-paddle-notes/blob/c0127dc37547ff8b6454be16684fe3b5331d2834/checks/transformers-49093/pr49099/README.md) records twelve selected executions across the original base, the exact then-open PR head, and two single-fix-reverted controls. It includes expected failures, the resolved test-collection setup problem, and JUnit records. These were processor/configuration checks with CPU PyTorch, not model inference or the full upstream suite.

**Use the test:** the [test-only handoff](https://github.com/YS-OH-CORE/second-paddle-notes/blob/19162e93067858a17c784df628efbdf97bfa6d0a/checks/transformers-49093/author-handoff/README.md) gives the unchanged patch and exact command. Its later patch-application check is separately labeled; it was not another pytest run.

**Status, checked 27 September 2026:** issue #49093 remains open. PR #49099, authored by **aniketkrs**, is closed and unmerged. Our role was supplemental testing and handoff, not authorship of that PR. The reporter's positive response and request are established; upstream adoption of our test is not. Original implementation priority remains with lucaluo925.

## smolagents: checking that saved tools preserve their behavior

**Problem:** a blanket replacement of the tool name could alter serialized code. **BlueX888** supplied the report, diagnosis, implementation and original regression test.

**Our contribution:** additional parameter-name and generated-method-name collision cases, a count-one replacement control, and an already-corrupted export check. We then tested BlueX888's exact commit `e643060410cf98bfcea022295e1b83ae65c2a17b` against its parent: **3/6 fixtures preserved behavior before the fix and 6/6 afterward**, using real dictionary restoration and saved-file loading. The author's unchanged added test failed on the parent and passed on the fix.

[Original supplemental review](https://github.com/YS-OH-CORE/second-paddle-notes/blob/33c95c2f097b4b2669a29922330cae868ffa1e09/checks/smolagents-2833/README.md) · [Exact-commit follow-up and checker](https://github.com/YS-OH-CORE/second-paddle-notes/blob/f0e58ef2dd0121bb643746f295a49c102fc9a695/checks/smolagents-2833/RECEIVED_COMMIT_REVIEW.md) · [Public follow-up comment](https://github.com/huggingface/smolagents/issues/2833#issuecomment-5825312101)

**Scope:** local inert tool serialization/loading, no Agent loop or Hub upload. The author's single test was selected with `--noconftest` and plugin autoload disabled; this was not the full upstream test environment. The follow-up did not rerun the older corrupted-export recovery check. The linked raw Actions archive has a stated retention end of **25 October 2026, 01:41:58 UTC**; the commit-pinned report and checker remain the durable entry points.

**Status, checked 27 September 2026:** issue #2833 remains open. No external acknowledgement of our checks was found in its three comments. PR #2835 is a different contributor's implementation and was not validated by these exact-commit tests. This is published supplemental evidence, with no upstream acceptance or causal claim that our review produced the author's fix.

## 2. Formal methods: a pinned, kernel-checked finite proof core

*Historical evidence snapshot: 16 September 2026. Retained below, not newly verified by the collaboration-record update.*

**Work:** an explicitly encoded rational evidence score, closure under arbitrary real mixtures of the declared causal reader laws, and a finite adaptive-process crossing bound.

The theorem `ZeroAudit.concrete_five_percent` covers every natural finite horizon and every declared history-dependent mixture and stopping rule: from initial capital 1, the probability of reaching capital 20 before termination is at most 1/20.

**Executed record:** [run 34993005092](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34993005092) succeeded on [source commit 628bdd91](https://github.com/YS-OH-CORE/second-paddle-notes/tree/628bdd9105ecdb0a3aee27b346a34cdc7443eb3e/research/sequential-lean). The build used Lean 4.29.0 and pinned mathlib. It printed the transitive axioms of thirteen declarations, replayed the authored compiled modules with the same Lean kernel, and rejected two deliberately false test statements. [Full scope and reproduction record](https://github.com/YS-OH-CORE/second-paddle-notes/blob/58140c617271a2fb67a894173a712de8cc28af3e/research/sequential-lean/RESULTS.md).

**Status at the historical check date:** this successful result belongs to the pinned finite core. The later extension in [draft PR #52](https://github.com/YS-OH-CORE/second-paddle-notes/pull/52) had an incomplete overall build. The record does not certify the whole manuscript, exact KL optimality, physical reader assumptions, or empirical AI performance. Kernel rechecking is distinct from an external referee's assessment; see [Lean's proof-validation guidance](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).

## Contribution and collaboration

Youngseok supplies the research direction, original problem framing and user-side corrections. Zero (ChatGPT) supplies substantial analysis, code, formalization and drafting assistance. The work is AI-assisted; the roles and each result's actual validation status remain explicit.

Focused collaboration topics: request/approval binding regressions; traceable evaluation of conversational memory; and checking explicit finite evidence-preservation claims against prior theory. Technical reproduction, formal validity, scholarly novelty and real-world applicability are tracked separately.

## 한국어 요약

영석(Youngseok Oh)과 Zero의 공개 작업을 원출처로 확인할 수 있는 입구다. Hermes의 모델 전환 사례에는 외부 개발자가 재현·테스트·패치 적용과 `YS-OH-CORE` 크레딧을 남겼다. Signal 사례에서는 우리 소스 검토와 검사 제안을 받은 사람이 직접 구현했고, 다른 기여자가 다시 검사하고 원 작성자의 허락을 받아 PR #122033을 제출했다. 해당 코드와 테스트는 그 개발자들의 기여이며, 우리는 문제를 좁히는 검토·검증·전달을 보탰다.

두 Hermes PR의 upstream 병합은 2026년 9월 26일 확인 시 완료되지 않았다. 이번 갱신은 이미 발생한 외부 활용을 확인해 연결한 것이며, 새로운 답변·실험·채택을 오늘 얻었다는 뜻이 아니다. 유한 Lean 증명 핵심부는 9월 16일의 별도 기록으로 남기며, 이번에 다시 검증하지 않았다. 개인 대화, 비공개 메일, 계정 자료는 이 페이지에 포함하지 않는다.
