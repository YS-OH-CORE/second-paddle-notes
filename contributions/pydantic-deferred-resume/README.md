# External deferred results after persisted-history resumption

A supplemental reproduction for [pydantic/pydantic-ai#8181](https://github.com/pydantic/pydantic-ai/issues/8181), originally reported by RemyOstyn. ExileK1G has already volunteered to implement an agreed approach. This contribution supplies a reproduction and an explicit-result control, not a competing feature implementation or an upstream PR.

## Question

An external tool answer is present in a Vercel `output-available` part, and `load_messages()` can materialize it. When a server resumes its own persisted history and clears the request messages to avoid replaying them, does `deferred_tool_results` preserve the answer? The original report demonstrates the missing property value. This example extends it through a real stop, file persistence, a new Python process, and `VercelAIAdapter.run_stream_native`.

## Reproduce

Use a disposable Python environment, not a working installation:

```sh
python -m venv /tmp/deferred-repro-env
/tmp/deferred-repro-env/bin/python -m pip install 'pydantic-ai-slim[ui]==2.43.0'
/tmp/deferred-repro-env/bin/python reproduce.py --out /tmp/deferred-repro-new-output
```

The output directory must not exist. Three separate processes perform:

1. Run an actual `Agent` with a deterministic `FunctionModel`, invoke a tool that raises `CallDeferred`, save its history and exit.
2. Reopen that history, read `adapter.deferred_tool_results` **before** clearing request messages, and attempt native-stream resumption with the extracted result.
3. Reopen the same unchanged history and provide the known pending call's actual synthetic frontend output via `DeferredToolResults(calls=...)` instead.

The script records tool-body invocations, events, return content, process IDs and history digests. It requires the explicit-result control to complete without invoking the deferred tool again, with exact Korean whitespace preserved. The version and imported production files are checked in the accompanying workflow. Production files are not patched.

## Interpretation

Successful reproduction is evidence for the reported gap, not a fixed library. A local function chooses the synthetic model response: no remote language model, provider request or AI-performance result is involved. The real agent loop, adapter, serialization and process restart do execute. No HTTP frontend server, actual browser or production user is used. Both resume branches use the same synthetic server history.

The control deliberately handles one already-known pending call. It is **not** a generic extractor that trusts arbitrary client results. A general API needs to distinguish still-pending external calls from old completed calls, reject unknown/replayed identifiers, and define error and mixed approval/call behavior. Reading cached adapter properties after emptying messages is a separate ordering issue; this reproduction reads the result property beforehand and avoids caching `messages` before clearing.

## Sources and contribution scope

- [Original report and current discussion](https://github.com/pydantic/pydantic-ai/issues/8181)
- [Official deferred-tool documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/)
- [Vercel adapter at v2.43.0](https://github.com/pydantic/pydantic-ai/blob/v2.43.0/pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py)
- [Upstream contribution process](https://github.com/pydantic/pydantic-ai/blob/main/CONTRIBUTING.md)

At this document's initial publication, hosted execution is pending. See the introducing PR for actual observations. No request for assignment or upstream review is implied by publishing an MRE here. Prepared by Youngseok Oh with Zero (ChatGPT); original discovery belongs to the reporter. No private messages or personal history are included.
