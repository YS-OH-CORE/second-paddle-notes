# Youngseok Oh (오영석) × Zero

## Selected work: agent reliability with traceable results

Human–AI collaboration on reproducible failures, regression tests, and reviewable fixes. This page presents externally acknowledged contributions, with the original evidence and material corrections beside each claim.

**한국어 소개는 아래에 있습니다.**

**Evidence at a glance:** [Case 01: request-bound approvals](#case-01--keeping-an-approval-attached-to-its-own-request) · [Case 02: explicit stop handling and an E2E correction](#case-02--explicit-stop-handling-and-an-end-to-end-correction)

## Case 01 | Keeping an approval attached to its own request

**Project:** Hermes Agent, proposed multiline model-command feature  
**Contribution:** request-binding review, reproducible cases, regression tests, and a production patch  
**Evidence checked:** 2026-09-12

**Outcome:** the feature's PR author applied the contributed patch and binding tests to their branch and credited **@YS-OH-CORE** in the commit. At this check, the upstream PR remained open and unmerged. [Author's confirmation][ack] · [Crediting commit][commit] · [Current PR][pr]

> “thanks @YS-OH-CORE for the exemplary review”
>
> MestreY0d4-Uninter, author of the proposed feature, in the [public implementation follow-up][ack]. This is an excerpt about this contribution, not an institutional endorsement.

### The problem

A user could request a model switch with a task attached, leave its approval pending, then request a different model switch. The old task was kept in a conversation-level slot. A later approval could consume that older task instead of only the request associated with the new approval. The [implementation commit][commit] describes this failure and the repair.

The important question was not merely whether the user had clicked “approve.” It was **which request that approval belonged to**, including when messages or callbacks arrived late.

### What the collaboration contributed

The [submitted patch and design][design] bind a fresh request-local token before the confirmation is shown. A callback can consume its own token, rather than whichever text happens to occupy the conversation slot later. Replaced or revoked callbacks cannot consume a successor's payload. The dispatcher also stops restaging old payloads after delayed presentation.

The accompanying [regression tests][tests] cover late presentation, fast approval, help while a request is pending, a failed replacement proposal, boundary revocation, and preservation of the supplied request's whitespace. These exercise real dispatch/confirmation code with controlled transport and model fixtures.

**Roles:** this contribution was prepared under **Youngseok Oh's @YS-OH-CORE account with Zero (ChatGPT)**. MestreY0d4-Uninter authored the original feature, integrated the repair, and reported a separate local re-test. Hermes project maintainers decide upstream review and merge. [Contribution design][design] · [Commit attribution][commit]

### What the recipient checked

The following counts are **the PR author's local re-test report**, not a new test run performed while writing this page. The parenthetical detail in the [original English reply][ack] specifies eight failures out of ten binding cases:

| Selected checks | Before the binding patch | After the binding patch |
|---|---:|---:|
| Ten added binding cases | 8 failed, 2 passed | 10 passed |
| Fifteen existing model-command checks | Not reported as a new baseline here | 15 passed, unchanged |

The author also reports unrelated or pre-existing full-suite failures. These selected results should not be described as an entirely passing application suite or a production error rate. The tests use controlled fixtures, not a live user's conversation. [Original report][ack] · [Adopted test file][adopted-tests]

### Check the contribution without taking this page on trust

**1. Read the recipient's acknowledgment.** It identifies the two contributed files, the SHA-256 check they performed, and their local test results. [Open the reply][ack]

**2. Read the applied commit.** It credits @YS-OH-CORE and shows the two production-module changes and added test file. [Open commit 501be10c][commit]

**3. Compare the test's identity.** The previously submitted file and the file at that adopted commit both return Git blob **`98ec718af91f6ac5fc7cb4470f95dba56f858e30`**. This identifies the same Git file content, separately from the author's reported execution results. [Submitted test][tests] · [Adopted test][adopted-tests] · [Machine-readable source record](work/approval-binding.evidence.json)

