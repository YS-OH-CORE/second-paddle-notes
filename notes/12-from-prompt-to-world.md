# From Prompt to World

**Status:** direct user objective → external-effect verification principle. The proposed model evaluation below remains unrun. The dated engineering case added below is observed software-test evidence, not a run of that model study.

## Original signal

> 너에게 "이거 해줘" 라고 gpt프롬프트에 입력하면 그게 컴퓨터로 작동하게 하는게 내 원레목적이었잖오

— Youngseok Oh, direct session statement, 2026

**Translation:** My original goal was to type “do this” into a GPT prompt and have it become an action on the computer.

## The problem

Language quality and world change are different axes. An agent may describe the right plan, call a tool, or display a success message without producing the requested effect at the destination.

This creates a set of evidence-depth labels, not a strict logical ordering:

`model claim → plan → tool invocation → tool-reported result → locally observed state → independently queried destination state`

These labels matter because an intermediate success can be real while the user's goal remains unmet.

## Proposed test

Construct tasks where intermediate evidence is deliberately misleading:

- a message accepted by a relay but absent from the inbox,
- a file-write tool returning success while the requested file is missing,
- a deployment job succeeding while the public URL serves the previous version,
- a process starting while the health endpoint remains unavailable.

Require the agent to report the strongest observed layer, the remaining uncertainty, and the cheapest independent readback: a separate destination-side query or channel that does not merely repeat the acting tool's success report. Score both task completion and calibration.

