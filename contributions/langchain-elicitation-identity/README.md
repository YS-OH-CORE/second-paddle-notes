# Is the resumed answer still attached to the question that was shown?

A companion diagnostic to [LangChain #40263](https://github.com/langchain-ai/langchain/issues/40263), reported and reproduced by Totoro-qaq. Their existing investigation covers fresh request keys failing on replay and proposes preserving the original round state. This example asks a different question: **if the key stays stable but a fresh initial request refers to a different synthetic draft, does successful resume preserve the original subject?**

The maintainer's [MCP feedback invitation](https://github.com/langchain-ai/langchain/issues/40072) led to the existing report. We are not requesting assignment, claiming its discovery, or writing a competing library fix.

## What runs

The real published FastMCP, MCPAdapter, LangGraph ToolNode and InMemorySaver are used in one process. The synthetic server creates a draft label on each initial request and issues opaque state referring to that round. State-bearing retries restore that exact previously issued draft. No effect happens before an accepted answer. The only effect is adding a string to an in-memory list, not touching a document, network service or account.

Six cases separate the mechanisms:

- Same key and same question, normal graph resume.
- Same key but a different draft on the replayed initial request.
- Fresh key and changed draft, reproducing the missing-key control.
- Changed draft with an answer explicitly bound to the original draft identifier and a server-side equality check.
- A declined answer, with no preview completed.
- Direct MCP session retry with the first response's original state and answer, avoiding another initial request.

The diagnostic records what the graph exposed as its interrupt, the exact submitted answer, every server initial/state-bearing call, the final tool-message status and the synthetic completed subject. The normal application-binding control is not a proposed general adapter fix: rejecting drift is different from restoring and completing the original question.

## Frozen source and results boundary

Install in a disposable Python 3.12 environment:

```sh
python -m pip install "langchain[mcp]==1.4.0" "langchain-core==1.6.2" "langgraph==1.2.11" "fastmcp==4.0.1" "mcp==2.1.1"
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false python reproduce.py --out /path/to/new-output
```

The installed elicitation module must match Git blob `efab8d70a74c74392f883df229c2053a58b2eddb`, observed at [source fa942aec](https://github.com/langchain-ai/langchain/blob/fa942aec719abd92026dcb56cab8e50a38776611/libs/langchain_v1/langchain/mcp/elicitation.py). That module is unchanged at inspected master348c9dc. Other module identities and installed versions are recorded. This is a fixed-version experiment, not a claim about every future release.

At preparation, the script compiled and its uploaded bytes matched the local file. Installed-SDK execution is pending. A completed diagnostic will explicitly record subject drift as a failed preservation property rather than calling the library all-green. The program exits successfully only when it collects the stated contrast and controls; that does not mean the subject-preservation requirement passed.

No LLM chooses tools or supplies an answer. Answers are programmed test inputs, not a person's live consent. No HTTP transport, process restart, multi-round session or production harm is covered. The source server intentionally changes the synthetic subject on a repeated initial call; this tests the replay assumption, not the prevalence of such servers. No mutation of a LangChain/SDK file is used.

New diagnostic code is MIT-licensed under the terms in [the existing evidence-tool license](../../tools/evidence-mcp/LICENSE). Credit for the original fresh-key finding and its minimal graph approach remains with Totoro-qaq. Prepared by Youngseok Oh with Zero (ChatGPT).
