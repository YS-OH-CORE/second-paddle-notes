# Does the final-send candidate repair real MCP initialization?

**Observed answer: the prior candidate does not repair the tested restart failure.** With request receives untouched, first initialization succeeds on both versions. After the real watcher carries the first server's shutdown state forward, second initialization fails on both. Resetting only that state as a diagnostic control restores initialization on both. Do not use the earlier plain-SSE interleaving result as proof of an MCP restart fix.

## Actual execution

[Run34705469328](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34705469328), `mcp_boundary` job, used real `mcp==2.2.0` over loopback Uvicorn/h11 HTTP. Six fresh processes made ten initialization requests. The baseline and the existing unchanged `final-send.patch` candidate produced identical outcomes:

| Scenario | Baseline | Prior candidate |
|---|---|---|
| First server, final send delayed20ms | Complete initialize | Complete initialize |
| Second server after watcher-confirmed shutdown | RemoteProtocolError | RemoteProtocolError |
| Same restart with diagnostic flag reset | Complete initialize | Complete initialize |

In all ten requests, a single169-byte `http.request` was consumed before response start. Successful requests completed the final send before the later disconnect event. Both restart failures occurred with `AppStatus.should_exit=True`, after response start but **before any final-send attempt**. Thus moving the final-send completion flag cannot repair this particular failure path. The existing watcher captured server1; after a diagnostic reset it could capture server2.

The first-server control does not establish that all other MCP schedules are immune. This is a small mechanism comparison, not an estimate of CPU-load failure frequency. The reset is a diagnostic intervention, not a supported production workaround.

## Why this differs from the earlier probe

The earlier wire probe deliberately withheld the first ordinary receive until final send began in an application that did not need a POST body. Here a real MCP server must consume the initialize request to form its reply. This probe only observes and immediately forwards actual receive events; it does not hold, duplicate, synthesize or reorder them. The final send is still delayed20ms to provide a cancellation opportunity. We retain both experiments and their different conditions rather than relabel the earlier one as a real MCP test.

## Attribution

The original report is [jonpspri's MCP issue3494](https://github.com/modelcontextprotocol/python-sdk/issues/3494). The restart/global-state mechanism and reset diagnostic are from [skulitom's investigation](https://github.com/modelcontextprotocol/python-sdk/issues/3494#issuecomment-5641191441). Our addition crosses that mechanism with our separate final-send candidate on Linux and actual MCP requests; it does not claim discovery of the restart mechanism.

## Reproduce and inspect

Run `verify_mcp.py --base <clean pinned sse checkout> --candidate <new disposable path> --out <new output path>` in an isolated environment using the packages in the workflow. Actual installed versions: MCP2.2.0, SSE-Starlette3.4.11, Uvicorn0.52.4, HTTPX0.28.1, AnyIO4.15.1, Starlette1.6.0, h110.16.0. The SSE source checkout is pinned at `6754ef387da97cf6cfbcd1bd5c216b533937b304`. Baseline/candidate module blobs are `c096b665e9857f9df86a01c81be3093c786cc353` / `f483035db645995f76168e66378ec1f42864beb7`; the imported MCP server blob is `fbd2c26dd8291e779df8a33fc2d18277c5f1b380`.

Returned artifact10301384089 is11784bytes, SHA256 `5de7d3ced0ba7f9bad164d78fc577a62539a0cdb8c9a7ba537ec08bf5c4e7d22`. It was downloaded and opened: archive CRC, six individual observations against the summary, ten request/response sequences, six process IDs, exact initialize protocol replies, both incomplete-response server logs, and source identities were checked. The artifact includes the actual dependency list and unedited process logs. Artifact retention is14days; the scripts and this dated conclusion remain in Git.

`comparison_complete` means evidence collection finished. It explicitly reports `all_initializations_succeeded=false`, `candidate_fixed_restart=false`, and `candidate_and_baseline_same_outcomes=true`. Eight successful requests and two failed requests are preserved as such. The old comparison job also ran successfully, but its pre-existing checks are not new evidence of an MCP repair.

No MCP production code is patched. The candidate is the exact previously tested SSE ordering patch, not a new repair. All traffic is synthetic loopback HTTP; no model/provider calls, private history, external server, recurring task, billing or production deployment. Prepared by Youngseok Oh with Zero (ChatGPT).