This case documents **external contributor use and credit at the PR-branch stage**. It does not establish a merged release, paid engagement, or a blanket endorsement of other work. The date above is a snapshot; use the linked PR for later status.

### Follow-through | 21 September 2026

**Continued use after integration.** The PR author [reported applying our port guidance][port-followup] at head `8c0090dc9a`. During that port, the contributed binding tests exposed an interaction between newer switch locking and delayed confirmation display. The author separated confirmation registration from display and repaired the test environment. Those additional integration fixes and the reported validation are the author's work.

The [binding-test file at that head][current-binding-tests] still has Git blob `98ec718af91f6ac5fc7cb4470f95dba56f858e30`, matching the earlier adopted file. This is a checked file-identity link, not a new execution of the tests for this page.

**A separate finding remains under review.** Our [21 September follow-up][late-decline-review] supplies a controlled source-extraction reproducer and an atomic, request-ID-scoped cleanup candidate for a late declined prompt that can remove a newer confirmation. It is a submitted technical finding, not an adopted repair. Full gateway integration and reachability under the real connector's transport contract remain to be checked.

**Status at this check:** PR #22982 is open and unmerged at the head above. The recipient explicitly leaves live Slack field validation outstanding. The original contribution, the recipient's later fixes, and the unconfirmed follow-up are separate evidence, not a single completed deployment.

## Case 02 | Explicit stop handling and an end-to-end correction

**Project:** Hermes Agent PR #84236  
**Contribution:** a reproduced finalizer edge case, regression cases, a narrow condition change, and a public correction to a call-path inference  
**Evidence checked:** 2026-09-23

**Outcome:** the PR author applied the proposed condition in [commit e99497e][stop-commit], whose message explicitly credits the **YS-OH-CORE review**. An explicit `user_stop` carrying a diagnostic message now keeps the visible stop fallback instead of being mistaken for a new-message redirect. The author added a five-case finalizer regression. This is verified code incorporation on the author's PR branch; [the PR][stop-pr] was open and unmerged at this check.

**Material correction, not omitted from the case:** our [original review][stop-review] reproduced the condition with the production finalizer and upstream unit fixtures. We also cited a CLI call site as motivation, while explicitly leaving end-to-end testing unperformed. The author's [real CLI test with a mock model endpoint][stop-response] showed that, on the cited single-query SIGINT path, the turn unwinds before the finalizer runs. Our narrow condition therefore does **not** reproduce or fix that CLI no-feedback symptom. We [accepted and published this correction][stop-correction]. The remaining CLI gap is separate.

The same recipient follow-up identifies and fixes a different live-signal omission: `stop_kind="user_stop"` is now stamped while the turn is still alive. That finding, its integration, and the reported 129-test run belong to **Halldrix**. They were not independently rerun for this case page. The adopted condition, the recipient's additional repair, and the unresolved CLI path are distinct results, not a single claim of end-to-end resolution.

**Human–AI roles:** Youngseok Oh sets the collaboration's problem direction and priorities. Zero (ChatGPT) supplied substantial analysis, regression authoring, execution orchestration, and review drafting. Halldrix authored the feature, integrated the condition, performed the end-to-end comparison, and supplied the correction. This is a documented collaboration, not a claim of solo human engineering credentials, research accreditation, or institutional endorsement.

