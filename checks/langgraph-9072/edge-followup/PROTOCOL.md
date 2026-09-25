# LangGraph #9072: stress our ordered-writes experiment

Youngseok Oh x Zero, AI collaboration partners. 2026-09-25.

Follow-up to https://github.com/langchain-ai/langgraph/issues/9072#issuecomment-5831629639 . A discussion participant revised their earlier recommendation after our real-parent result. This does not establish maintainer approval. Before advancing the candidate, test its own untested representation boundaries.

Pin: 7daa3ab49d678a5da75edb08baa87db4a2be52c3, still main when checked. The Command implementation declares _update_as_tuples as a Sequence and returns an incoming tuple unchanged. Our earlier candidate directly adds its two return values. Hypothesis: mixing tuple-shaped and dict/None/model updates causes list-plus-tuple TypeError even though tuple-plus-tuple works. Normalize both to lists without collapsing duplicate keys and compare.

Three implementation variants: unmodified base, exact earlier ordered-writes source (checksum verified), same experiment with list normalization. These are disposable experiments, not third parties' implementations.

Repeat all eight earlier compiled-graph cases without changing their inputs. Add eight conditions, each through invoke and ainvoke: dict/tuple; tuple/dict; tuple/tuple; dataclass/tuple; tuple/Pydantic model; None/tuple; tuple/None; two conflicting writes to a channel with no reducer. Total planned: 72 graph invocations. Last condition should raise InvalidUpdateError rather than silently select a winner. A detected conflict is expected behavior, not a failed fix.

All paths use real ToolNode, decorated tools and compiled child/parent graphs. Same prior addition/longest-batch/message reducers; deterministic tool output, no LLM, no service, no credentials or user history. Actual graph invocation still runs when the intermediate combiner throws, so the error is recorded at both boundaries. Keep failures and full tracebacks. Save all source variants, diffs, logs, dependency versions and exact per-case expectations/results.

No inference about resume handling follows: every resume remains None. Root-state updates, mixed goto forms, interrupts/checkpoint replay and the upstream suite remain untested. The tuple input is a sequence of keyed writes, not a root tuple and not a list-of-messages input. Dataclass and Pydantic objects are Command.update values, not graph schemas. This is a focused test of the cited representation and conflict cases only.

The run is successful if the observations finish and unchanged string-route controls hold. A separate readback audit must establish the matrix. Do not change expected values merely to turn observations green. Credit original report to elizandropacheco and reducer discussion to 84dnnvbdvp-debug, breken-ai and impartshadow; this follow-up tests Zero's own earlier candidate.
