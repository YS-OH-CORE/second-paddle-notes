# Saved form round after a clean Python-process exit

Observed on 2026-09-14, 08:46 KST (2026-09-13, 23:46 UTC).
Prepared by Youngseok Oh with Zero (ChatGPT).

## What was corrected

The first PR #34 workflow had invalid YAML at its compile command (line 24).
[Run 34790113078](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34790113078)
failed before the new experiment could run. The successful
[34790121685](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34790121685)
was the older, single-interpreter experiment, not evidence of a process restart.

The compile command now uses a YAML block. Explicit Bash/pipefail propagates a
probe failure through `tee`, and both output streams enter the log. Local checks
reproduced the YAML parser error, parsed the corrected YAML, checked all run
blocks with `bash -n`, and compiled the probe. A separate shell fixture returned
0 without pipefail and 17 with it when the piped command exited 17. This fixture
checks failure reporting, not LangGraph persistence. Checkout credentials are
not persisted; tracing is disabled; the workflow retains its read-only repository
permission and six-minute cap.

## The observed experiment

[Restart run 34790640065](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34790640065)
completed successfully for PR head `e254b77ff1364aeb031dc7ceae916f28afbb8ad3`.
The runner checked out the PR merge commit
`86d922d05fbf704360fed0f6a621a9dac5c5479b`.
The unchanged earlier experiment also passed in
[run 34790640052](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34790640052).

| Observation | Recorded value |
| --- | --- |
| Parent / process A / process B identifiers | 2464 / 2466 / 2471 |
| A start, A exit observed by parent, B start (monotonic ns) | 591133665035 / 592809348542 / 592899017404 |
| Child exit codes | 0, 0 |
| Synthetic session calls | One initial call in A; one continuation in B |
| Saved and reopened frame | Entire JSON objects equal |
| Original question key | `confirm-process-A` |
| Original opaque state | `opaque-process-A-state` |
| Terminal result | `completed-from-process-B`, `isError: false` |
| External socket attempts during each child exercise | None recorded |

The question text, schema, original key/state, supplied answer, tool name and
arguments were cross-checked, not only the final `status` field. Both processes
reported the same three source-file digests and six pinned package versions.
The opaque state was absent from the question payload exposed for review.
This is one programmed scenario across two child processes, not two independent
trials or a live human approval.

## Read-back evidence

The [original artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34790640065/artifacts/10328551129)
was downloaded: 3,960 bytes, SHA-256
`5eacef632fe2f8ed56d7dc1f3880e976a713b94e26f7063aa2a4cba3115e527a`.
All three ZIP members passed CRC checks. The JSON printed in the execution log
matched the separate JSON result. The dependency list matched the recorded pins;
the executing probe's SHA-256 matched the prepared source.

The [unaltered observation JSON](evidence/process_restart_run34790640065.json)
is retained here beyond the workflow artifact's 14-day retention setting:
4,869 bytes, SHA-256
`838eb0d9b8aaa4ccaa51ddccfb37f615eb3e7487e70aae1550028ab9710bfdd4`.
It contains synthetic fixtures only. Real application checkpoints must not be
published this way. Checking the downloaded files was not a second SDK execution.

## Reproduce and interpret

From this directory in a disposable environment, install `requirements.txt` and run:

```sh
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false \
  python process_restart_probe.py --out /path/to/a/new-output-directory
```

The parent waits for A to exit before starting B, imposes child timeouts, and marks
success only after all correspondence checks. A missing checkpoint or a regenerated
initial request cannot satisfy the assertions. Run without Python optimization;
the script explicitly rejects disabled assertions.

The real LangGraph graph and SQLite saver persist/reopen the form frame. The
`call_tool` sessions are deterministic test doubles, and the answer is programmed.
This establishes the tested clean-exit application path only. It does not test
MCP transport/session recreation, remote-server restart, kill/power-loss recovery,
concurrent replies, or exactly-once remote effects. The earlier in-process MCP
experiment and its attribution remain unchanged. No upstream SDK was patched.

Relevant API behavior: [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts).
Workflow command syntax: [GitHub's maintained workflow reference](https://github.com/github/docs/blob/main/content/actions/reference/workflows-and-actions/workflow-syntax.md).
Local work checked syntax and returned evidence; installed-package execution was
performed by the hosted workflow, not by the local working container.
