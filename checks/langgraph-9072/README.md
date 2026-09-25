# LangGraph #9072: test the parent boundary, not only the combiner

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

**Returning two intact parent-directed Commands is not sufficient in the tested compiled graph: the ToolNode boundary contains both, but the parent applies only the first update and runs only the first worker.** Reversing the sibling order reverses which survives.

This is supplemental evidence for [elizandropacheco's report](https://github.com/langchain-ai/langgraph/issues/9072) and the [existing reducer-preservation discussion](https://github.com/langchain-ai/langgraph/issues/9072#issuecomment-5813288929). It does not claim their original diagnosis or propose a competing PR. The experimental variants below are our interpretations for testing, not any participant's unpublished implementation.

## Actual execution

Pinned upstream: `7daa3ab49d678a5da75edb08baa87db4a2be52c3`. All four LangGraph runtime libraries (checkpoint, sdk-py, prebuilt and langgraph) were installed from the same complete source checkout. The original ToolNode Git blob was checked against `95e161b9078e3123afa1854247a5dfd132410a53`, and each fresh subprocess verified its actual ToolNode import path and source hash.

The probe uses real decorated tools, ToolNode and compiled child/parent StateGraphs, not extracted methods or mock graph components. Tools return predetermined values; no model or provider call occurs. Python socket connections and DNS resolution are disabled during the probe, and tracing is off. Python was 3.12.3; langchain-core resolved to 1.6.5. The runner records the complete resolved environment.

Five variants each exercised four scenarios through both `invoke` and `ainvoke`: one Send-based handoff, two sibling handoffs, reversed siblings, and one string-goto control. **40 graph invocations completed**, including intentional preservation failures. This is not a full upstream suite or a model-accuracy benchmark.

[Completed CPU execution](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36117327987) | [all 40 compact observations](OBSERVATIONS.json) | [readback audit](AUDIT.json)

## Reducer-sensitive fixture

The parent has `add_messages`, a numeric-addition reducer and a custom reducer that keeps the longest incoming list rather than concatenating lists. Alpha contributes `total=2`, `best=[a]` and one ToolMessage; beta contributes `total=3`, `best=[b,c]` and another ToolMessage. Each Send targets a worker that records which job it received.

With alpha then beta, the required parent result is total **5**, best **[b,c]**, both ToolMessage IDs and both workers. Observed results were identical for synchronous and asynchronous calls:

| Experimental implementation | Parent total | Parent best | ToolMessage IDs retained | Workers reached |
|---|---:|---|---|---|
| Unchanged upstream | 0 | [] | None | alpha, beta |
| Preserve only first command; merge later Sends | 2 | [a] | alpha only | alpha, beta |
| Return each intact PARENT command separately | 2 | [a] | alpha only | alpha only |
| Merge dictionaries; concatenate list values | 3 | [a,b,c] | alpha, beta | alpha, beta |
| One PARENT command with ordered key/value writes and combined Sends | **5** | **[b,c]** | **alpha, beta** | **alpha, beta** |

The separate-commands variant exposes two intact Commands at `_combine_tool_outputs`, so checking only that return value would miss the downstream loss. In reversed order, only beta's update and worker survive. The first-only variant also changes survivor with order, although both workers still run.

The structural-merge negative control keeps both messages but changes the application's reducer semantics: it overwrites a number and concatenates lists before the graph gets to apply its reducers. With reversed siblings it produces total 2 and best [b,c,a]. This concretely exercises the concern already raised in the discussion.

The ordered-writes experiment retains duplicate state keys using the existing `Command._update_as_tuples()` representation and combines the Sends into one parent command. The normal parent reducers then receive both values. It preserved the required result in all eight selected scenarios, including the reversed-order and string-route controls. The other variants preserved respectively 2, 4, 4 and 4 of their eight selected scenarios. These counts describe this fixture only.

## Useful acceptance criterion, not a production fix

Check the final compiled parent's reducer outputs **and** the reached workers, alongside the combiner's intermediate output. Preserving all fields in an intermediate list is not itself proof that they reach the parent graph.

All resume values in this fixture are None. Resume conflicts, mixed parent destinations, root-state updates, non-reduced conflicting keys, arbitrary Command.update types, interrupts/checkpoint replay, LangChain create_agent wrappers, model behavior and the full upstream suite remain untested. The ordered-writes variant is an executable design experiment, not a complete or approved patch. No claim is made about the reporter's production loop or token expenditure.

## Reproduction and provenance

The [probe](probe.py), [runner](run.py) and [protocol](PROTOCOL.md) were committed before execution at `f8d4797189e44a8342b2e03feaefbdd85e19f308`. From a directory containing the two scripts, use a new disposable output path:

```bash
python run.py --root /absolute/new-disposable-directory --probe ./probe.py
```

The setup downloads the pinned source and dependencies, creates a venv, and edits only its disposable ToolNode copy. Each variant starts a fresh process; the original is restored at the end. No existing project checkout or user profile is edited. The runner exits successfully when the planned observations complete and the unchanged string-route controls hold, not when every experimental variant preserves state.

Run: `36117327987`; workflow commit: `f35ebe25ad5889b68ffb072fdb8567b8b44502da`; artifact: `10855581791` (140,411 bytes). [Full raw artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36117327987/artifacts/10855581791) includes every variant's source, diff, log and full report, plus environment and original source. Actions retention is 30 days; compact observations and the audit are committed here.

Artifact SHA-256: `0e44ea9e500a94747a1825e2f4b2ff7379abb7b6cd5a1ae215ee70a553ca7417`.
Probe SHA-256: `86b4a500e79568eae246894d70b6b59893e7a714477f800119627b99319b68c1`.
Runner SHA-256: `bbf76738c97274cba5b2ad1c9502e5ea15cb2e4f68ae3bcbb7383d2fac61722a`.

Readback verified the downloaded archive checksum, script/source identities, all 40 log rows against the reports and the matching synchronous/asynchronous outcomes. This was reanalysis of the actual run, not a second independent execution.

Credit: original report by elizandropacheco; reducer-preservation discussion by 84dnnvbdvp-debug and breken-ai; upstream LangGraph implementation by its contributors. Supplemental fixture, execution and analysis by Zero, an AI collaboration partner working with Youngseok Oh. No maintainer endorsement, adoption or merge is implied.
