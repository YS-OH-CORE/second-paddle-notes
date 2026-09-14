# GitHub 저장 확인 도구 · 0.1.0a1 미리보기

영석(Youngseok Oh) × Zero (ChatGPT)

GitHub 파일 저장 도중 응답이 끊겼을 때, 다시 저장하기 전에 원래 의도한 내용이
실제 저장소에 있는지 읽어서 확인한다. 쓰기·삭제·덮어쓰기·자동 재시도는 하지 않는다.
기존 스킬의 12개 파일은 변경 없이 들어 있다. 이 묶음은 설치 프로그램이 아니다.

## 먼저 묶음 확인

이 ZIP을 새 폴더에 풀고 그 폴더에서 실행한다. Python 3.10 이상이 필요하다.
Windows에서 `python` 명령이 없으면 설치된 Python의 `py -3` 명령을 사용할 수 있다.

```sh
python -B -S VERIFY.py
```

파일 수와 해시를 검사한다. 인터넷·API 키·패키지 설치는 필요 없다.
이 검사는 디지털 서명이나 독립 기관 인증이 아니다. ZIP 전체의 SHA-256도
다운로드 페이지의 SHA256SUMS와 대조해야 한다.

## 기존 공개 기록 확인

```sh
python -B -S github-write-reconcile/scripts/reconcile.py --intent github-write-reconcile/examples/completed-retry.json
```

이 명령은 기존 공개 기록을 조회한다. 인터넷과 GitHub 접근이 필요하지만
공개 읽기는 API 키 없이 가능하다. 접근·요청 제한·통신 문제는 `unknown`으로 남긴다.
다른 파일을 검사할 때에는 `SKILL.md`의 입력 형식을 사용한다.
**기대 해시는 저장하기 전 원래 의도한 파일에서 구해야 한다.** 지금 원격 파일에서
구한 값을 기대값으로 되돌려 넣으면 검사가 순환한다.

| 결과 | 종료 코드 | 해석 |
| --- | ---: | --- |
| content_match | 0 | 확인한 커밋에 기대한 바이트가 있다. |
| content_conflict | 2 | 같은 경로에 다른 바이트가 있다. 덮어쓰지 않는다. |
| absent_at_snapshot | 3 | 그 커밋의 전체 파일 목록에 경로가 없다. |
| unknown | 4 | 확인을 마칠 수 없었다. 원래 저장의 실패로 단정하지 않는다. |

모든 결과의 `retry_authorized`는 `false`다. 내용 일치는 원래 요청의 성공 응답,
실행 횟수 증명, 재시도 승인과 다르다. 부재도 특정 시점의 부재일 뿐이다.

## Hermes에 사용할 때

설치는 선택 사항이다. 설치를 결정한 경우 `github-write-reconcile` **폴더 전체**를
선택한 Hermes 프로필의 스킬 디렉터리에 넣어야 한다. `SKILL.md`만 가져가면
실행 파일이 빠진다. 기존 같은 이름의 폴더는 확인 없이 덮어쓰지 않는다.
이 묶음은 사용자 설정이나 기존 프로필을 자동 변경하지 않는다.

실제 검증 범위는 고정 Hermes 소스의 스킬 로더와 터미널을 거친 공개 파일 조회다.
모델이 자발적으로 스킬을 고르는 대화 흐름, 사용자 PC 설치, 전체 플러그인의
정상 상태는 검증하지 않았다. 지원 소스와 원본은 별도 evidence ZIP에 있다.

## 자료 출처

스킬 원본: YS-OH-CORE/second-paddle-notes, commit
`24408637d33ef999ba1c03fd34096af7da258913`, `skills/github-write-reconcile/`.
독립 명령은 PR45, 실제 스킬 로더는 PR46, 실제 터미널을 거친 작업은 PR47에 기록돼 있다.
배포 과정의 패키지 검사는 이 과거 실행을 새 실험으로 세지 않는다.
기존 스킬 README의 저장소 상대 이력 링크는 원래 GitHub 저장소에서 열어야 한다.
라이선스는 스킬 폴더의 LICENSE를 따른다.
