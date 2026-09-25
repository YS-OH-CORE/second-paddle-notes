# LangGraph #9072: reducer and parent-boundary probes

Youngseok Oh x Zero, AI collaboration partners. 2026-09-25.

Question: can a candidate retain all parent-directed sibling updates AND all Sends through a real compiled child/parent StateGraph, without inventing reducer behavior inside ToolNode?

Original report: elizandropacheco in https://github.com/langchain-ai/langgraph/issues/9072 . breken-ai and 84dnnvbdvp-debug already discussed preserving the first command and independent graph writes. This fixture supplies executable evidence to that existing discussion, not a competing PR or an original claim to their diagnosis.

Pin: 7daa3ab49d678a5da75edb08baa87db4a2be52c3. Install all four runtime libraries from that checkout. Verify ToolNode's original Git blob before any experimental edit and its actual import path in each fresh process.

Five variants: unchanged source; preserve only the first parent command; return parent commands separately; structural dict/list merge (negative control); concatenate ordered key/value writes into one parent command (experimental, not production-ready).

Each runs one tool, two sibling tools, reversed siblings, and the one-tool string-goto control, through both synchronous and asynchronous APIs. Total planned: 40 graph invocations. Capture combined commands before graph interpretation plus final parent state and reached workers.

Parent state has add_messages, numeric addition and a custom longest-batch reducer. For alpha=2/[a] and beta=3/[b,c], both updates should give total 5 and best [b,c], with both tool IDs and workers retained. Simple structural merging cannot implement those two reducers. Separate parent commands may still short-circuit at the parent boundary; measure rather than assume they work because both appear at ToolNode's output.

Use deterministic inert tools, no LLM, no network inside the probe, no actual user history or credentials. No upstream suite, LangChain create_agent wrapper, root-state updates, non-reduced conflicting writes, mixed parent destinations, or resume conflict policy is claimed tested. All resume values are None. Record failures and successful controls, full sources/diffs, environment and logs. A green workflow means the planned observations completed, not that every variant preserved state.
