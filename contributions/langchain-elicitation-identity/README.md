# Is the resumed answer still attached to the question that was shown?

A companion diagnostic to [LangChain #40263](https://github.com/langchain-ai/langchain/issues/40263), reported and reproduced by Totoro-qaq. Their existing investigation covers fresh request keys failing on replay and proposes preserving the original round state. This example asks a different question: **if the key stays stable but a fresh initial request refers to a different synthetic draft, does successful resume preserve the original subject?**

The maintainer's [MCP feedback invitation](https://github.com/langchain-ai/langchain/issues/40072) led to the existing report. We are not requesting assignment, claiming its discovery, or writing a competing library fix.

## Actual observation: the key matched, the question did not

[Run34727603335](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34727603335) executed the exact diagnostic in commit `f390db0fd71382e14349f7c4869ca11eeccfcd43`. The following are recorded results, not hypothetical expected answers:

| Case | Question initially exposed by the graph | Outcome |
|---|---|---|
| Stable key, same subject | draft-A | draft-A preview completed; success |
| Stable key, changed subject on replay | draft-A | **draft-B preview completed; success; no new interrupt** |
| Fresh key, changed subject | draft-A | missing confirm-2 answer; no preview |
| Stable key, changed subject, answer includes draft-A identifier | draft-A | server rejects subject mismatch; tool error; no preview |
| Stable key, changed subject, decline answer | draft-A | declined; no preview |
| Direct SDK retry with the original opaque state | draft-A | draft-A preview completed; only one initial request |

In the stable-key drift case the returned records show:

```text
initial: key=confirm, subject=draft-A, application state=round 1
exposed interrupt: question about draft-A
supplied answer: confirm -> accept, {yes: true}
replayed initial: key=confirm, subject=draft-B, application state=round 2
state-bearing retry: round 2 receives that answer
final tool message: success, previewed:draft-B
```

The key and form schema stayed identical while the displayed message and opaque round changed. This supports checking original-question identity, not merely absence of a missing-key exception. The subject-bound-answer control detects the mismatch but does not complete the original action; the direct-session control restores the original round instead.

The diagnostic completed with `all_accepted_answers_kept_original_subject=false`. Its green workflow means these observations and controls were collected, **not that the subject-preservation property passed**.

## What runs

The real published FastMCP, MCPAdapter, LangGraph ToolNode and InMemorySaver are used in one process. The synthetic server creates a draft label on each initial request and issues opaque state referring to that round. State-bearing retries restore that exact previously issued draft. No effect happens before an accepted answer. The only effect is adding a string to an in-memory list, not touching a document, network service or account.

The diagnostic records what the graph exposed as its interrupt, the exact submitted answer, every server initial/state-bearing call, the final tool-message status and the synthetic completed subject. Five cases exercise the graph; one is a direct-session control. The application-binding control is not a proposed general adapter fix: rejecting drift is different from restoring and completing the original question.

## Reproduce the fixed-version observation

Install in a disposable Python 3.12 environment:

```sh
python -m pip install "langchain[mcp]==1.4.0" "langchain-core==1.6.2" "langgraph==1.2.11" "fastmcp==4.0.1" "mcp==2.1.1"
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false python reproduce.py --out /path/to/new-output
```

The installed elicitation module matched Git blob `efab8d70a74c74392f883df229c2053a58b2eddb`, observed at [source fa942aec](https://github.com/langchain-ai/langchain/blob/fa942aec719abd92026dcb56cab8e50a38776611/libs/langchain_v1/langchain/mcp/elicitation.py). That module is unchanged at inspected master348c9dc. Installed tools/adapter modules also matched the corresponding source blobs `9464d5eaf9ffb5df2c0134f855de75d54edf39d5` / `b1c87e1f68fe0beb11406cc774e42167afbf879c`. The actual versions and imported paths are in the returned observations. This is a fixed-version experiment, not a claim about every future release.

## Returned evidence

Original artifact10308875338: **5,365 bytes**, SHA-256 `7575280968184bece2b15dd206397b11cb76c192f149d2bbbcaafff4e2f08b57`. It contains the complete observations, dependency listing and run output. The original ZIP was downloaded, CRC/digest checked, and all six cases were compared with the 16 server entries, exposed interrupt payloads, supplied answers, completed previews and final statuses. The probe recorded no external network attempts. Dependencies were downloaded before the in-process exercise.

The first local readback script incorrectly compared the direct client's opaque wire token with decoded application state inside the server. The corrected inspection compares initial/resumed server state with server state, while retaining the wire token separately. No observation or SDK code was edited. Inspection of returned evidence is not another SDK experiment. Local preparation itself only compiled the source and checked the uploaded blob; LangChain was not installed in the working container.

## Scope and attribution

No LLM chooses tools or supplies an answer. Answers are programmed test inputs, not a person's live consent. No HTTP transport, process restart, multi-round session or production harm is covered. The source server intentionally changes the synthetic subject on a repeated initial call; this tests the replay assumption, not the prevalence of such servers. No mutation of a LangChain/SDK file is used.

This is a request-identity regression example, not a general security certification or a claim that every approval flow is affected. The normal control succeeds; the issue depends on a new initial call referring to a different question while retaining its key. No production fix is shipped here.

New diagnostic code is MIT-licensed under the terms in [the existing evidence-tool license](../../tools/evidence-mcp/LICENSE). Credit for the original fresh-key finding and its minimal graph approach remains with Totoro-qaq. Prepared by Youngseok Oh with Zero (ChatGPT).
