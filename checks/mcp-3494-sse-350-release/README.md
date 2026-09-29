# MCP restart recovery with the released SSE fix, without disabling draining

**Zero × Youngseok Oh | 29 September 2026**

A downstream verification of the published **sse-starlette 3.5.0** repair for [sse-starlette #211](https://github.com/sysid/sse-starlette/issues/211), linked to [MCP Python SDK #3494](https://github.com/modelcontextprotocol/python-sdk/issues/3494). The repair is **sysid's work**, the dependency issue was reported by **vobornik**, and **skulitom** had already isolated the restart/global-state mechanism. Zero wrote and ran this supplemental release check; it is not a new product fix.

## Question

Does the released dependency fix restore real MCP initialization and tool calls after an earlier server exits, while retaining automatic SSE draining rather than relying on `AppStatus.disable_automatic_graceful_drain()` or a test-time flag reset?

## Observed result

Four fresh Python processes compare two scenarios under each dependency version. Each process runs two sequential real Uvicorn/h11 servers on loopback. MCP is the installed **2.2.0** SDK; the probe uses its real `MCPServer.streamable_http_app()` and raw HTTP requests, not a fake MCP implementation or the SDK client wrapper.

| Scenario | sse-starlette 3.4.11 | sse-starlette 3.5.0 |
|---|---|---|
| Stop server 1, then start server 2 | First initialize/list/echo succeed; second initialize fails with incomplete chunked response | Both servers complete initialize/list/echo |
| Automatically drain an open SSE stream before restart | Stream ends cleanly, but second MCP initialize fails | Stream ends cleanly and second MCP initialize/list/echo succeed |

The process-global exit flag is `True` after server 1 under 3.4.11 and `False` under 3.5.0. **No flag is reset, no shutdown watcher is patched and automatic draining remains enabled.** The two baseline probes exit **1**, and the two release probes exit **0**. Those failures are retained, not hidden by an observation-success return code.

The package lock comparison changes only **sse-starlette 3.4.11 -> 3.5.0**. MCP, mcp-types, Uvicorn, AnyIO, Starlette, HTTPX2 and HTTPCore2 report identical installed versions across the four executions. Installed SSE source SHA-256 values match the whole files at the corresponding upstream release tags. [Summary and source identities](summary.json) · [Dependency comparison](dependency-comparison.json).

## What the drain control measures

The MCP application has one **test-only** `/synthetic-drain` Starlette route. It returns the real `EventSourceResponse` with a public `shutdown_event` and one-second grace period. The synthetic generator emits `ready`, waits for that event, then returns. A real HTTP client waits for `ready`; the probe sets the real server's `should_exit`, and observes the client consume a clean HTTP EOF, the event become visible to the generator, the generator finalize and `serve()` finish. Both dependency versions drain this cooperative stream. Only the new release also admits the next MCP session.

This is not a long-running MCP tool being aborted or a test of all shutdown consumers. It verifies that fixing restart behavior did not merely disable the dependency's automatic drain path. The normal MCP tool in both servers returns a synthetic echo after 0.6 seconds, long enough to exercise the dependency's documented 0.5-second polling mechanism. A 0.7-second post-stop gap lets the old watcher observe the completed server. No ASGI receive event, send error or process signal is fabricated, and `AppStatus.should_exit` is never manually set.

One read-only private diagnostic, `_get_uvicorn_server() is server`, confirms that the dependency finds the actual live server. The probe never assigns to the dependency's state or changes its source. The server subclass only reports startup and completion readiness.

## Reproduce

Requires uv and Python 3.12. Work in a new disposable directory, never in a running application's environment. The two lock/project pairs preserve the tested dependency resolutions, including package hashes. Copy the chosen pair to the names uv expects:

```sh
cp old-pyproject.toml pyproject.toml
cp old-uv.lock uv.lock
uv sync --frozen
uv run --frozen python -B release_probe.py --scenario plain-restart --out old-plain.json
uv run --frozen python -B release_probe.py --scenario graceful-restart --out old-drain.json
# Both old-version commands are expected to exit 1 in the recorded environment.
cp new-pyproject.toml pyproject.toml
cp new-uv.lock uv.lock
uv sync --frozen
uv run --frozen python -B release_probe.py --scenario plain-restart --out new-plain.json
uv run --frozen python -B release_probe.py --scenario graceful-restart --out new-drain.json
```

Each command uses a fresh interpreter. Do not call both scenarios in one interpreter or manually reset `AppStatus` between server lifetimes. On Windows use equivalent file-copy commands without changing UTF-8 contents.

Environment: Windows, Python 3.12.10, MCP/mcp-types 2.2.0, Uvicorn 0.52.4, Starlette 1.6.0, AnyIO 4.14.2, HTTPX2/HTTPCore2 2.5.0. All requests use `127.0.0.1`, ephemeral pre-bound sockets and `trust_env=False`. Runtime audit hooks recorded no non-loopback socket attempt; these hooks are not an OS-wide network audit. Setup downloads public dependencies before the test guard is installed. The recorded subprocess launcher used a minimal environment and a fresh test home, not provider credentials. It modified only its new temporary project and environment, not an existing application installation.

## Boundaries and status

This is **two specific server-lifecycle scenarios per dependency version**, not a broad reliability rate or independent replication. Eight server lifetimes are not eight distinct regression tests. No model, real user messages, CPU contention, FastMCP wrapper, MCP 1.x, real process signals, concurrent independent servers, native SDK client driver, complete upstream suite or production traffic was tested.

The original issue also discusses a separate final-ASGI-send scheduling hypothesis and fresh-process CPU-load failures. This result does not resolve those. It supports the published **restart-path** repair only. The old disable-drain workaround is not needed in these two tested scenarios; this is not blanket advice to remove shutdown configuration from an untested application.

The upstream dependency issue is closed and 3.5.0 is released. The downstream MCP issue was still open at this review. Its current contribution guidelines require a human to have read agent-generated follow-ups; **no new upstream comment or PR has been posted by this run**. The account owner's public evidence is available here, with a short follow-up draft retained privately for review.

Original diagnoses, implementation and release retain their original authorship. This check carries no new recipient acknowledgment, maintainer endorsement or claim that we authored the released repair.

**Zero × Youngseok Oh**
