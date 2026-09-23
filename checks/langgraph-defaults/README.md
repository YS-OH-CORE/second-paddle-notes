# LangGraph #5225: explicit defaults for a new run

23 September 2026 · Youngseok Oh × Zero (ChatGPT)

An application-level workaround for people waiting on [LangGraph issue #5225](https://github.com/langchain-ai/langgraph/issues/5225), not another proposed framework patch or a decision on the default/reducer semantics under discussion there.

## What was actually executed

The [public execution](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35810387194) ran the [complete check script](https://github.com/YS-OH-CORE/second-paddle-notes/blob/02f82e3d3d26178b48be2c8ab6e571910ecd5abf/checks/langgraph-defaults/check_defaults.py) against LangGraph source `1211af45b18cab9c0a7efe366ba12f51ad2a9996`. The job was `107020429948`, with workflow commit `64dd89c01adb86f54702cbccdad6e2fb6d6010c8`.

Reported environment: Python 3.12.3; LangGraph 1.2.12; checkpoint 4.2.0; langchain-core 1.6.4; Pydantic 2.13.5. The four local LangGraph packages were built from the pinned checkout. Other dependencies were resolved at execution time and recorded with `pip freeze`; this was not a frozen-lockfile run.

The real compiled graph uses a Pydantic state with an additive list default `["default"]` and an additive integer default `10`. Its node appends `["node"]` and adds `5`.

| Input or scenario | Observed list | Observed counter |
|---|---|---:|
| New run: `{}` | `["node"]` | 5 |
| New run: `OverallState()` | `["default", "node"]` | 15 |
| New run: full `OverallState().model_dump()` | `["default", "node"]` | 15 |
| New run: `model_dump(exclude_unset=True)` | `["node"]` | 5 |
| New run: explicit `["provided"]` and `100` | `["provided", "node"]` | 105 |
| New run: explicit `[]` and `0` | `["node"]` | 5 |
| Continue checkpoint with only `["next"]` and `2` | `["default", "node", "next", "node"]` | 22 |
| Negative control: seed the same checkpoint twice | `["default", "node", "default", "node"]` | 30 |

Passing the model instance directly worked in this revision too; converting it to a dict is not the sole workaround. The script also checked input preservation, a second fresh run, a separate checkpoint thread, checkpoint readback, and an async fresh run. These are observations within one development execution, not independent studies or a general compatibility guarantee.

## Apply only at initial creation

Using `OverallState` and `build` from the linked script:

```python
def initial_input(overrides=None):
    return OverallState.model_validate(
        {} if overrides is None else overrides
    ).model_dump()

# Initial call for a NEW checkpoint thread.
graph = build(InMemorySaver())
config = {"configurable": {"thread_id": "synthetic-continuation"}}
graph.invoke(initial_input(), config)

# Later calls on the SAME thread contain only new updates.
graph.invoke({"variable": ["next"], "counter": 2}, config)
```

Do not expand all defaults on every continuation: those values become another reducer update and are added again. Do not use `exclude_unset=True` to construct the initial seed when the point is to include defaults. The caller must know whether it is starting a new thread; this example is not an atomic concurrent initialization protocol.

## Scope and attribution

The original report and earlier root-cause analyses belong to their respective issue contributors. This example deliberately uses pure `operator.add`, not the reporter's in-place `extend` reducer, and does not patch library source. It illustrates explicit caller initialization for flat list/int fields. It does not settle how LangGraph should automatically apply schema defaults, or claim coverage for custom reducers, custom serializers, aliases, separate input schemas, concurrent initial creation, durable database backends, or process restarts.

The runtime used actual StateGraph and InMemorySaver, with synthetic data and no model. Tracing was disabled; socket connection attempts were blocked during the graph checks. Setup downloaded public dependencies. The installed channel source was byte-compared with the pinned checkout, and the checkout was clean afterward. This is author-run testing, not a maintainer or independent validation.

Example, execution and analysis prepared by Zero (ChatGPT) for Youngseok Oh / @YS-OH-CORE. Public availability or a successful run does not establish upstream adoption or user uptake.
