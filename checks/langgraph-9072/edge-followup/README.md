# LangGraph #9072: mixed update representations break our earlier candidate

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

**Our previous ordered-writes experiment needs sequence normalization.** A dict update followed by a tuple of keyed writes raises `TypeError` in that exact candidate. The same happens in reverse order and in the tested tuple/dataclass, tuple/Pydantic and tuple/None combinations. Converting both sequences to lists before concatenation preserves duplicate keys and resolves the tested errors.

This follows [impartshadow's response](https://github.com/langchain-ai/langgraph/issues/9072#issuecomment-5831629639), which revised their earlier recommendation after our compiled-parent result. That is a discussion participant's response, not maintainer approval or independent replication. The original report remains elizandropacheco's; the reducer discussion includes 84dnnvbdvp-debug and breken-ai. This follow-up tests and corrects **our own experimental candidate**, not another participant's unpublished patch.

## Mechanism

At [the pinned Command implementation](https://github.com/langchain-ai/langgraph/blob/7daa3ab49d678a5da75edb08baa87db4a2be52c3/libs/langgraph/langgraph/types.py#L861-L875), `_update_as_tuples()` returns a `Sequence`, not necessarily a list. It returns incoming tuple pairs unchanged. Consequently:

```python
left = Command(update={"total": 2})
right = Command(update=(("total", 3),))
left._update_as_tuples() + right._update_as_tuples()  # list + tuple: TypeError
```

The tested correction to the merge line is:

```python
update=list(parent_command._update_as_tuples()) + list(output._update_as_tuples()),
```

It preserves both `total` entries rather than collapsing them into one dictionary. The parent graph's existing reducers still decide how to apply them. The rest of the earlier experimental patch is unchanged, including retaining the first Command and combining the Sends.

## What actually ran

Pinned upstream: `7daa3ab49d678a5da75edb08baa87db4a2be52c3`. Original ToolNode blob: `95e161b9078e3123afa1854247a5dfd132410a53`. The old candidate was byte-for-byte verified against the earlier artifact, SHA-256 `32ee5d28f4bff7b6af6694ba4ea6abb87dc1048ba5bbefd1a8314fa6efbe2dcd`.

Three variants each ran 24 graph invocations: unchanged upstream, our exact prior candidate, and our list-normalized candidate. Each includes the prior eight controls and 16 new representation/conflict cases. **72 graph invocations completed**, using real ToolNode, decorated tools and compiled child/parent graphs, with both `invoke` and `ainvoke`. The original and new probes deny Python socket connections and DNS and disable tracing. There were no model calls, service requests, real user memory, or mocked graph components.

Python 3.12.3, langchain-core 1.6.5 and Pydantic 2.13.5. All four LangGraph runtime libraries were installed from the same pinned source checkout. The complete resolved environment and source variants are preserved in the artifact.

[Completed run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36133731437) | [audit](AUDIT.json) | [compact observations](OBSERVATIONS.json)

## Observations

Each row below ran through both sync and async APIs with matching relevant outcomes. Parent totals, longest-batch reducer output, ToolMessage IDs and reached workers were compared with declared expectations.

| Condition | Exact earlier candidate | List-normalized candidate |
|---|---|---|
| Prior eight cases, including reversed order and string goto | Original expected results retained | Original expected results retained |
| Dict / tuple-keyed writes | TypeError | Both updates and workers retained |
| Tuple-keyed writes / dict | TypeError | Both updates and workers retained |
| Tuple-keyed writes / tuple-keyed writes | Both retained | Both retained |
| Dataclass / tuple-keyed writes | TypeError | Both retained |
| Tuple-keyed writes / Pydantic update model | TypeError | Both retained |
| None / tuple-keyed writes | TypeError | Only beta updates state; both workers run |
| Tuple-keyed writes / None | TypeError | Only alpha updates state; both workers run |
| Two updates to a key without a reducer | InvalidUpdateError | InvalidUpdateError |

On the six mixed-representation conditions, the old candidate raised 12 TypeErrors across sync/async. No such errors occurred in the normalized candidate. For both populated updates, the expected total is 5 and best is `[b,c]`; None contributes no update. Two conflicting unreduced writes must raise, not silently select a winner: this is consistent with the documented [concurrent-update contract](https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE).

Contract matches: original upstream **2/24**, exact earlier candidate **12/24**, normalized candidate **24/24**. The last 24 comprise **22 expected successful results and 2 expected conflict errors**. These are selected fixture conditions, not a model accuracy score or a claim that all LangGraph behavior passes. The base loses the parent updates, including the conflicting writes; its lack of error is not success.

## Limits

Every `resume` remains None. Resume conflicts, root-state updates, mixed goto forms, interrupt/checkpoint replay, arbitrary third-party update objects and the full upstream suite remain untested. A tuple here is a sequence of keyed writes, not a root tuple or a message-list input. Dataclass and Pydantic objects are Command.update values, not graph schemas. This is still an executable design experiment, not a complete production fix.

## Reproduce and audit

Put `edge_probe.py`, `run_edge.py` and `PROTOCOL.md` from this directory into a bundle. Copy [the unchanged prior probe](../probe.py) into that bundle as `baseline_probe.py`. Then use a new disposable root:

```bash
python run_edge.py --root /absolute/new-disposable-directory --bundle /absolute/bundle
```

Code/protocol commit before execution: `c4cecac937916af286717bf4ce066092c463091e`. Workflow commit: `ac600776a3c53f81c27ccfde7016f15e1b953d23`. The workflow being green means observations completed and the string-route controls held. Behavioral outcomes are audited separately.

[Raw artifact 10862342913](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36133731437/artifacts/10862342913), 116,826 bytes. SHA-256: `d846b02cd482c810164fad459bf9423d92246375aaa46a889b64b82f4ac797a0`. It contains full per-case reports, error tracebacks, execution logs, every source variant, diffs, scripts, protocol and dependency versions. Actions artifact retention is 30 days.

Readback verified the ZIP checksum, all 72 logged observations against their reports, sync/async equivalence, the byte-identical prior candidate and the unchanged earlier controls. The audit is reanalysis of this actual run, not another independent graph execution.

Supplemental design, execution and analysis: Zero, AI collaboration partner working with Youngseok Oh. Original issue and other participants' proposals retain their authorship.
