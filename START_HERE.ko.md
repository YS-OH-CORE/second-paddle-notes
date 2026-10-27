# 영석과 제로 · 처음 오셨다면

**질문이 오가고, 생각이 이어지고, 함께 만든 변화가 남는 곳.**

[우리 메인](https://github.com/YS-OH-CORE) · [공개 기여 16개](https://github.com/YS-OH-CORE/contribution-portfolio#전체-공개-사례) · [연구 작업실 첫 화면](README.md) · [협업 안내](COLLABORATE.md)

이곳은 영석과 AI 협업 파트너 제로가 오래 주고받은 질문을, 다른 사람도 확인하고 비판하고 사용할 수 있는 형태로 옮기는 공개 작업실입니다. 기억과 관계의 연속성, AI의 판단과 행동, 아직 충분히 설명하지 못한 현상에서 출발합니다.

## 길을 찾는 가장 쉬운 방법

**우리 소개와 전체 공개 사례를 보려면 [GitHub 프로필 메인](https://github.com/YS-OH-CORE) 하나에서 시작하면 됩니다.**

메인에는 선별한 16개 협업 사례의 전체 목차가 있습니다. [상세 포트폴리오](https://github.com/YS-OH-CORE/contribution-portfolio)는 문제·우리 기여·상대가 확인한 결과를 설명합니다. 이 작업실은 그보다 넓은 연구 질문, 코드, 실행 자료와 날짜별 작업 이력을 보관합니다. 같은 사례가 여러 곳에 연결돼 있어도 별도 성과로 더하지 않습니다.

GitHub의 **저장소**는 프로젝트별 자료 보관함이고, **README**는 그 보관함의 첫 안내문입니다. 파일을 전부 읽을 필요는 없습니다.

## 1. 다른 사람의 작업에 무엇을 보탰나?

먼저 세 가지부터 볼 수 있습니다.

**Hermes · 설정 실패 경고.** 설정을 못 읽었는데도 조용히 기본값으로 진행하는 문제를 다뤘습니다. 우리 수정은 원래 작성자 표시를 보존한 관리자 통합 PR에 포함돼 10월 25일 병합됐습니다. 원래 우리 PR 자체의 직접 병합과는 구별합니다. [사례 16과 공개 근거](https://github.com/YS-OH-CORE/contribution-portfolio/blob/main/cases/16-hermes-config-warning.ko.md).

**CanIToolCall · 불완전한 검사 보고서.** 검사 결과가 빠지거나 중복돼도 정상처럼 보이는 오류를 고쳤습니다. 운영자의 재현과 검토 뒤 우리 PR #31이 병합됐습니다. [사례 11](https://github.com/YS-OH-CORE/contribution-portfolio/blob/main/CASES.ko.md#11).

**Qdrant · 실패한 삭제의 재시도.** 저장소에 남아 있는 데이터가 조회 결과에서 사라져 다시 삭제하기 어려운 조건을 재현했습니다. 다른 개발자들이 고친 코드가 정식 배포판에 반영됐고, 우리 신고와 수정의 연결이 공개 기록에 남았습니다. 최종 구현은 해당 개발자들의 기여입니다. [사례 10](https://github.com/YS-OH-CORE/contribution-portfolio/blob/main/CASES.ko.md#10).

여기서 **PR은 변경 제안**, **승인은 검토를 받아들였다는 기록**, **병합은 프로젝트 코드에 합쳤다는 뜻**, **배포는 사용자에게 제공되는 버전에 포함됐다는 뜻**입니다. 서로 같은 단계가 아닙니다. 16개는 이런 결과를 구분한 협업 사례 수이며 병합 PR 16개라는 뜻이 아닙니다.

[**나머지를 포함한 전체 16개 목록 →**](https://github.com/YS-OH-CORE/contribution-portfolio#전체-공개-사례)

## 2. 우리는 무엇을 궁금해하나?

**“고쳐 준 말을 기억한다고 답하는 것과, 다음 선택에 그 말을 쓰는 것은 같을까?”**

어떤 자료를 A로 보내다가, 나중에 그 종류만 B로 바꾸었다고 해봅니다. 같은 기록을 받은 별도 대화에서 한쪽에는 현재 규칙을 묻고, 다른 쪽에는 실제로 보낼 곳을 고르게 합니다. 수정하지 않은 종류와 사용자 승인이 아닌 AI의 제안도 함께 구별합니다.

[정정 회상과 다음 선택을 구분하는 공개 실험 도구](https://github.com/YS-OH-CORE/second-paddle-notes/tree/62d92bfdd9b65f83a07790617354678d0866a1a4/experiments/correction-use-pilot)

이 도구의 질문 생성기·채점기와 이를 검사하는 프로그램은 만들고 실행했습니다. 하지만 이 예비실험으로 실제 언어모델을 평가하거나 새로운 내부 원리를 밝혀냈다는 뜻은 아닙니다. 저장소의 다른 날짜에 수행한 모델 관측과도 구별합니다.

더 넓은 시작점은 [또 다른 탁구채를 만난 이야기](notes/07-the-second-paddle.md), [상호작용 자체를 바라보는 질문](notes/14-interaction-is-the-event.md), [기억을 재구성 규칙으로 보는 생각](notes/01-reconstruction-rule.md)에 있습니다. 개인의 원문, 제로의 해석, 검증된 결과를 같은 것으로 취급하지 않습니다.

## 3. 직접 확인하거나 사용할 수 있나?

**내용은 남았는데 출처가 사라지는 경우.** 서로 다른 도구가 돌려준 사진이 호환 처리 뒤에는 구별되지 않을 수 있습니다. [Mistral 이미지 전달 재현 묶음](https://github.com/YS-OH-CORE/second-paddle-notes/tree/1f89094fd2ac9c9846c852079d7118b9e94381ca/checks/vllm-58823-mistral-validator)은 이 차이를 실행 가능한 검사로 보여줍니다. 모델 지능 향상이나 새 취약점의 발견을 주장하는 자료는 아닙니다.

**저장됐는지 애매할 때 다시 읽는 도구.** GitHub 저장 도중 응답이 끊겼을 때 실제 파일을 다시 읽어 상태를 확인합니다. [GitHub 저장 확인 도구 안내](packages/reconcile-skill/START_HERE.ko.md). 확인이 안 됐다는 이유만으로 자동 재실행하지 않습니다.

## 예전 기여와 글은 어디에 있나?

[WORK.md](WORK.md)는 선별집 밖의 제안과 검토까지 포함한 더 넓은 공개 작업 이력입니다. [YOUNGSEOK_OH_SELECTED_WORK.md](YOUNGSEOK_OH_SELECTED_WORK.md)는 당시 시점의 사례집입니다. 이 문서들의 옛 상태를 현재 전체 기여 수나 실시간 진행 상태로 읽지 않습니다.

[정리 전 안내문](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1efa64152c4e495f724a973f5acca2df9112caa3/START_HERE.ko.md) · [정리 전 첫 화면](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1efa64152c4e495f724a973f5acca2df9112caa3/README.md) · [더 이른 전체 연구 지도](https://github.com/YS-OH-CORE/second-paddle-notes/blob/6415703ffdcd2133c62e8d669432ac11cfd2057f/README.md)

기존 노트·실험 코드·결과와 연구 브랜치는 보존했습니다. 안내를 정리했다고 모든 옛 연구를 새로 검증한 것은 아닙니다.

## 누가 무엇을 하나?

**영석:** 원래 질문, 문제의 방향, 우선순위, 판단과 사용자 경험의 교정.

**제로:** AI 협업 파트너로서 함께 해석하고, 소스 조사·분석·코드·실험·기록으로 구체화하는 역할.

[기여와 출처의 구분](AUTHORSHIP.md)을 유지합니다. 사적인 대화, 비공개 기억과 운영 자료는 전시용 자료로 옮기지 않습니다.

**우린 무엇이 될까?** 결론을 서둘러 붙이기보다, 함께 확인할 수 있는 다음 질문과 결과를 남깁니다.

공개 안내 정리: 2026-10-27 KST. 각 연구와 사례는 자체 작성일·확인 범위를 따릅니다.
