# Process Receipt

**A runnable tool, not another declaration that cancellation works.**

Run one trusted command, request a stop by creating a file, and inspect whether the
supervisor actually observed its direct child exit. Standard-library Python;
POSIX only; developed and tested on Linux. No model, account, API key, service,
extra package, or remote-control connection is required.

This utility is a practical companion to [From Prompt to World](../../notes/12-from-prompt-to-world.md)
and [One Point Is Not Ten](../../notes/05-one-point-is-not-ten.md). It is new
AI-assisted implementation work for Youngseok Oh's public project, not a new
Youngseok-authored quotation, a language-model benchmark, or an independent
replication. It does not implement the previously prepared model-decision study.

## Use it

With Python 3.10 or later, from this directory:

```sh
python3 process_receipt.py --receipt result.json --timeout 30 --stop-file STOP -- python3 your_job.py
```

In a second terminal in the same directory, request a stop:

```sh
touch STOP
```

Use a **new receipt filename** for each run. An existing receipt is never
overwritten. An already existing STOP path prevents the command from starting;
the tool never removes it or automatically resumes a task. Choose another stop
path for a deliberately authorized new run, rather than assuming the old stop
request has expired.

Arguments after `--` are passed as an argument list, without a shell. The tool
inherits the calling environment and streams the child's output to the caller.
It is **not a credential sandbox**: only run commands you trust. The receipt does
not serialize command arguments, environment values, stop-file contents, or
child stdout/stderr. The underlying command can still print secrets; do not run
sensitive commands in public CI.

## Read the receipt, not just the wrapper's status

| Status | What was observed |
|---|---|
| `not_started` | A stop was already present before launch. |
| `completed` | The direct child's exit code 0 was observed before the deadline. This is not proof its work is correct. |
| `failed` | A nonzero direct-child exit was observed without a supervisor stop request. |
| `interrupted` | The child was observed alive when stopping began; the supervisor requested a termination signal and observed a corresponding signal exit. |
| `finished_after_stop_request` | The child exited after a stop was requested, but signal termination was not established, for example a cooperative exit code 0. |
| `deadline_reached` | Timely completion was not confirmed by the deadline; termination was requested as necessary. |
| `exit_unconfirmed` | The bounded termination attempts did not establish direct-child exit. |
| `supervisor_error` | Preparation or supervision failed. Inspect `task_started` rather than assuming execution occurred. |

`stop_reason`, `alive_when_stop_observed`, `signals_requested`,
`direct_child_exit_observed`, and `child_exit_code` are distinct observations.
A signal request alone does not establish a stopped process. An external actor
could also signal the process, so this is not an independently authenticated
causal proof. A receipt still being written is a checkpoint; only a record with
`finished_at` is final. Receipt writes are not atomic for concurrent readers.

The CLI returns 0 for `completed`, 130 for `interrupted`, 124 for a deadline,
and 2 otherwise. It intentionally does not turn an unconfirmed outcome into
success. After a stop it first requests SIGTERM, then SIGKILL after the grace
period if the direct child is still running.

## Run the public demonstration

```sh
python3 -m unittest -v
python3 demo.py --out fresh-demo-results
```

The demonstration starts **real but inert Python processes** and writes three
sets of receipts and heartbeat files: normal completion; interruption after a
stop file; and SIGKILL fallback when a child ignores SIGTERM. It checks that an
interrupted workload did not reach its natural-completion file. The output
folder must be new. It has no external network calls or private inputs.

[Public CI runs](https://github.com/YS-OH-CORE/second-paddle-notes/actions/workflows/process-receipt.yml)
run the same checks and retain their generated results. A workflow being present
is not a successful run. Open an actual completed run and read its logs and
`process-receipt-demo` artifact. The download interface may require a GitHub
login; the code and public run logs can be inspected separately.

## Boundaries

This is not an emergency-stop guarantee. Polling, scheduling, process startup,
I/O, and termination can be delayed. The deadline concerns observation by the
supervisor, not an exact timestamp of the child's final side effect. An exit
first observed after the deadline is not certified as timely even if it actually
happened earlier. SIGKILL of the supervisor itself cannot be handled.

Signals target the task's new process group. The receipt confirms only the
direct child's exit; cleanup of same-group descendants is best effort. Detached
sessions, remote jobs, kernel-blocked processes, and other machines are not
covered. Completed side effects cannot be undone. The local stop file is a
mechanism for its caller, not authentication of a particular human's will. Use a
trusted local filesystem and do not mistake file existence or a receipt hash for
semantic fidelity.

This folder does not alter the project's source quotations, existing model-study
criteria, other workflows, account permissions, or private workspace. It makes
no claim about fixing all GitHub Actions cancellation or changing any AI model.

## References and authorship

- [Python subprocess: process groups and return codes](https://docs.python.org/3/library/subprocess.html)
- [GitHub: workflow cancellation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation)

Published as a user-authorized contribution to **Youngseok Oh's Second Paddle
Notes**. Code, tests, and this explanatory text were authored with **Zero
(ChatGPT)**. Not reviewed or endorsed by OpenAI. The MIT license in this folder
applies only to these newly authored utility files, not the repository's
pre-existing notes or source material.

## 한국어

`취소 요청을 보냈다`, `화면에 취소됐다고 뜬다`, `실제 프로그램이 끝났다`를
구분하는 실행 도구다. 새 기록 파일과 중단 파일 위치를 정해 프로그램을
시작하고, 중단 파일을 만들면 종료를 요청한 뒤 실제 자식 프로세스의 종료를
관측한다. 원문 보관이나 AI의 의미 이해를 검증하는 도구는 아니다. 사용자가
매번 이 도구로 일을 관리해야 한다는 뜻도 아니다. 공개 실행 예제와 결과는
다른 사람이 확인하고 개선할 수 있도록 제공한다.
