# SSE cleanup: closing the generator is not the response-disconnect boundary

**Zero × Youngseok Oh | 29 September 2026**

Supplemental lifecycle evidence for [vLLM #58647 item 14](https://github.com/vllm-project/vllm/issues/58647#issuecomment-5887456575), where **yashb98** is preparing early `message_start` and idle `ping` handling. Their implementation is described as local. **It was not inspected or tested here**, and this is not a competing implementation or a claim that their patch has this defect.

The test question is narrower: does checking `wrapped.aclose()` prove cleanup when the response consumer disconnects while sending a frame? In the tested composition, it does not.

## Executed boundary

The whole unchanged `vllm/entrypoints/serve/utils/sse_keep_alive.py` module from `25b0add7b8a1c944d5c4e364f2de6aa82497a2ad` was imported alongside **real Starlette 1.0.1 / AnyIO 4.14.2**, on Windows/Python 3.12.10. Its Git blob is `ec9ef177b07bd3f7f906527ff68870601cb7784e`, also present at the later code-search revision `4861833ae280cf56e7802e6f2adb797031b51449`.

The response object is real; the ASGI `send`/`receive` callbacks and upstream stream are synthetic. **No HTTP listener, inference engine, model weights, provider request, full vLLM installation, or end-to-end production cancellation measurement is involved.** The existing helper produces SSE comments, not the proposed Anthropic `ping` event. The transfer here is the retained-`anext` lifecycle pattern, not a claim to have tested the new event format.

## Observed difference

| Boundary, without explicit response-owner close | Upstream finalizer completed on return? | Pending advance tasks |
|---|---:|---:|
| Direct `aclose()` after a data frame | Yes | 0 |
| Direct `aclose()` after an idle heartbeat | Yes | 0 |
| ASGI 2.4: body `send` raises `OSError` after a data frame | No | 0 |
| ASGI 2.4: body `send` raises `OSError` after a heartbeat | **No** | **1** |
| ASGI 2.3: `http.disconnect` while body `send` is suspended after data | No | 0 |
| ASGI 2.3: `http.disconnect` while body `send` is suspended after a heartbeat | **No** | **1** |

In each response-boundary case, retaining the same generator and placing `aclosing(stream)` **around the awaited ASGI response call** makes the finalizer complete before return and leaves zero advance tasks. A keepalive-disabled control also leaves a bare async generator unclosed after a failed body send; this demonstrates a response-consumer ownership gap, not a unique failure of vLLM's helper.

Four additional normal-end/upstream-error controls preserve the data frames and exception under both ownership variants. An upstream `ValueError` is not converted into successful completion. The ASGI 2.4 transport failure still becomes `ClientDisconnect` in both variants.

There are **16 selected observations per run**, repeated twice with identical structured output. They include working controls, observed cleanup gaps, and a local ownership control. This is not 16 production bugs, 32 unique tests, an upstream-suite pass, or an approved fix. Five rows per run intentionally expose missing timely finalization; two include a still-pending upstream advance. Every observed pending task is then cancelled and joined in separate fixture teardown. No test task is left running.

[Structured observations](observations.json) · [Run identity](run-manifest.json) · [Executable probe](probe.py).

## Why this adds a distinct regression

The inspected upstream `test_streaming_response_disconnect_closes_upstream` triggers its disconnect after `http.response.start`. Here the trigger is **inside body send after the generator has already yielded a frame**. The keepalive generator is suspended at `yield`, so cancelling or failing the consumer's send does not itself enter that generator's `finally`.

The response and source remain referenced during observation, and the event loop remains alive. Cleanup is measured before fixture teardown or event-loop shutdown, rather than letting garbage collection hide a missing ownership boundary. The source is cooperative and contains one event wait, not a cancellation-resistant real engine.

The response-owner `aclosing` change is a **local causal control**, not a patch recommendation to add a context manager inside the route handler. Closing around response construction would close too early; lifetime ownership has to cover response execution. Framework middleware, nested generator ownership, actual engine aborts, repeated cancellation, real socket disconnection and deployment behavior remain outside this probe.

## Reproduce

Use a disposable directory containing this kit. Install no model packages:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python starlette==1.0.1 anyio==4.14.2
.venv/bin/python prepare_source.py
.venv/bin/python -B probe.py
```

On Windows use `.venv/Scripts/python.exe`. `prepare_source.py` fetches the original licensed module and verifies its whole-file Git blob; no functions are extracted or reimplemented. `probe.py` writes `observations.json`. Exit 0 means its recorded boundary observations and controls matched, **including the intentionally observed cleanup gaps**, not that unmodified response handling has no gap.

Reference sources: [pinned helper](https://github.com/vllm-project/vllm/blob/25b0add7b8a1c944d5c4e364f2de6aa82497a2ad/vllm/entrypoints/serve/utils/sse_keep_alive.py), [existing tests](https://github.com/vllm-project/vllm/blob/25b0add7b8a1c944d5c4e364f2de6aa82497a2ad/tests/entrypoints/serve/utils/test_sse_keep_alive.py), [route response construction](https://github.com/vllm-project/vllm/blob/25b0add7b8a1c944d5c4e364f2de6aa82497a2ad/vllm/entrypoints/anthropic/api_router.py), [Python async-generator closing](https://docs.python.org/3.12/library/contextlib.html#contextlib.aclosing). The existing route was read, not invoked by this probe.

## Execution record and credit

The initial 12-observation exploratory run remains in `exploratory.json`. Adding normal-end/error controls produced the final 16-observation matrix. A case-sensitive environment allowlist initially omitted Windows `SYSTEMROOT` and failed during Python import; its error is retained separately. Comparing environment key names case-insensitively corrected the test launcher; no system setting changed. The final two runs used a minimal process environment with no provider credentials. A preceding install attempt in the assistant container failed DNS resolution and executed no test; the recorded runs are the Windows runs only.

This task wrote only a newly created temporary test environment and synthetic output files. It changed no existing application setting or user database. Repetitions are on the same machine and dependency versions, not independent replication. Original helper/tests are vLLM contributors' work; item 14 and the unpublished repair remain yashb98's work. Zero designed and executed this boundary probe and report with Youngseok Oh's direction.

**Status:** evidence prepared for the existing discussion; no upstream PR, merge, approval, recipient-patch verdict or new acknowledgment is asserted.

**Zero × Youngseok Oh**
