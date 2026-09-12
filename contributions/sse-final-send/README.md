# A response is not finished until its final send completes

A bounded investigation of `EventSourceResponse` in [sse-starlette](https://github.com/sysid/sse-starlette), prompted by the final-send hypothesis in [MCP Python SDK issue3494](https://github.com/modelcontextprotocol/python-sdk/issues/3494). The original issue is jonpspri's report. Skulitom's separate restart/global-state diagnosis is not reproduced or claimed as ours.

## Observed, not just inferred

[Executed run34703822255](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34703822255) compares exact upstream commit `6754ef387da97cf6cfbcd1bd5c216b533937b304` with one change in a disposable copy: move `self.active = False` after the awaited final body send, under the existing send lock. No other production line changes.

| Same case on each version | Baseline | Candidate |
|---|---|---|
| Ordinary completion | Final body sent | Final body sent |
| Final send waits while one normal request event is delivered | Final send cancelled; response returns incomplete | Final body sent |
| An actual `http.disconnect` event is supplied during a pending final send | Send cancelled; close callback once | Send cancelled; close callback once |
| Uvicorn/h11 and HTTPX over localhost with controlled receive/final-send scheduling | `RemoteProtocolError`; server logs incomplete response | HTTP200, exact Korean SSE body, complete response |

The disconnect case supplies a protocol event to the real response implementation; it does not close a physical client socket. The loopback case uses real sockets, an ordinary server receive event and one fresh server. Its middleware deliberately releases the first receive event when final send begins and delays final send by20ms. This is an adversarial but legal scheduling case, not a measured incident rate or a reproduction of the report's uninstrumented CPU-load environment. Both HTTP cases observed `AppStatus.should_exit=False` before test-server shutdown, separating this mechanism from stale shutdown state.

The selected original files `tests/test_sse.py`, `tests/test_issue167.py` and `tests/test_event.py` were run unchanged on both versions: **59 passed on each, no failure/error/skip**. Those59 alone did not expose this scheduling case. The eight new probe executions use distinct Python processes; they are four cases compared twice, not eight independent real-world incidents.

## Why the change helps

The disconnect listener loops while `self.active`. If an ordinary request event finishes arriving after the stream has already set that flag false but before its final send finishes, the listener returns. Its `cancel_on_finish` wrapper then cancels the shared task group, including the pending final send. The ASGI callable can return normally while the HTTP body remains unfinished. The candidate delays the completion state until the awaited send returns. It does not shield sends, ignore disconnects, suppress errors, or alter shutdown handling.

[ASGI response-body semantics](https://asgi.readthedocs.io/en/stable/specs/www.html#response-body-send-event) require `more_body=False` to complete the response. The sample SSE payload can already have been sent while this final completion message is lost. Do not describe this as necessarily losing the last application payload.

## Reproduce

Use a disposable virtual environment and a clean checkout of the exact upstream commit. Install the listed versions or inspect the captured dependency list. The same environment is used for both source variants.

```sh
python -m pip install 'sse-starlette==3.4.11' 'anyio==4.15.1' 'starlette==1.6.0' 'uvicorn==0.52.4' 'httpx==0.28.1' 'httpx2==2.12.0' 'asgi-lifespan==2.1.0' 'pytest==9.1.1' 'pytest-asyncio==1.4.0'
python verify.py --base /path/to/clean-upstream --candidate /path/to/new-candidate --out /path/to/new-evidence
```

`verify.py` refuses an unexpected revision, a dirty baseline or existing output/candidate directory. It copies the public checkout, changes exactly one ordering, runs each probe in a fresh process, and preserves raw logs, observations, the actual patch and original-test XML. `probe.py` can also run one case directly with `PYTHONPATH` set to the desired checkout. Its output is an observation, not a pass/fail claim by itself.

The candidate is [final-send.patch](final-send.patch). Apply only after reviewing the target version. The verifier checks imported module paths and file identities; it never patches a user installation. A successful verifier means the specified baseline defect and selected candidate controls were observed. It is not a universal certification or an upstream release.

## Evidence identities

- Baseline source blob: `c096b665e9857f9df86a01c81be3093c786cc353`.
- Candidate source blob: `f483035db645995f76168e66378ec1f42864beb7`.
- Run artifact10301616324:14,673bytes, SHA256 `d6a1108f4287b546bd57c0adbcd7505c45763ee2749ad0acb95d40f58f17d50d`.
- Probe blob: `a56911dbe268faebbcf425840c8bf289e3314fab`; verifier blob: `771e6a6638fcbd5863b928c3e626d8b3df5bb127`.

The returned artifact was downloaded, CRC/digest checked, and all eight observation files, both59-case XML reports, source identities and actual client/server errors were inspected. Raw artifact retention is14days; the code and precise experiment remain here and the original ZIP is also provided in the conversation archive. Earlier local public-source download failed at DNS; runtime evidence is the hosted execution, not a local-runtime claim.

All test traffic is synthetic and confined to localhost. No MCP initialize request, external model, real-user session, billing change or recurring job. Prepared by Youngseok Oh with Zero (ChatGPT). The candidate remains for upstream review; the findings here do not establish the cause of every symptom in MCP issue3494.
