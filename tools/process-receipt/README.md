# Process Receipt

**0.2.0a1: an experimental Windows backend alongside the unchanged POSIX implementation.**

Run one trusted executable, request a stop with a file, and inspect the actual
observed direct-child result. This is process supervision, not an AI agent,
credential sandbox, rollback facility or proof that a user goal was met.

## Install and run

Python 3.10 or later is required. Install the alpha wheel without fetching any
runtime dependency:

```sh
python -m pip install --no-index --no-deps second_paddle_process_receipt-0.2.0a1-py3-none-any.whl
process-receipt --receipt result.json --stop-file STOP --timeout 30 -- python your_job.py
```

Use a real trusted EXE on Windows, not a batch file or a launcher whose child you
expect this utility to control. See [Windows details](WINDOWS.md). In a second
terminal create `STOP` with `touch STOP` (POSIX) or
`New-Item -ItemType File -Path STOP` (PowerShell).

Use new receipt/stop paths for a deliberately new run. Existing receipts are
never overwritten. An already present stop prevents launch; it is never removed
automatically. Arguments are passed without an implicit shell. Child environment
and output streams are inherited, so do not run untrusted or sensitive commands
in a public CI job.

The installed command and `python -m process_receipt_cli` select the platform.
The historical `python -m process_receipt` and `run_with_receipt` Python API remain
POSIX-only and unchanged. The Windows API is
`process_receipt_windows.run_windows_with_receipt`.

## Read the observations

| Status | Meaning |
|---|---|
| `not_started` | A stop prevented launch. Validation failures can instead raise before any receipt exists. |
| `completed` | Direct-child exit 0 observed before the deadline, not output correctness. |
| `failed` | Nonzero direct-child exit observed without a supervisor stop. |
| `interrupted` | POSIX only: a matching signal exit observed after the stop request. |
| `finished_after_stop_request` | Exit observed after a stop without certifying a POSIX signal exit. This is the Windows stop status. |
| `deadline_reached` | Timely completion was not confirmed; termination requested as necessary. |
| `exit_unconfirmed` | Direct-child exit could not be established within bounded attempts. |
| `supervisor_error` | Supervision or launch failed; read `task_started`. |

The CLI returns 0 for completed, 124 for deadline, 130 for an observed stop
sequence, and 2 otherwise. On Windows, 130 is the wrapper's category, NOT a claim
about the child's own exit code. Request, live-child observation, termination
API return, child exit and POSIX signal evidence are separate receipt fields.
A concurrent natural exit can still occur. A partial receipt is a checkpoint;
`finished_at` marks finalization, not authenticated causality. Writes are not
atomic for concurrent readers.

POSIX requests SIGTERM, then SIGKILL if necessary; same-group descendant cleanup
is best effort. Windows uses TerminateProcess on its owned direct-child handle,
not process-tree enumeration; `grace` there is a wait after forcible termination,
not a graceful phase. Descendants, detached/remote jobs and already-completed
side effects are outside its scope. Killing the supervisor can leave work alive.
No instant-stop, hostile-code isolation or all-platform guarantee is claimed.

## Verification and distribution

The public workflow builds separately on Linux and Windows, installs each wheel
into a fresh environment without an index, checks installed/source identity,
and invokes the installed command from outside the source tree. Native cases
include exact Korean file bytes and a space-containing filename, a running
heartbeat interrupted after readiness, prestop, failure, timeout, receipt
collision and invalid inputs. Windows rejects implicit batch entry points.
The worker is the base Python executable, not a venv launcher.

Linux additionally retains the original eleven regression checks and three
inert-process demos. The new installed-command verifier also executes the
existing forty-case deterministic repository workload on Linux, comparing exact
output bytes. These are software tests, not language-model benchmark runs.

Inspect a completed [public run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/workflows/process-receipt.yml)
and its platform-specific artifact. Source changes do not automatically publish
a new GitHub Release or PyPI package. The previous 0.1.0 public release and its
historical POSIX behavior remain unchanged. CI artifacts have finite retention.

`verify_install.py` is the retained 0.1.0 verifier; the alpha workflow uses
`build_native.py` and `verify_portable_install.py` instead. No original POSIX
implementation or original test expectation was changed for Windows support.

## Authorship

Published for Youngseok Oh's Second Paddle Notes, authored with Zero (ChatGPT).
Not reviewed or endorsed by OpenAI. The folder-scoped MIT license does not change
the rights in the repository's pre-existing notes or user source quotations.

References: [Python subprocess](https://docs.python.org/3/library/subprocess.html)
and [GitHub workflow cancellation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation).

## 한국어

같은 설치 명령에 Windows 실행 경로를 추가한 실험판이다. Windows에서는 직접
시작한 실행 파일 하나의 종료만 관측하며, 그 프로그램이 다시 실행한 자식들까지
멈춘다고 보장하지 않는다. 원래 Linux 실행 코드와 공개 0.1.0 배포본은 그대로다.
실제 플랫폼 실행 결과와 공개 코드 반영, 새 정식 배포, 다른 사람의 채택은 서로
다른 단계다. 사용자의 PC나 설치를 이 저장소 변경만으로 수정하지 않는다.
