# Does the final-send candidate repair real MCP initialization?

This checks the existing `final-send.patch` against actual `mcp==2.2.0` initialization over Uvicorn/h11 HTTP, not a synthetic EventSourceResponse app. The three scenarios run in fresh processes for each source version: one server; two successive servers after observing the real shutdown watcher; and the same restart with an explicitly labeled diagnostic reset of the shutdown flag.

Only the final HTTP send is delayed by20ms. Request receives are forwarded immediately and unchanged. The probe does not fabricate an empty receive, hold a request until the final send, introduce CPU contention, or set a shutdown flag in the ordinary restart scenario. Capture of the real server pointer is observational. The reset scenario is a causal control, not a supported production workaround.

The original report is [jonpspri's MCP issue3494](https://github.com/modelcontextprotocol/python-sdk/issues/3494). The restart/global-state mechanism and reset diagnostic are from [skulitom's investigation](https://github.com/modelcontextprotocol/python-sdk/issues/3494#issuecomment-5641191441). This comparison asks whether our separate final-send candidate changes that behavior; it does not reassign their discovery.

Run `verify_mcp.py --base <clean pinned sse checkout> --candidate <new disposable path> --out <new output path>` in an isolated environment containing the pinned packages in the workflow. The source revision and old patch bytes are checked. A completed comparison may include failed requests and must not be presented as all initializations passing. No MCP production source is changed. Runtime evidence is pending at the initial addition; see the introducing PR for subsequently observed results.

Prepared by Youngseok Oh with Zero (ChatGPT). No private history, model request, external server, recurring task, or production deployment.
