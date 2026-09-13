# Resume the saved question instead of making a new one

An opt-in application graph for one MCP form-driven operation. It follows the
[question-identity diagnostic](../langchain-elicitation-identity/README.md), which
extended Totoro-qaq's [LangChain #40263](https://github.com/langchain-ai/langchain/issues/40263).
This is not a competing upstream assignment or a replacement for MCPAdapter.

The distinction is where the checkpoint goes:

```text
begin tool round -> checkpoint the returned question and opaque state
                 -> review / interrupt
                 -> checkpoint the supplied answer
                 -> retry that same round with its original state
                 -> checkpoint the next question or terminal result
```

The interrupting node never performs the initial tool call. Rebuilding that node
therefore reads the already-persisted question, not a freshly generated question
with an old answer. The existing LangGraph checkpoint/interrupt APIs supply the
persistence; no SDK file is patched. This is an application recipe, not a new
checkpointing algorithm.

## Use in an application that owns its workflow

Install `requirements.txt` in a disposable environment. With a connected MCP
session and a checkpoint saver chosen by the application:

```python
from round_graph import build_round_graph
from langgraph.types import Command

config = {"configurable": {"thread_id": "one-operation"}}
graph = build_round_graph(connected_session, saver)
paused = await graph.ainvoke(
    {"tool_name": "preview", "arguments": {"case": "example"}},
    config, durability="sync",
)
# Present only paused["__interrupt__"][0].value to the authorized reviewer.
# Obtain the response to those exact keys; do not manufacture consent.
finished = await graph.ainvoke(Command(resume=reviewer_answer), config, durability="sync")
```

The resume shape is `{"responses": {"original-key": {"action": "accept",
"content": {...}}}}`; decline and cancel carry no content. The caller must supply
all and only the original request keys. The server validates form content and
authorization. Do not infer approval merely from a valid schema.

The caller owns session lifecycle, server identity, checkpoint access and serializing
concurrent resumes for one thread. Use one thread per operation. On resume, keep
the same graph topology, tool/arguments, server, thread and checkpoint store;
send `Command(resume=...)`, not a fresh initial input. The example supports form
elicitations only. URL prompts, sampling, roots and continuation-only rounds are
rejected, not guessed. At most eight review rounds are permitted by default.

Checkpoint frames contain opaque server state and are **private application data**.
They are not automatically safe for a model or a UI. Only the selected question
is exposed at the interrupt. The application must select terminal output for its
own consumer; do not serialize the whole graph state into a model message.

## Test boundary

The probe compares two original MCPAdapter paths with eight application-graph
cases, using fixed published SDK versions. It closes and reopens the real SQLite
connection and rebuilds the graph between every question and resume. The in-process
MCP server and Python interpreter stay alive. This tests persisted-state reopening,
**not an operating-system process restart**.

Cases: stable-key drift, fresh-key drift, unchanged subject, two review rounds,
decline, cancel, a wrong answer key, and an explicit server error. Only synthetic
preview labels are appended to an in-memory list. No LLM, live human decision,
HTTP service, credential, paid API or production side effect is involved.

## Observed on 2026-09-13

[Run34758706876](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34758706876)
executed commit `2cda1994e4584a4aa07eaebaa3a97695f0e10649` with the pinned packages.
No SDK file was modified.

| Path and case | Recorded result |
|---|---|
| Original adapter, stable key with a regenerated subject | The question exposed A; B completed and the tool returned success. |
| Original adapter, fresh key with a regenerated subject | Missing-answer error; no preview completed. |
| Application graph, unchanged/stable/fresh-key cases | A completed; only one initial tool request per operation. |
| Application graph, two distinct review rounds | Two original questions were exposed in order; A completed after both answers. |
| Application graph, decline or cancel | No preview completed. |
| Application graph, wrong answer key | Rejected before another tool call. |
| Application graph, server error | No preview completed; terminal error flag remained true. |

Eight application cases reopened nine saved question frames; each frame matched
its saved copy, and each state-bearing wire call used the immediately preceding
response's exact opaque token. The database connection was closed and a new graph
compiled for each continuation. There were 16 application tool calls and five
baseline calls, not 21 independent trials or model-chosen actions.

The original 8,553-byte artifact10318715472 has SHA-256
`d5160caac243efa119f16e9e0a6860126fc2a19484d273c1b5c021995313b18e`.
It was downloaded and checked against all ten case records, 21 server entries,
nine saved/reopened pairs, visible questions, programmed answers, wire tokens,
completed subjects and error flags. Eight answer tests passed locally and in the
hosted run. No external socket attempts were recorded during the exercise.
Inspection of returned files is not another SDK execution.

The demonstration uses disk-backed SQLite checkpoints, but the MCP server and
interpreter remain alive. It does not establish recovery after an OS-process
crash, session recreation or remote-server restart. Invalid answers fail the
current invocation; the host must define how it validates/corrects responses
rather than assuming automatic recovery from an invalid resume value.

Local work ran only the pure answer tests and syntax checks; package acquisition
was unavailable there. The installed-SDK observations above came from the hosted
run. The earlier fresh-key finding and replay mechanism remain credited to the
original reporter; the new deliverable is this tested application-level route.

```sh
python -m unittest -v test_answers
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false python probe.py --out /path/to/new-output
```

Dependencies are installed before the exercise. The exercise blocks external
socket connections. It records exact questions, programmed answers, server-side
observations, opaque wire state supplied/received, saved/reopened frames and
module/version identities. The public artifact contains synthetic observations
and logs, not checkpoint databases or user data.

## Not an exactly-once guarantee

A crash after a remote side effect but before its result is checkpointed can still
leave an uncertain operation. This example does not close that distributed commit
gap. Production callers still need server-side idempotency/receipts and a policy
for uncertain outcomes, expiration, revocation, concurrent replies and workflow
migration. Rejecting a changed key and preserving a recorded round are useful,
but neither proves a real person's authorization.

Sources: [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts),
[functional API and replay](https://docs.langchain.com/oss/python/langgraph/functional-api),
and [SQLite saver](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-sqlite/langgraph/checkpoint/sqlite/aio.py).
New files use the MIT terms at [the existing license](../../tools/evidence-mcp/LICENSE).
Original fresh-key report credit remains with Totoro-qaq. Prepared by Youngseok Oh
with Zero (ChatGPT). Existing published tools and releases are unchanged.
