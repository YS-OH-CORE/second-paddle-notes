# Quiet CLI interruption: a bounded follow-up

Youngseok Oh (오영석) × Zero (ChatGPT) · 23 September 2026

**Result:** in a real Linux quiet single-query CLI process at `e99497e5101358b496ca860a3e42c1b623375287`, a narrow exception-path candidate added one interruption notice on **stderr**, kept exit code **130**, and left stdout unchanged. This is a tested candidate in a disposable checkout, not an upstream adoption or a general cancellation fix.

## Start with the other contributor's evidence

Halldrix supplied the [CLI follow-up on #84207][followup] and the [sanitized mock and harness][gist]. The subsequent [thread-topology correction][topology] matters: SIGINT unwinds the main thread's wait; the agent worker is abandoned during process teardown. Our earlier inference that `run_conversation` itself unwinds was not established. The absence of a finalizer log line and the absent CLI result are observations; neither alone proves the complete thread lifecycle.

We reused the **unchanged `make_mock`** from the pinned public script. The process runner and assertions here are new work by Zero, not an unchanged rerun of the original harness. Gist source SHA-256: `0c24f281e5702b7f6b8dca1530b50175426d5df2e95bbae54eb18ffae25387be`.

## Observed four-process comparison

[Completed public run 35805467618][run], job `107005179472`, workflow commit `59debf8c127946d1e56d5898ad69650c0ce57fd0`. The returned job log includes the four `CASE` records and `ZERO_CLI_E2E_RESULT` with `success=true` and `source_restored=true`.

| Process | Exit | Model reply printed | New notice on stderr | `Turn ended` lines |
|---|---:|---|---:|---:|
| Original, no signal | 0 | `MOCK_REPLY_OK` | 0 | 1 |
| Original, SIGINT during request | 130 | No | 0 | 0 |
| Candidate, no signal | 0 | `MOCK_REPLY_OK` | 0 | 1 |
| Candidate, SIGINT during request | 130 | No | 1 | 0 |

All four processes reached the local sentinel request. SIGINT was actually sent only in the two interrupted cases. Original/candidate normal stdout was exactly equal; original/candidate interrupted stdout was also exactly equal. One four-case development comparison does not estimate a production failure rate.

**Important raw-output detail:** stdout was not literally empty. Every process printed an existing warning that the tirith scanner was enabled but unavailable and pattern matching would be used. We did not disable that setting or remove the warning. The mock also logged a `BrokenPipeError` after writing to a connection whose CLI process had exited; this is retained in the job log, not described as an error-free run.

## Narrow candidate

Inside `_run_quiet_single_query`'s `except KeyboardInterrupt`, after the existing emitter branch and before the session-ID line:

```python
if emitter is None:
    print("Turn interrupted.", file=sys.stderr, flush=True)
```

The existing exit remains 130. The neutral text does not assert who originated the signal. Stderr keeps the diagnostic separate from answer stdout. The candidate does **not** make `finalize_turn` finish, recover streamed output, prove tool cleanup, or repair persistence. The interrupted candidate still had zero `Turn ended` lines. Whether this wording and placement should be integrated is for the maintainer to decide.

## Reproduction and the first failed checker

Use the [pinned workflow][workflow] for the complete setup in a disposable Ubuntu runner. It installs `uv==0.12.17`, uses the target's unchanged frozen lockfile with Python 3.12, and runs [the v2 adapter][v2]. That adapter verifies and loads [the pinned original orchestration][v1], applying only its documented checker corrections and neutral candidate wording. Do not run against an installed personal Hermes workspace.

The child CLI uses a fresh HOME/HERMES_HOME, fake mock credentials, and a minimal environment. Python socket connections are restricted to loopback in this fixture; this is not an OS sandbox or a change to user security settings. No real model, private conversation, account token, or remote production target is involved. Setup still downloads public source and dependencies.

[Run 35805232482][first] failed our initial checker after two baseline processes, **before candidate execution**: it incorrectly required absolutely empty stdout, so the unrelated startup warning tripped it. The second run checks the actual missing closing notice and exact original/candidate stdout preservation. It does not turn the first failure into a pass, and no failed output was removed.

## Limits and contribution roles

Executed: real quiet CLI, local mock chat-completion request, actual process SIGINT, separate output streams, normal controls, disposable Linux environment. Not executed: live-model service, tool mode, TUI, Windows, stream-JSON, SIGTERM, repeated-signal races, full upstream suite, or the recipient's reported 129-test suite. The application source was restored after the comparison.

Halldrix owns the supplied mock, mechanism investigation and prior integration. Youngseok Oh sets the collaboration's direction and priorities; Zero supplied the new orchestration, candidate, execution analysis and writing. There is no claim of solo human engineering credentials, independent expert certification, upstream release, or an institutional endorsement.

## 한국어 요약

헤르메스 개발자 Halldrix가 공개한 재현 자료를 이어받아, 실제 Linux 명령줄 프로그램을 네 번 실행했습니다. 원본과 수정 후보 각각에서 정상 실행 및 SIGINT 중단을 비교했습니다. 정상 답변은 그대로였고, 중단한 경우에는 후보에서만 `Turn interrupted.` 안내가 표준 오류(stderr)에 한 번 나왔습니다. 종료 코드는 둘 다 130입니다.

이전 함수 안의 검사를 전체 실행의 증거로 쓰지 않았습니다. 이번에는 실제 프로세스에 중단 신호를 보냈지만, 모델의 응답은 로컬 모의 서버가 제공합니다. 도구 실행·실제 모델·아이폰·Windows·대화형 화면·전체 검사 모음을 확인한 결과는 아닙니다.

첫 실행에서는 원래부터 출력되던 검사기 경고 때문에 제가 만든 채점 조건이 실패했습니다. 경고를 지우거나 검사기를 끄지 않고, ‘완전히 빈 출력’ 대신 ‘중단 안내의 유무’와 ‘원본/후보의 답변 출력 동일성’을 보도록 고쳤습니다. 첫 실패와 두 번째 결과는 둘 다 공개돼 있습니다. 모의 서버의 BrokenPipeError도 실행 기록에 남아 있습니다.

후보는 안내가 나오지 않는 문제만 다룹니다. 작업 스레드가 정상 마무리되거나 저장·정리까지 해결됐다는 뜻은 아닙니다. 원래 개발자의 재현 코드와 원인 조사, 영석의 방향 판단, Zero의 새 실행 조율과 분석을 구분합니다. 아직 상대가 이 후속 후보를 반영했다는 확인은 없습니다.

[followup]: https://github.com/NousResearch/hermes-agent/issues/84207#issuecomment-5787022803
[topology]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5787022600
[gist]: https://gist.github.com/Halldrix/1eaaef203821dae5c8abfb94c24a2ccd
[run]: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35805467618
[first]: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35805232482
[workflow]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/59debf8c127946d1e56d5898ad69650c0ce57fd0/.github/workflows/cli-sigint-20260923.yml
[v2]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/73c095a8105c032c3cc2174d95573402048d2c48/checks/cli-sigint/run_check_v2.py
[v1]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/0928493b2e1ce777fcf38866ce3cc69174270eb1/checks/cli-sigint/run_check.py
