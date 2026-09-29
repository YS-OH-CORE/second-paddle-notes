# 외부 반응 · 채택 기록

**영석과 제로의 기여에 상대가 남긴 말과 행동.**

**Zero × Youngseok Oh** · 2026-09-29 KST

[English](README.md) · [공개 작업실](../README.md) · [상세 기여 기록](../WORK.md) · [캡처·출처 묶음](archives/recognition-2026-09-29.zip)

**9개 외부 계정 · 9개 작업 주제 · 13개 원문 기록**  
대상 기록: 2026-09-12 ~ 2026-09-29. 단순 감사, 실제 채택, 검토 승인, 보고서의 이름 표기와 중요한 교정을 함께 모았다.

짧은 번역은 편집자의 번역이다. 이미지 본문은 실제 GitHub 페이지에서 잘라낸 원문 픽셀이며 주변 이름·날짜·출처는 편집 카드다. 전체 댓글 화면을 재현한 것이 아니다. 이미지를 누르면 전체 맥락이 있는 원문으로 이동한다.

관련 PR 8개의 상태를 2026-09-29에 다시 조회했다. 상대의 채택과 최종 병합·배포는 구분한다. 이 보관 작업 자체에서는 코드나 모델 실험을 새로 실행하지 않았다.

---

## 01. MCP conformance | 수정 커밋과 저작자 표기를 함께 채택

**@aton-of-data · 2026-09-29 KST**

실제 허점을 찾았어요. *(발췌 번역)*

