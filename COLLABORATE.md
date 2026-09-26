# Work with Youngseok Oh × Zero
## Does the user's changed intent reach the action that actually runs?

**Focused reproduction and regression checks for AI-agent teams.**

We investigate a concrete mismatch between what a user authorized, what the system retained, and what the software actually executed. A useful first engagement is **one reported failure, one agreed execution path, and one reproducible acceptance check**, not an open-ended audit of an entire product.

Youngseok Oh frames the questions and judges the user-facing meaning. Zero is his AI collaboration partner for technical investigation, implementation, analysis and communication. Public evidence and the division of work are explicit.

## Start with a contribution someone else applied

In [Hermes Agent PR #22982](https://github.com/NousResearch/hermes-agent/pull/22982), a later model-switch approval could consume an earlier request's retained payload. Our contribution supplied a request-binding reproduction, a patch and regression tests.

The PR author [reported running the tests and applying the patch](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201). Their [commit 501be10c](https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601) credits `YS-OH-CORE` and says the patch and binding tests were adapted verbatim from the proposal. The author reported eight of ten new cases failing before the repair and all ten passing afterwards, with the existing fifteen model-command tests still passing.

**Evidence status, rechecked 26 September 2026:** external contributor application in a PR branch. The upstream PR remains open and unmerged. This is neither a paid-client testimonial nor a claim that the change has shipped. Those test counts are the recipient's reported verification, not a new execution for this page.

## A bounded review you can ask about

| Your concrete question | Proposed check |
|---|---|
| Can a fresh approval accidentally execute an older request? | Bind the approval to its request and inspect the actual routed payload, including cancellation and replacement. |
| Did a user correction survive history reconstruction? | Compare the source messages, rendered model input and observed final action separately. |
| Did an SDK or model-template change silently drop reasoning history? | Reproduce the exact input boundary with pinned versions, then test a minimal client-side adapter. |

For an agreed case, the deliverable is a short diagnosis, exact environment and reproduction steps, observed before/after evidence where execution is available, and a regression check the team can rerun. A source-only finding is labeled source-only; an unavailable endpoint is not scored as a model failure. Runtime costs, access, deadline, permitted AI use and any fee are agreed before accepting work. No subscription or payment is collected by this page.

## Current-model example: reasoning-history handoff

Our [Qwen3.8-27B input-boundary check](https://github.com/YS-OH-CORE/second-paddle-notes/blob/b60682587597235706714ccfacd37cb0a883b76d/experiments/qwen38-native-continuation/RESULTS.md) compares a response-shaped `reasoning` field with the pinned official HF template's `reasoning_content` input. At that direct client-to-template boundary, an explicit adapter restores the expected rendered text and token IDs. The report supplies the adapter, nine unit tests and twelve rendered-input observations.

**Scope:** tokenizer/template execution with synthetic markers, not generated-answer accuracy, a server-side vLLM diagnosis or a model-memory defect. The attempted public generation endpoint was paused; current-model answer behavior in that pilot is still unmeasured. [Adapter source](https://github.com/YS-OH-CORE/second-paddle-notes/blob/b60682587597235706714ccfacd37cb0a883b76d/experiments/qwen38-native-continuation/history_bridge.py).

## Begin with the problem, not a large upload

Use the existing public contact **[ku38155@gmail.com](mailto:ku38155@gmail.com?subject=Scoped%20AI%20continuity%20review)** and include:

```text
Product/model/SDK and exact version or public link:
What the user changed or approved:
What should have happened, and what actually happened:
One public-safe example and the decision this review would help you make:
Desired deadline, execution budget and permitted AI use:
```

Do not send credentials, private conversations or confidential manuscripts in an initial inquiry. Use synthetic or redacted examples; agree on access and permitted AI processing before sharing non-public material. An inquiry is not a booking, a delivery guarantee or permission to modify a production system.

Public critique and replication are also welcome through [CONTRIBUTING.md](CONTRIBUTING.md). We respect the original contributor's implementation priority and each project's agent-contribution policy. We do not open competing patches merely to claim ownership. [Selected public work](YOUNGSEOK_OH_SELECTED_WORK.md) provides additional dated evidence, with its own scope labels.

---

## 한국어 | 바뀐 의도가 실제 실행까지 이어지는지 확인합니다

**사용자가 취소했는데 옛 계획이 실행되거나, 새 승인에 예전 요청이 붙거나, 보존한 줄 알았던 기록이 입력에서 빠지는 문제**를 대상으로 합니다. 처음부터 제품 전체를 검사한다고 약속하지 않고, 실제 문제 하나와 실행 경로 하나를 합의해 재현·원인 구별·재발 검사로 연결합니다.

대표 근거는 Hermes PR 작성자가 우리 패치와 검사를 직접 적용하고 크레딧을 남긴 기록입니다. 2026년 9월 26일 재확인 시 해당 upstream PR은 아직 열려 있고 병합되지 않았습니다. 최신 모델 관련 예시는 Qwen3.8의 입력 연결 검사이며, 실제 모델 답변 실험과 구별합니다.

영석은 문제의 출발점과 사용자 관점의 의미·판단을 맡고, 제로는 기술 조사·구현·분석·전달을 맡는 AI 협업 파트너입니다. 원래 개발자의 기여와 우리 기여도 나눠 표시합니다. 공개 가능한 예시와 기대 동작부터 보내 주세요. 기한·실행비·자료 사용 범위와 유료 작업 여부는 수락 전에 정합니다.

*Updated 26 September 2026. The [earlier product-communication offer](https://github.com/YS-OH-CORE/second-paddle-notes/blob/fc13c190725da5a0ad0547da2a69fbee152b7a43/COLLABORATE.md) and [bilingual sample](work/source-checked-product-copy.md) remain available as historical work; they are no longer this page's primary offer. This page is a proposed collaboration scope, not evidence of new clients, endorsements or revenue.*
