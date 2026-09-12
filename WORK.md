# Youngseok Oh × Zero

## Selected work: agent reliability with traceable results

Human–AI collaboration on reproducible failures, regression tests, and reviewable fixes. This page presents one externally acknowledged contribution, with the original evidence beside the claim.

**한국어 소개는 아래에 있습니다.**

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

### 현재 단계와 다음 연결

2026년 9월 12일 확인한 단계는 **외부 개발자의 적용과 기여 명시**입니다. 원프로젝트의 PR은 당시 아직 열려 있었습니다. 이후 병합이나 배포 상태는 [원 PR][pr]에서 확인할 수 있습니다.

관련 협업을 제안할 때는 공개해도 되는 작은 재현 예시와 코드 버전, 기대한 결과와 실제 결과를 [이슈](https://github.com/YS-OH-CORE/second-paddle-notes/issues/new)에 남겨 주세요. 소개글의 설명보다 원문 답변, 코드, 검사 자료를 먼저 확인할 수 있도록 구성했습니다.

*This case page was written with Zero (ChatGPT) for Youngseok Oh. It reuses public contribution evidence, not private correspondence. Original code and test licensing remain with their existing files; this page does not relicense them.*

[ack]: https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201
[commit]: https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601
[pr]: https://github.com/NousResearch/hermes-agent/pull/22982
[design]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/21cd675cf4ce8b3722354bd58f673e61c0eb7856/contributions/hermes-model-confirmation/BINDING.md
[tests]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/21cd675cf4ce8b3722354bd58f673e61c0eb7856/contributions/hermes-model-confirmation/test_model_confirmation_binding.py
[adopted-tests]: https://github.com/MestreY0d4-Uninter/hermes-agent/blob/501be10cce7159a08279c89c724db602d9770601/tests/gateway/test_model_confirmation_binding.py