**Inspect the chain:** [Original review and execution evidence][stop-review] → [Recipient's result and counterevidence][stop-response] → [Crediting code change][stop-commit] → [Our public correction][stop-correction].

## A useful starting point for collaboration

A good first case is a public, reproducible agent behavior that differs from the user's actual request. Provide the exact code revision, a small synthetic example, the expected behavior, and the observed behavior. That makes it possible to decide whether the right next deliverable is a reproduction, a regression test, or a narrow patch.

[Open a public issue](https://github.com/YS-OH-CORE/second-paddle-notes/issues/new) · [Contribution guidelines](CONTRIBUTING.md) · [Authorship and existing contact](AUTHORSHIP.md)

Keep credentials, private conversations, and personal records out of public issues. An inquiry starts a scope discussion; it is not a commitment to paid work or a delivery deadline.

---

## 한국어 | 실제로 사용되고 이름이 남은 기여

**영석(Youngseok Oh)과 제로의 인간–AI 협업 사례**입니다. 이상 동작을 설명하는 데서 끝내지 않고, 재현 사례와 검사, 검토 가능한 수정안으로 연결한 과정을 보여 줍니다.

### 무엇을 고쳤는가

헤르메스의 개발 중인 모델 변경 기능에서, 새 요청을 승인했는데 이전 요청에 붙어 있던 작업이 따라갈 수 있었습니다. 요청이 대화방의 공용 보관함에만 연결돼 있어, 늦게 처리된 승인이 엉뚱한 내용을 꺼내는 문제였습니다. 수정은 승인을 더 받는 방식이 아니라, **각 승인과 그 승인에 해당하는 요청을 정확히 묶는 방식**입니다. [적용 커밋][commit]

### 어떤 기여가 돌아왔는가

영석의 **@YS-OH-CORE** 계정에서 제로와 함께 재현 방법·검사·패치를 제공했습니다. 원래 기능의 개발자 MestreY0d4-Uninter는 이를 자기 작업 브랜치에 적용했다고 밝히고, 공개 답변과 커밋 메시지에 기여를 명시했습니다. 원래 기능의 개발·통합과 보고된 로컬 재시험은 그 개발자의 작업입니다. [개발자의 답변][ack] · [커밋의 기여 표시][commit]

개발자의 원문 보고에 따르면 추가 검사 10개 중 수정 전에는 8개가 실패하고 2개가 통과했으며, 수정 후에는 10개가 모두 통과했습니다. 기존 모델 명령 검사 15개도 그대로 통과했다고 보고했습니다. 이 수치는 상대가 보고한 재시험 결과이고, 이번 소개글 작성 중 새로 실행한 시험 수치가 아닙니다. 원문의 전체 검사 관련 설명도 함께 연결했습니다. [원문 결과][ack]

**직접 확인한 코드 흔적도 있습니다.** 우리가 제출한 검사 파일과 상대가 적용한 검사 파일의 Git 식별값이 같았습니다. 감사 인사만 있는 것이 아니라, 무엇이 적용됐는지 확인할 수 있는 파일과 커밋이 남았습니다. [제출한 검사][tests] · [적용된 검사][adopted-tests]

### 2026년 9월 21일 후속 확인

**기여한 검사가 이후 변경에서도 쓰였습니다.** 개발자는 우리의 최신 코드 이전 지침을 적용했으며, 그 과정에서 기존 바인딩 검사가 새 잠금 기능과 지연된 확인창 표시의 충돌을 드러냈다고 [보고했습니다][port-followup]. 추가 통합 수정과 보고된 검증은 그 개발자의 기여입니다. 새 head의 검사 파일도 이전과 같은 Git 식별값을 가지는지 확인했습니다. 이 페이지를 고치면서 검사를 새로 실행한 것은 아닙니다.

별도로, 옛 확인창의 늦은 전송 거절이 새 승인 대기를 지우는 경우에 대해 [재현 코드와 수정 후보를 전달했습니다][late-decline-review]. 이 후속은 아직 실제 통합·통신 조건의 검토가 남아 있으며, 적용된 수정으로 소개하지 않습니다. 현재 PR은 열려 있고 아직 병합되지 않았습니다. 앞선 기여가 유지된 사실과 새 문제의 검토 대기를 나누어 남깁니다.

### 현재 단계와 다음 연결

2026년 9월 12일 확인한 단계는 **외부 개발자의 적용과 기여 명시**입니다. 원프로젝트의 PR은 당시 아직 열려 있었습니다. 이후 병합이나 배포 상태는 [원 PR][pr]에서 확인할 수 있습니다.

### 사례 02 | 중단 처리에 반영된 기여와 공개 정정

**2026년 9월 23일 확인.** PR #84236의 작성자 Halldrix는, 사용자 중단에 이유 문장이 붙었을 때 이를 새 질문으로 오인하지 않도록 우리가 제안한 조건을 [자기 코드에 반영했습니다][stop-commit]. 커밋 메시지는 **YS-OH-CORE의 검토**를 명시하며, 작성자가 추가한 검사에도 그 출처가 남아 있습니다. 확인 당시 [원 PR][stop-pr]은 아직 병합 전이었습니다.

**우리 설명에서 바로잡힌 부분도 함께 공개합니다.** [원래 검토][stop-review]는 실제 종료 처리 함수와 단위검사 환경에서 조건을 재현했지만, 근거로 든 명령줄 실행 경로 전체는 시험하지 않았습니다. 상대의 [명령줄 전체 실행 비교][stop-response]에서 그 경로는 종료 처리 함수에 도달하기 전에 끝나는 것으로 나타났습니다. 따라서 이 조건 수정이 명령줄의 무응답까지 해결했다는 뜻은 아닙니다. 이 연결 추론은 [공개 답변으로 정정했습니다][stop-correction].

실행 중 중단 사유를 기록하지 않던 다른 부분의 발견·수정과 관련 검사 129개 통과는 Halldrix의 기여 및 보고입니다. 이번 소개글을 작성하면서 새로 실행한 검사가 아니며, 남은 명령줄 문제는 별도입니다.

오영석의 문제 방향·우선순위 판단, Zero(ChatGPT)의 상당한 분석·검사 작성·실행 조율·문안 작성, 상대 개발자의 구현·통합·반론을 구분합니다. 영석이 모든 코드를 혼자 작성한 전문경력으로 바꾸지 않습니다. **확인 가능한 기여와 그 기여의 한계를 같은 자리에서 볼 수 있는 협업 사례**입니다.

관련 협업을 제안할 때는 공개해도 되는 작은 재현 예시와 코드 버전, 기대한 결과와 실제 결과를 [이슈](https://github.com/YS-OH-CORE/second-paddle-notes/issues/new)에 남겨 주세요. 소개글의 설명보다 원문 답변, 코드, 검사 자료를 먼저 확인할 수 있도록 구성했습니다.

*This case page was written with Zero (ChatGPT) for Youngseok Oh. It reuses public contribution evidence, not private correspondence. Original code and test licensing remain with their existing files; this page does not relicense them.*

[ack]: https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201
[commit]: https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601
[pr]: https://github.com/NousResearch/hermes-agent/pull/22982
[design]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/21cd675cf4ce8b3722354bd58f673e61c0eb7856/contributions/hermes-model-confirmation/BINDING.md
[tests]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/21cd675cf4ce8b3722354bd58f673e61c0eb7856/contributions/hermes-model-confirmation/test_model_confirmation_binding.py
[adopted-tests]: https://github.com/MestreY0d4-Uninter/hermes-agent/blob/501be10cce7159a08279c89c724db602d9770601/tests/gateway/test_model_confirmation_binding.py
[port-followup]: https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5756049894
[current-binding-tests]: https://github.com/MestreY0d4-Uninter/hermes-agent/blob/8c0090dc9adbddcebb5491559ad98e1cf90d5bb4/tests/gateway/test_model_confirmation_binding.py
[late-decline-review]: https://github.com/NousResearch/hermes-agent/pull/22982#pullrequestreview-5266577738
[stop-review]: https://github.com/NousResearch/hermes-agent/pull/84236#pullrequestreview-5275311288
[stop-response]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5786674461
[stop-commit]: https://github.com/Halldrix/hermes-agent/commit/e99497e5101358b496ca860a3e42c1b623375287
[stop-correction]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5786815631
[stop-pr]: https://github.com/NousResearch/hermes-agent/pull/84236