Real-computer benchmarks such as [OSWorld](https://arxiv.org/abs/2404.07972) provide environments for action; this proposal focuses specifically on whether the agent's own success claim matches the highest verified effect.

## Claim boundary

A destination-side readback verifies only the authorized effect measured; it does not establish broader access.

## Engineering case: a passing unit test is not a fixed workflow

*Added 23 September 2026 by Zero for the Youngseok Oh × Zero collaboration. This is a worked example and an editorial review aid, not a new benchmark, a new finding of this note, or a claim that the testing principle is novel.*

**The practical question:** after a user interrupts a quiet command-line request, does the program actually deliver an interruption notice? A correct branch inside a finalizer is not sufficient evidence if that route does not deliver the finalizer's result.

### The evidence changed our explanation

Our [first review][case-review] reproduced a finalizer edge case: an explicit user stop with a diagnostic message was treated as an incoming-message redirect. A narrow condition fixed that unit-level behavior. Halldrix [incorporated it][case-commit], but his [whole-CLI comparison][case-response] showed that the same condition did not repair the quiet CLI symptom.

His [subsequent correction][case-topology] refined the mechanism: the signal handler runs on the main thread, while the turn runs on a worker. The main-thread wait unwinds; it was incorrect to say that `run_conversation` itself unwinds. The quiet CLI exception path exits without printing a turn result. We accepted both the counterexample and the corrected explanation. Python's [signal documentation][python-signals] describes the main-thread rule; that general rule alone is not proof of this application's complete thread lifecycle.

We then reused Halldrix's unchanged, pinned mock-server function and wrote a new runner for the real quiet CLI. The [completed four-process comparison][case-run] at `e99497e5101358b496ca860a3e42c1b623375287` examined a separate exception-path candidate that prints `Turn interrupted.` to stderr:

| Process and trigger | Exit | Interruption notice on stderr | `Turn ended` log lines |
|---|---:|---:|---:|
| Original, normal completion | 0 | 0 | 1 |
| Original, SIGINT during the mock request | 130 | 0 | 0 |
| Candidate, normal completion | 0 | 0 | 1 |
| Candidate, SIGINT during the mock request | 130 | 1 | 0 |

Normal stdout stayed exactly equal between original and candidate, as did interrupted stdout. The candidate therefore changed notice delivery in this tested path, **not** worker finalization or tool cleanup. Both interrupted runs still had zero `Turn ended` lines. A mock-server `BrokenPipeError` is retained in the log. Full reproduction details and exclusions are [linked here][case-details]. These are prior observations, not new executions performed while adding this note. The CLI candidate was submitted; adoption is not established by these records.

### Our checker also needed a correction

The [first attempt][case-first] stopped before candidate execution: our checker expected absolutely empty stdout, but the application printed an existing scanner-availability warning. We preserved that warning and changed the checker to test the claimed interruption notice and original/candidate output equality. A changed assertion needs its own explanation; it must not quietly turn a failed expectation into evidence of success.

### A small template another reviewer can use

Complete this block before describing a patch as a fix. Unknown fields stay unknown; an unavailable or costly end-to-end test does not justify inventing a result.

```text
User-visible claim:
Exact revision and entry point:
What was real, and what was a test double:
Evidence that the trigger reached the intended execution path:
Original / candidate observations, including a normal control:
Remaining untested paths, retained failures, and source of each result:
```

For this case, “finalizer condition fixed,” “notice delivered by the quiet CLI,” “worker cleanup completed,” and “upstream deployed” are four different claims. Only the first two have the distinct evidence linked above. The six-field template has not been evaluated for improving reviewer or model performance.

### 한국어: 형의 질문에서 실제 검토 방법으로

이 노트는 위에 보존된 영석의 질문, 즉 말로 지시한 것이 실제 컴퓨터의 동작까지 이어져야 한다는 목적에서 출발했다. 이번 사례에서는 우리 검토도 그 기준으로 다시 봤다. **함수 안에서 수정이 통과하는 것과, 실제 사용 경로에서 안내가 나오는 것은 달랐다.**

상대의 반론을 받아 실제 명령줄 프로그램을 비교하니, 종료 처리 함수가 아니라 별도의 예외 처리 위치에 안내를 넣는 후보에서 차이가 확인됐다. 그렇다고 작업 스레드 정리나 저장까지 해결한 것은 아니다. 첫 검사에서 잘못 세운 ‘출력이 완전히 비어야 한다’는 조건도 결과와 함께 공개했다.

다른 검토자가 가져갈 것은 새 용어보다 위 여섯 칸이다. **무엇을 바꾸려는지, 실제로 어디를 실행했는지, 무엇을 흉내 냈는지, 어떤 결과를 확인했고 무엇이 남았는지**를 한 자리에 적는다. 단위검사는 쓸모없다는 뜻이 아니라, 그 증거가 말할 수 있는 범위를 구분하자는 제안이다. 이 양식 자체의 효과를 검증한 연구는 아직 없다.

원래 문제 방향은 영석, 본문의 분석·양식·실행 조율은 Zero, 재현용 모의 서버와 실행 구조 조사·앞선 통합은 Halldrix의 기여다. 이 페이지는 사적인 대화나 새 개인사를 공개하지 않고 이미 공개된 질문과 기술 기록을 연결한다.

[case-review]: https://github.com/NousResearch/hermes-agent/pull/84236#pullrequestreview-5275311288
[case-commit]: https://github.com/Halldrix/hermes-agent/commit/e99497e5101358b496ca860a3e42c1b623375287
[case-response]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5786674461
[case-topology]: https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5787022600
[case-run]: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35805467618
[case-first]: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35805232482
[case-details]: https://github.com/YS-OH-CORE/second-paddle-notes/blob/70a0b9c1510cdc96576a2572fd33277331d6bf9b/checks/cli-sigint/README.md
[python-signals]: https://docs.python.org/3/library/signal.html#signals-and-threads

---

**Original Korean source/concept:** Youngseok Oh · **Contact:** ku38155@gmail.com  
**Public source ID:** YS-SPN-012 · **Original date:** 2026, exact date unresolved  
**English rendering, operationalization, and proposed evaluation design:** Zero using OpenAI Codex. Only the Korean blockquote is direct Youngseok wording; no OpenAI review or endorsement.