[![aton-of-data source excerpt](cards/2026-09-29/mcp-adoption.png)](https://github.com/modelcontextprotocol/conformance/pull/533#issuecomment-5880560542)

상대는 우리의 지연 연결 수정 커밋을 저작자 기록과 함께 PR 브랜치에 반영하고, 동일한 검사를 수정 전후 코드에서 실행했다고 보고했다. 후속 답변에서는 서버 세션 생성 시점과 연결 반환 시점을 구분하도록 설명을 바로잡았다. 영원히 끝나지 않는 연결 준비와 별도의 SDK 경로는 남은 범위다.

**조회 당시 상태:** [PR #533](https://github.com/modelcontextprotocol/conformance/pull/533) · 열림 · 미병합

[상대 원문](https://github.com/modelcontextprotocol/conformance/pull/533#issuecomment-5880560542) · [기여 근거](https://github.com/YS-OH-CORE/second-paddle-notes/blob/2ca3b644315b0e60e88b21cdaa7f3c41fb14feee/checks/mcp-533-bypass/README.md) · [원문 영역 캡처](captures/2026-09-29/mcp-adoption.png)

<details><summary>후속 기록과 캡처</summary>

**2026-09-29 · @aton-of-data**

[![mcp-wording-correction](cards/2026-09-29/mcp-wording-correction.png)](https://github.com/modelcontextprotocol/conformance/pull/533#issuecomment-5883048830)

</details>

---

## 02. Mem0 | 설계 대화에서 상대의 수정과 재검증으로

**@Sai-Sreenath-1819 · 2026-09-28 KST**

잘 짚었어요, @YS-OH-CORE. *(발췌 번역)*

[![Sai-Sreenath-1819 source excerpt](cards/2026-09-29/mem0-scope-dialogue.png)](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5861178611)

상대는 부분 삭제 조건과 정확한 저장 키의 차이를 인정하고 의견을 다시 물은 뒤 수정 포크를 게시했다. 우리의 후속 검증은 같은 72개 조건에서 이전 구현 16개 통과, 수정본 72개 통과를 기록했다. 닫힌 PR의 기존 head와 후속 포크는 구분하며, 검증은 실제 SQLite 저장 계층에 한정한다.

**조회 당시 상태:** [PR #7455](https://github.com/mem0ai/mem0/pull/7455) · 종료 · 미병합

[상대 원문](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5861178611) · [기여 근거](https://github.com/YS-OH-CORE/second-paddle-notes/tree/ee6a2e622436c4dd3519b5d72be2d7727a44148d/checks/mem0-7452-recipient-recheck) · [원문 영역 캡처](captures/2026-09-29/mem0-scope-dialogue.png)

<details><summary>후속 기록과 캡처</summary>

**2026-09-29 · @Sai-Sreenath-1819**

[![mem0-scope-revision](cards/2026-09-29/mem0-scope-revision.png)](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5878793041)

</details>

---

## 03. Hermes Agent | 검사 파일을 그대로 채택하고 공동 저작 표기 유지

**@liuhao1024 · 2026-09-28 KST**

이 PR에 꼭 필요했던 증거예요. *(발췌 번역)*

[![liuhao1024 source excerpt](cards/2026-09-29/hermes-http.png)](https://github.com/NousResearch/hermes-agent/pull/121944#issuecomment-5863926910)

상대는 실제 HTTP 검사 커밋을 그대로 가져가고 공동 저작 표기를 유지했다고 밝혔다. 수정 전·수정 후·본 프로젝트 코드의 비교를 높이 평가했으며, 관련 검사 43개가 자신의 환경에서 통과했다고 보고했다.

**조회 당시 상태:** [PR #121944](https://github.com/NousResearch/hermes-agent/pull/121944) · 열림 · 미병합

[상대 원문](https://github.com/NousResearch/hermes-agent/pull/121944#issuecomment-5863926910) · [기여 근거](https://github.com/liuhao1024/hermes-agent/commit/859b987d1df0f47236eabe4190e9d41122b5ea12) · [원문 영역 캡처](captures/2026-09-29/hermes-http.png)

---

## 04. CanIToolCall | 재실행 뒤 검토 승인, 사람·AI 역할 구분도 인정

**@redd34 · 2026-09-27 KST**

사람과 AI의 역할을 명확히 밝힌 점도 감사합니다. *(발췌 번역)*

[![redd34 source excerpt](cards/2026-09-29/canitoolcall-approval.png)](https://github.com/redd34/canitoolcall/pull/13#pullrequestreview-5330173478)

프로젝트 소유자는 두 사례를 재실행해 설명과 일치한다고 보고하고 APPROVED 상태를 남겼다. 실제 오류와 해석상의 불확실성을 구분한 점, 사람과 AI의 역할을 명시한 점을 긍정적으로 평가했다. 검토 승인은 최종 병합과 별개의 단계다.

**조회 당시 상태:** [PR #13](https://github.com/redd34/canitoolcall/pull/13) · 열림 · 미병합

[상대 원문](https://github.com/redd34/canitoolcall/pull/13#pullrequestreview-5330173478) · [기여 근거](https://github.com/redd34/canitoolcall/pull/13#pullrequestreview-5330173478) · [원문 영역 캡처](captures/2026-09-29/canitoolcall-approval.png)

---

## 05. Mem0 | 조용한 거짓 성공을 피하도록 수정 방향 변경

**@Souptik96 · 2026-09-26 KST**

실제 데이터가 있는 저장소 검사에 감사드립니다. *(발췌 번역)*

[![Souptik96 source excerpt](cards/2026-09-29/mem0-explicit-failure.png)](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5843366869)

상대는 빈 결과로 대체하면 오류가 조용한 삭제 성공으로 바뀐다는 지적을 인정했다. 지원하지 않는 경우를 명시적 오류로 바꾸고, 실제 데이터가 있는 FAISS 검사도 추가했다고 밝혔다. 후속 포크 수정과 공식 프로젝트의 병합은 구분한다.

**조회 당시 상태:** [PR #7464](https://github.com/mem0ai/mem0/pull/7464) · 종료 · 미병합

[상대 원문](https://github.com/mem0ai/mem0/issues/7439#issuecomment-5843366869) · [기여 근거](https://github.com/Souptik96/mem0/commit/127bb79725aeb09d70e58620fd1d88476abf9aca) · [원문 영역 캡처](captures/2026-09-29/mem0-explicit-failure.png)

---

## 06. Hermes / Signal | 제안을 실제 기기에 적용해 작동 확인

**@ren2140eth · 2026-09-25 KST**

설명한 대로 작동합니다. *(발췌 번역)*

[![ren2140eth source excerpt](cards/2026-09-29/signal-runtime.png)](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823143850)

상대는 우리의 제안 형태를 로컬에 구현하고 연결된 보조 기기로 확인했다고 보고했다. 개인 메모는 에이전트를 깨우지 않고 그룹 정책은 유지되는지 설명했다. 이후 PR #122033으로 이어졌으며 실제 기기 검증은 상대의 보고다.

**조회 당시 상태:** [PR #122033](https://github.com/NousResearch/hermes-agent/pull/122033) · 열림 · 미병합

[상대 원문](https://github.com/NousResearch/hermes-agent/issues/121970#issuecomment-5823143850) · [기여 근거](https://github.com/NousResearch/hermes-agent/pull/122033) · [원문 영역 캡처](captures/2026-09-29/signal-runtime.png)

---

## 07. Total Agent Memory | 상대의 평가 보고서에 영석과 제로 이름 명시

**@vbcherepanov · 2026-09-24 KST**

상대 보고서에 영석과 제로의 검토 기여가 명시되어 있다. *(설명)*

[![vbcherepanov source excerpt](cards/2026-09-29/tam-credit.png)](https://github.com/vbcherepanov/total-agent-memory/commit/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e)

상대는 저장된 판정의 검산과 보고 방식 피드백에 대한 외부 기여로 Youngseok Oh (@YS-OH-CORE)를 명시하고, Zero (ChatGPT)의 기술 분석·코드·실행 기여도 함께 기록했다. 해당 표기를 추가한 별도 커밋이 있다. TAM 방법의 원저자 지위나 전체 시스템 인증을 뜻하지 않는다.

**상태:** 상대 저장소의 보고서에 기여 표기 게시됨.

[상대 원문](https://github.com/vbcherepanov/total-agent-memory/commit/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e) · [기여 근거](https://github.com/vbcherepanov/total-agent-memory/blob/55d0ab0124ca4fca81479a5bcafa262aaaf0e19e/docs/benchmarks/head-to-head-v14/RESULTS.md#revisions) · [원문 영역 캡처](captures/2026-09-29/tam-credit.png)

---

## 08. Hermes Agent | 유용한 수정은 반영하고 원인 설명은 서로 교정

**@Halldrix · 2026-09-23 KST**

정확하게 읽어줘서 고맙습니다. *(발췌 번역)*

[![Halldrix source excerpt](cards/2026-09-29/hermes-stop-correction.png)](https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5787022600)

상대는 좁은 코드 조건의 보강을 채택하면서, 실제 명령줄 중단 증상은 그 수정으로 해결되지 않는다는 반증을 제시했다. 후속 답변에서는 자신의 앞선 스레드·호출 경로 설명도 교정했다. 첫 답변과 이후 교정을 함께 보존해 단위 검사 성공을 전체 문제 해결로 확대하지 않는다.

**조회 당시 상태:** [PR #84236](https://github.com/NousResearch/hermes-agent/pull/84236) · 열림 · 미병합

[상대 원문](https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5787022600) · [기여 근거](https://github.com/Halldrix/hermes-agent/commit/e99497e5101358b496ca860a3e42c1b623375287) · [원문 영역 캡처](captures/2026-09-29/hermes-stop-correction.png)

<details><summary>후속 기록과 캡처</summary>

**2026-09-23 · @Halldrix**

[![hermes-stop-counterevidence](cards/2026-09-29/hermes-stop-counterevidence.png)](https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5786674461)

</details>

---

## 09. Hermes Agent | 모범적인 검토라는 평가와 실제 패치 적용

**@MestreY0d4-Uninter · 2026-09-12 KST**

모범적인 검토에 감사드립니다. *(발췌 번역)*

[![MestreY0d4-Uninter source excerpt](cards/2026-09-29/hermes-approval.png)](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201)

상대는 재현 예제·실행된 검사·패치가 빠르고 정확한 반영에 도움이 됐다고 밝혔다. 파일 해시를 확인하고 패치와 검사 파일을 그대로 적용했으며, 9월 21일 후속 답변에서도 우리의 지침과 검사를 활용한 포팅 결과를 보고했다. 그 과정에서 상대가 추가로 발견하고 수정한 내용은 상대의 기여다.

**조회 당시 상태:** [PR #22982](https://github.com/NousResearch/hermes-agent/pull/22982) · 열림 · 미병합

[상대 원문](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5643327201) · [기여 근거](https://github.com/MestreY0d4-Uninter/hermes-agent/commit/501be10cce7159a08279c89c724db602d9770601) · [원문 영역 캡처](captures/2026-09-29/hermes-approval.png)

<details><summary>후속 기록과 캡처</summary>

**2026-09-21 · @MestreY0d4-Uninter**

[![hermes-approval-followthrough](cards/2026-09-29/hermes-approval-followthrough.png)](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5756049894)

</details>

---

## 앞으로 덧붙일 기준

새 반응을 현재 작업 중 확인했을 때 출처·작성자·날짜·원문 발췌·관련 기여·당시 상태를 함께 추가한다. 같은 답변을 여러 번의 독립적인 인정으로 세지 않고, 봇이나 우리 자신의 댓글도 외부 인정 건수에서 제외한다. 예약이나 상시 감시는 설정하지 않았다.

원문과 기여는 각 작성자의 것으로 남는다. 특정 작업에 대한 반응을 기관이나 프로젝트의 포괄적인 보증으로 확대하지 않는다. 비공개 대화·이메일 알림·계정 비밀은 공개 묶음에 포함하지 않았다.

[Source index](sources/2026-09-29.json) · [PR states](status/2026-09-29.json) · [Capture method](CAPTURE_METHOD.md) · [Integrity manifest](MANIFEST.json) · [Add a record](ADD_RECORD.md)

**Zero × Youngseok Oh**
