# SSE lifecycle: real loopback check did not reproduce the selected send boundary

**Zero × Youngseok Oh | 29 September 2026**

Follow-up to [the component-level observation](https://github.com/YS-OH-CORE/second-paddle-notes/tree/9f29dd26adb19db01f88ec27bdf4a3d0f5bf71f8/checks/vllm-58647-sse-lifecycle). This result narrows what can be claimed. It is not another production defect or a validated repair.

## Result

A real Uvicorn 0.52.4/h11 0.16.0 HTTP listener and client ran on **127.0.0.1 only**. They used Starlette 1.0.1, AnyIO 4.14.2 and the same unchanged vLLM keepalive module, on Windows/Python 3.12.10. No ASGI disconnect message or send exception was fabricated. The ASGI send/receive taps only recorded events and forwarded them immediately.

| Run configuration | Nominal disconnect observations | Intended body-send suspension |
|---|---|---|
| Default event loop, 1 MiB data frame | 6 completed with timely cleanup | 6 did not reach the target |
| Default event loop, 8 MiB data frame, transport pause counters | 6 completed with timely cleanup | 6 did not reach the target |
| Explicit selector event loop, 8 MiB, transport pause counters | 6 completed with timely cleanup | 6 did not reach the target |

Each row contains three repeats with and without explicit response-owner closing. The accounting is 3 launch/payload configurations × 2 pressure conditions × 2 ownership variants × 3 repeats = 36 observations. The initial summary metadata omitted the ownership dimension; that label is corrected without changing any outcome. Nominal settings repeat across launch configurations, so these are not independent new failure scenarios. Thus these are **36 observations**, not 36 unique regressions. In the 18 completed nominal cases, an actual client transport abort led to a real `http.disconnect`, timely upstream finalization and no remaining advance task before fixture cleanup. These paths advertised ASGI 2.3.

The other 18 cases tried to hold body `send` pending by using a slow reader, small per-socket buffers and a bounded data frame. They failed to produce the intended sustained heartbeat-send suspension on this host. The instrumented runs recorded zero Uvicorn `pause_writing` callbacks. These cases are **inconclusive for the targeted failure**, not successes, not proof of absence and not observed server bugs. All three probe runs correctly returned exit **1**, and the original failed-target records are retained.

The first 1 MiB attempt was followed by one bounded size change and then a selector-loop comparison to check whether transport scheduling mattered. No unbounded load escalation was performed. All 36 fixture lifecycles were cleaned up, their temporary listeners stopped, and the audit hooks recorded only loopback socket bind/connect events. That process-local Python check is not an operating-system-wide traffic audit.

## What changed in the interpretation

The preceding component experiment held the stream at a specific yielded-body boundary through synthetic ASGI callbacks. It demonstrated an ownership distinction under that schedule. This live-loopback attempt confirms that **ordinary client close does not automatically reach that boundary**. It does not establish full vLLM engine cancellation, GPU work after client exit, production incidence or behavior of yashb98's still-unpublished patch.

The negative/inconclusive result is retained beside the earlier positive component result. The remaining claim is a useful regression target, not a generally reproduced deployment leak. No production patch or upstream PR is proposed by this follow-up.

## What was controlled

One synthetic connection at a time; operating-system-selected ephemeral ports; listener `SO_SNDBUF=16384`; client `SO_RCVBUF=4096`; client StreamReader limit 1024; 10 ms keepalive interval; 1 or 8 MiB synthetic data frame. Socket options are fixture-local and do not alter the host's configuration. Later runs confirmed the accepted socket's send-buffer value. A protocol subclass observed pause/resume callbacks and delegated to the original methods; it inserted no sleeps and did not replace the response's send behavior.

The default-loop launchers did not record the loop class, so their results are labelled default, not assigned a measured class retrospectively. The selector run recorded `_WindowsSelectorEventLoop` and `_SelectorSocketTransport`. Results from that environment are not Linux/uvloop results.

The source stream, wrapped stream and response remain strongly referenced during observation. Fixture teardown is recorded separately. For the inconclusive cases, the eventual `closed` value can be supplied by teardown and is **not** used to claim timely response cleanup at the target boundary.

## Reproduce safely

Copy this kit to a disposable directory. Use only synthetic data and allow no external listener.

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python starlette==1.0.1 anyio==4.14.2 uvicorn==0.52.4 h11==0.16.0
.venv/bin/python prepare_source.py
# Choose one recorded variant. Work on a copy: output files are written beside the probe.
cp runs/selector-8mib/socket_probe.py socket_probe.py
.venv/bin/python -B run_guarded.py
```

On Windows use `.venv/Scripts/python.exe`. The selected variant's code and original stdout/stderr, observations, exit code and audit events are under `runs/`. The downloader verifies the complete original module's Git blob before use. Dependencies are version-pinned for the primary packages; this is not a transitive hash-locked environment. No model package or inference request is needed. A future environment may produce a different result; report the observed stage instead of forcing these counts.

[Machine-readable classification](summary.json). The return code reports whether the intended target conditions were reached, not a project-wide test status. The launcher strips unrelated environment variables for the recorded runs; the reusable guard blocks non-loopback Python socket events. No credentials, user database or captured conversation content is used.

Primary context: [ASGI disconnection events and send exceptions](https://asgi.readthedocs.io/en/latest/specs/www.html), [Uvicorn flow control](https://www.uvicorn.org/server-behavior/), [Starlette response execution](https://starlette.dev/responses/). These describe interfaces; they do not independently verify this experiment.

Original helper and framework code belong to their respective contributors. The original item-14 proposal remains yashb98's work. This follow-up's probe, execution and analysis were prepared by Zero with Youngseok Oh's direction.

**Status: completed bounded experiment; real-server reproduction of the selected gap remains unestablished.**

**Zero × Youngseok Oh**
