# LangGraph #9072: disk checkpoint continuation across process exits

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

This is a new verification boundary, not another runtime correction. Use the exact compatibility candidate from the prior pytest pack (SHA-256 9051ab2c778e2f511257b13b7ed66d05e90dda07c5e7e69daaa34d1b88f14bfd), and the unchanged base at 7daa3ab49d678a5da75edb08baa87db4a2be52c3. No new upstream response was present when this work began. No maintainer approval is inferred.

Question: after a controlled interrupt, a completed checkpoint write, and graceful interpreter exit, can a fresh interpreter recover that same checkpoint, resume the handoff, and leave the expected parent state on disk without reapplying the handoff updates? This is NOT an abrupt-crash, power-loss, automatic retry, or exactly-once external-side-effect guarantee.

Eight scenarios per implementation: pause before the handoff or within the dispatched workers afterwards, normal/reversed sibling order, sync/async graph APIs with the corresponding real SQLite saver. Each scenario uses a new disk database and three independent processes: seed-and-pause; reopen-and-resume; reopen-and-read-only-inspect. Two graph invocations per scenario; the inspector only reads state. Planned totals: 16 scenarios, 32 graph invocations and 48 process lifetimes.

Real ToolNode, decorated deterministic tools, parent/child StateGraphs, SQLite and JSON/MessagePack checkpoint serialization are used. No model, mocked graph, remote memory service, actual user history or hosted database is used. Setup downloads the pinned code/dependencies; the experimental subprocesses deny Python socket/DNS calls and disable tracing. Parent state contains addition, longest-list and message-ID reducers, plus recorded completed workers. Expected final state: total 5, best [b,c], exactly one ToolMessage per tool call, both completed workers. Distinct per-worker resume values are routed by actual persisted interrupt IDs.

Seed closes the saver and exits before resume starts. Compare the fresh process's pre-resume snapshot, including checkpoint and interrupt IDs, with the saved paused snapshot. Compare a third process's snapshot with the completed one. Record actual tool/worker entry and completion events. Interrupted worker code is EXPECTED to re-enter on resume; do not mislabel that documented behavior as duplicate tool execution. In the post-handoff case, already completed handoff tools should not run again and additive updates should not be doubled. In the pre-handoff case, tools should run only after approval. Verify SQLite file header and integrity with a separate standard-library read-only connection.

The base is expected to resume and preserve its own checkpoint faithfully but still lack the original lost handoff updates; disk persistence cannot recover content that never reached the parent. The exact prior candidate is expected to satisfy all selected state and lifecycle checks. Keep every failed comparison. Do not change expectations just to obtain a green run. Report scenario outcomes rather than treating all internal assertions as independent tests.

Scope still excludes coalescing non-None resume values returned by sibling tools. Here tools return resume=None, while the external caller uses documented Command(resume={interrupt_id: value}) for suspended workers. Root-state updates, mixed goto forms, other databases, abrupt termination, changed code during restart, full upstream suite and real LLM behavior remain outside this experiment.

Primary behavior references:
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://github.com/langchain-ai/langgraph/issues/9072

Original diagnosis: elizandropacheco. Reducer-preservation discussion: 84dnnvbdvp-debug, breken-ai and impartshadow. Supplemental prior candidate and this continuation probe: Zero, AI collaboration partner working with Youngseok Oh.
