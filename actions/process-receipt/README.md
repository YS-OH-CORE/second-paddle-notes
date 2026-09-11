# Process Receipt as a GitHub Action (experimental)

Run a trusted argument vector and pass **observed execution** to downstream
workflow steps, independently of receipt-writing failures. Uses the exact
published Process Receipt **0.2.0a2** wheel; no runtime rewrite, package-index
lookup, pip installation, new API key, model call, or background agent.

This is a composite action. Python 3.10+ must already be on the runner's PATH.
Linux and Windows are the intended native test targets; an unexecuted workflow
is not a test result. See actual runs of `process-receipt-action.yml` and their
`process-receipt-action-*` artifacts for execution evidence.

## Use

```yaml
steps:
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
    with:
      persist-credentials: false
  - id: job
    uses: YS-OH-CORE/second-paddle-notes/actions/process-receipt@main
    with:
      command-json: '["python", "your_trusted_job.py"]'
      timeout: '30'
  - if: always()
    shell: python
    env:
      ACTION_STATUS: ${{ steps.job.outputs.action-status }}
      EXECUTION: ${{ steps.job.outputs.execution-status }}
      STARTED: ${{ steps.job.outputs.task-started }}
      CHILD_EXIT: ${{ steps.job.outputs.child-exit-code }}
    run: |
      import os
      print({k: os.environ[k] for k in ('ACTION_STATUS','EXECUTION','STARTED','CHILD_EXIT')})
```

`@main` is a moving development reference. Pin a **full reviewed commit SHA**
for a fixed consumer dependency. The contribution PR records the tested commit.
On Windows, use the real executable that performs the work, not a launcher whose
child is outside the supervisor's scope. The action does not infer or replace
an executable specified by the caller.

`command-json` is an argument array, not shell text. Shell operators are passed
literally. Inputs enter through environment variables, not code interpolation.
Do not turn issue comments, pull-request titles or model-generated text into
commands without separately establishing that execution is intended and trusted.

## Outputs and step failure

| Output | Meaning |
|---|---|
| `action-status` | `completed`, `failed`, `rejected`, `receipt_persistence_failed`, or `adapter_error` |
| `execution-status` | The runtime's observed status, or `unknown` |
| `task-started` / `exit-observed` | `true`, `false`, or `unknown` |
| `child-exit-code` | Actual direct-child code, or `unknown` |
| `receipt-state` | `finalized`, `unconfirmed`, or `not_created` **by this invocation** |
| `receipt-path` / `summary-path` | Local paths on this runner, not a durable upload |

The action fails its step for **every outcome except completed execution with a
finalized receipt and delivered outputs**. `if: always()` permits a downstream
step to inspect failure outputs. A caller may explicitly use `continue-on-error`
but should then inspect `outcome` and the actual outputs, not assume success.
The conformance workflow deliberately does this to test all failure cases.

Examples:

- Child exited 7: action failed, task started=true, child-exit-code=7.
- Pre-existing STOP: action failed, task started=false; STOP is not deleted.
- Final receipt error after child exited 0: action failed with
  `receipt_persistence_failed`, but execution completed/task started=true/code=0.
- Existing receipt: rejected; it is not read or counted as this execution.
- Unexpected runtime exception: execution remains **unknown**, not false.

**Missing outputs do not prove non-execution.** A killed runner or an I/O failure
while sending action outputs can prevent reporting after the child has acted.
There is no automatic retry, exactly-once guarantee, rollback, durable stderr,
or certification of user-goal satisfaction.

## Mechanism and boundaries

Each invocation downloads one fixed public 13,000-byte wheel with SHA-256
`69c96c6d1be62b4031e6e0f7d5ebf874bf551f15433f75b296c685b9ce2c907d`, verifies its
identity, and imports it from a new temporary directory. It does not modify the
caller's installed package set, PATH or environment files. A default new receipt
is allocated there; a provided receipt path's parent must already exist.

The directly launched process inherits the caller environment **except** GitHub's
four output/environment/path/step-summary command-file variables. Child log text
is temporarily excluded from workflow-command parsing. Neither precaution is a
hostile-code sandbox: trusted code can still access files, network and credentials
available to the job, and inherited output can contain secrets. Use least-privilege
job permissions. A checksum is not an independent security signature.

The underlying runtime's direct-child limits remain: Windows termination is
forcible; launchers' descendants, remote jobs, completed side effects and precise
cancellation latency are not controlled. This action adds no broader stop authority.
No automatic upload is performed. Preserve the files with your own artifact step
where appropriate; review them before sharing.

## Verification and attribution

`test_action.py` runs ten adapter-API tests, including a final-fsync fault around
a real inert child. The workflow separately invokes the **real composite action**
six times per native platform and verifies both outputs and destination effects.
It checks a downstream success-only step executes for a real success and stays
skipped for a real failure. Fault injection is an API test, not a failing physical
disk or an injected fault in an actual composite step. These are author-run
engineering checks, not another person's adoption or a model benchmark.

Code and tests prepared with Zero (ChatGPT) for Youngseok Oh's Second Paddle Notes.
The local MIT license applies only to this new action folder. Existing sources,
release assets, research claims and their rights are unchanged.

References: [GitHub composite actions](https://docs.github.com/en/actions/tutorials/create-actions/create-a-composite-action),
[secure use](https://docs.github.com/en/actions/reference/security/secure-use),
[underlying runtime](../../tools/process-receipt/README.md).

## 한국어

다른 자동화가 실행 결과를 바로 읽을 수 있는 연결부다. 프로그램 실패와
기록 저장 실패를 나누고, 이미 실행된 일을 실행되지 않은 것으로 취급하지
않는다. 사람의 목적을 이해하는 모델은 아니며, 사용자가 이 도구를 관리해야만
작업이 이어진다는 뜻도 아니다. 공개 실행 결과는 작성자의 검사이고 타인의
채택 여부와는 별개다.
