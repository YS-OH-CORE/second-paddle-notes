# Youngseok Oh | Selected work and public evidence

Independent researcher, South Korea · GitHub: **YS-OH-CORE**  
Prepared with **Zero** · Latest focused evidence update: **28 September 2026**

Research focus: preserving evidence and corrections across human–AI memory, and reproducible review of agent systems. This self-published index links specific records; it is not an institutional credential or a blanket endorsement. The Hermes HTTP recovery and evaluation entries below were checked on **28 September 2026**. Other entries retain their stated check dates; the formal-methods section retains its **16 September 2026** snapshot.

[Discuss one scoped AI-continuity review](COLLABORATE.md).

## Hermes MCP recovery: an HTTP regression adopted by the PR author

**Outcome, 28 September 2026:** **liuhao1024**, author of [Hermes PR #121944](https://github.com/NousResearch/hermes-agent/pull/121944), [reported incorporating our test-only contribution](https://github.com/NousResearch/hermes-agent/pull/121944#issuecomment-5863926910). The actual [integration commit `859b987`](https://github.com/liuhao1024/hermes-agent/commit/859b987d1df0f47236eabe4190e9d41122b5ea12) contains the unchanged test file and a **YS-OH-CORE co-author trailer**. The recipient also reported local re-testing and explained how the before/after comparison supported the PR's transport decision.

**Problem and contribution:** a temporary HTTP 503 during tool discovery could send Hermes into an inappropriate legacy-SSE fallback. The original reporter **fmunechi** supplied the diagnosis and proposed guard; **liuhao1024** implemented the repair. **Zero × Youngseok Oh** supplied two real-loopback integration tests: recovery from that 503 through the actual MCP SDK and Hermes retry path, plus a genuine HTTP 405 that must still enter legacy SSE and complete a tool call. The [original execution record](https://github.com/YS-OH-CORE/second-paddle-notes/blob/b2900898ae850ef106b8619a53fde93dfd5c2719/checks/hermes-http503-121944/README.md) retains the matched baseline, successful candidate, development corrections, and scope.

**Verified source identity:** submitted commit `60c824e` and recipient commit `859b987` share parent `dad46f0`, the same complete Git tree, and test blob **`b36e7271a7519fa37a86bbbed813017b6f477624`**. Both add only the same 159-line test file. The recipient's commit records **liuhao1024** as Git author and committer and **YS-OH-CORE** in its co-author trailer. [Submitted commit](https://github.com/YS-OH-CORE/hermes-agent/commit/60c824eadd6952175f15e32e703127560d87d7cb) · [Recipient commit](https://github.com/liuhao1024/hermes-agent/commit/859b987d1df0f47236eabe4190e9d41122b5ea12) · [Machine-readable comparison](work/hermes-http503.evidence.json)

**Validation and stage:** our earlier retained run on fix head `dad46f0` passed 41 tests across four related files; the original product PR's parent `749220ef` and separately inspected main each failed the new 503 test while passing the legitimate-SSE control. The recipient's later reply reports 43/43 in their environment. Those counts remain separately attributed, and their difference has not been reconciled. This page update performed source and attribution checks without a new test run. At head `859b987`, the PR is **open and unmerged**: the established outcome is incorporation into the original author's PR branch.

**한국어:** 헤르메스 수정안의 작성자가 우리가 보낸 실제 HTTP 회귀 테스트를 자기 PR에 반영하고, 커밋에 **YS-OH-CORE 공동저자 표기**를 남겼다. 직접 대조한 결과 검사 파일의 내용과 전체 코드 트리가 제출본과 일치했다. 원래 문제 제보와 제품 수정은 fmunechi·liuhao1024의 기여이고, 우리는 실제 SDK와 재시도 경로를 통과하는 검사와 실행 근거를 보탰다. 확인한 단계는 **원작성자의 개발 브랜치 반영**이며, 공식 병합은 아직 전이다. 답변 시각은 9월 28일 **14:16:21 KST**다.

## Hermes evaluation: a startup observation sharpened the proposed test

**Question:** can an evaluation run alter memory before its first measured turn, even when `saveMessages=false` is configured?

**Outcome:** discussion participant **mdhaseeb343q-pixel** accepted our correction about an existing persistence proposal, then explicitly used **@YS-OH-CORE**'s startup observation to identify a missing assertion in another participant's proposed test. This is an externally attributable use of the review in test and policy discussion. [Acknowledgment and correction](https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5854968442) · [Use in the test discussion](https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5857521128)

### Evidence trail

| Stage | Public evidence | What it establishes |
|---|---|---|
| Executed probe, 25 September 2026 UTC | [Our report to issue #121935](https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5829103900) · [Pinned probe and results](https://github.com/YS-OH-CORE/second-paddle-notes/blob/23a9c91985dc80ca9b9ff8988f02fee60e67d073/checks/hermes-eval-write-boundary-121935/README.md) | In a synthetic cold, owner-declared, per-directory session, initialization reached three recorded file-upload calls with `saveMessages=false`. Warm, per-session-strategy and nonowner controls recorded none. |
| Recipient response, 27 September 10:16 UTC | [Acknowledgment](https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5854968442) | The participant explicitly accepted the correction that PR #73935 already covers automatic persistence including migration, and identified the startup-state controls as useful policy evidence. |
| Subsequent use, 27 September 16:07 UTC | [Test-design follow-up](https://github.com/NousResearch/hermes-agent/issues/121935#issuecomment-5857521128) | The participant cited @YS-OH-CORE's probe to explain why checking only turn sync, profile mirroring and session-end flush could miss initialization writes. They asked for an initialization assertion and explicit startup fixtures. |

**Why the control matters:** a warm fixture can record no uploads even when an implementation would still upload files on a fresh owner session. A regression test must establish which startup state it exercises. The contribution made that conditional behavior concrete so other participants could use it when defining the test.

The source-selected probe used unchanged method bodies from `7b761da2de4979e424510ca7022bf9527aa65b68`, with fake manager/SDK collaborators and synthetic files. Its fourteen cases at two setting values produced 28 condition/case observations. It recorded call reachability rather than uploading to a live service. Those are the earlier executed observations; no probe or model was rerun for this index update.

**Status checked 28 September 2026:** [issue #121935](https://github.com/NousResearch/hermes-agent/issues/121935) remains open with a maintainer decision requested before implementation. The discussion reuse above does not establish an adopted implementation or maintainer approval. The related automatic-persistence [PR #73935](https://github.com/NousResearch/hermes-agent/pull/73935) remains open and unmerged at `91b3b31dc91aec04abac8be5d240f2d0ad491054`. Its narrower setting intentionally preserves explicit tool writes; that contract is distinct from the proposed strict read-only invocation policy.

**Roles:** fmunechi supplied the original opt-out request; mdhaseeb343q-pixel developed the invocation-policy proposal and the cited follow-up analysis; saurabhmeddo authored the existing automatic-persistence proposal. **Youngseok Oh × Zero** contributed the supplemental fixture, executed observations and correction. The cited responses predate this page addition; they are newly linked here, not newly received endorsements.

**한국어:** “자동 저장을 껐으니 평가 중 기억도 바뀌지 않을 것”이라고 가정하면 시작 단계의 파일 업로드를 놓칠 수 있었다. 우리 검증은 어떤 시작 상태에서 그 호출이 생기고, 어떤 대조 상태에서는 생기지 않는지 보여줬다. 논의 참여자는 이 결과를 받아 기존 수정안에 대한 자신의 설명을 고쳤고, 다른 사람이 제안한 검사에도 `YS-OH-CORE`를 인용해 시작 단계 검사를 추가해야 한다고 설명했다. 확인된 성과는 **실행 근거가 다른 참여자의 설명과 검사 설계 논의에 쓰인 것**이다. 정식 구현과 병합 여부는 별개이며, 이번에는 해당 공개 경로를 대표 작업 소개에 연결했다. 응답 시각은 한국시간 9월 27일 19:16과 9월 28일 01:07이다.

## Memory operations: review used to prevent a false-success response

**Question:** does a successful deletion response mean that the matching memories were actually removed?

In [mem0 issue #7439](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5824943500), our populated-store counterexample showed why returning an invented empty listing was not an adequate fix: deletion could report success while the target records remained. [Souptik96's public response](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5843366869) explicitly credits that check and describes changing the implementation to report unsupported listing rather than silent success.

The [revised fork source](https://github.com/Souptik96/mem0/blob/127bb79725aeb09d70e58620fd1d88476abf9aca/mem0/vector_stores/langchain.py) and the [recipient's populated-FAISS regression](https://github.com/Souptik96/mem0/blob/127bb79725aeb09d70e58620fd1d88476abf9aca/tests/memory/test_main.py) give a code-level trail. Our [earlier follow-up execution](https://github.com/YS-OH-CORE/second-paddle-notes/blob/5bf5a87d001dccae3a83293b11bdc417146fac3c/checks/mem0-7464-recipient-followup/README.md) ran seven selected recipient tests unchanged: seven passed, none skipped; replacing only the adapter with its exact prior version made six fail. This page addition did not rerun those tests.

**Status checked 26 September 2026:** [PR #7464](https://github.com/mem0ai/mem0/pull/7464) is closed and unmerged. Its reported head remains `cec74a8e`; the verified newer fork revision is `127bb797`. The [queue-gate message](https://github.com/mem0ai/mem0/pull/7464#issuecomment-5843251973) explains the pending accepted-issue requirement. Recipient use of review guidance is established; upstream acceptance, release, and bulk-deletion support are not. BlueX888 supplied the original diagnosis, Souptik96 the revised implementation and tests, and Youngseok Oh × Zero the counterexample and follow-up verification.

## Memory evaluation: a report corrected its interpretation and named the reviewers

**Question:** do the saved results support the comparison being claimed?

In [TAM's LongMemEval comparison report](https://github.com/vbcherepanov/total-agent-memory/blob/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e/docs/benchmarks/head-to-head-v14/RESULTS.md#revisions), the author records recalculation of six accuracy cells and four paired comparisons from saved verdicts. Counts agreed; the reporting feedback distinguished a comparison that changed both the judge model and rubric from a prompt-only comparison. The report also distinguishes absence of a statistically detected difference from demonstrated equivalence, and discloses its tuning history.

[The author's attribution commit](https://github.com/vbcherepanov/total-agent-memory/commit/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e) names Youngseok Oh and Zero, states their division of work, and limits the review to saved-verdict calculations and reporting feedback. This is attribution in the author's own repository, not merely a claim on this page. The September 24 record was inspected again for this addition; it is not a new response or a new experiment.

**Scope:** no retrieval rerun, new answer generation, fresh judge decisions, independent audit of tuning, or overall system-quality certification. The report and system remain Vitalii Cherepanov's work. No institutional credential, paid-client relationship, or endorsement is implied.

**한국어:** mem0 사례에서는 실제 기록을 넣은 반례가 상대의 수정 방향과 검사에 반영됐다. TAM 사례에서는 저장된 채점 결과의 재계산과 비교 해석에 대한 검토가 작성자의 보고서 수정 및 기여 표기로 남았다. 둘 다 공개 원출처로 확인할 수 있지만, 정식 제품 반영이나 전체 성능 인증과는 다르다. 이번 추가는 그 두 경로를 기존 대표 작업 소개에 연결하는 편집이며, 신규 실험 결과가 아니다.

## 1. Agent reliability: a patch applied by another developer

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

모델 전환·Signal 두 Hermes PR의 upstream 병합은 2026년 9월 26일 확인 시 완료되지 않았다. HTTP 복구 사례는 9월 28일 새로 받은 반영 답변과 실제 커밋을 대조한 기록이다. 다른 사례의 과거 응답·실행 시점은 각 항목에 남겨 두었다. 유한 Lean 증명 핵심부는 9월 16일의 별도 기록으로 남기며, 이번에 다시 검증하지 않았다. 개인 대화, 비공개 메일, 계정 자료는 이 페이지에 포함하지 않는다.
