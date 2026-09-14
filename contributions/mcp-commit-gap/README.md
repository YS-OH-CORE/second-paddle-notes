# An effect completed, but its client checkpoint did not

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.
An additive companion to [PR35's clean stdio restart](../stdio-round-restart/README.md),
not another run of that experiment. The existing saved-round graph is unchanged.

## New fault boundary

A prepare process saves a form. A new client submits the programmed answer over
real MCP stdio. The fixture server commits a harmless SQLite label and returns
a result. Immediately after the SDK receives that result, a wrapper records a
fault marker and calls `os._exit(73)`, before returning to the graph node.
This bypasses normal client cleanup and leaves the graph result uncheckpointed.
A fresh client and server reopen the same two databases. Recovery uses
`graph.ainvoke(None, config, durability='sync')` for the pending node, not a new
initial request or a new approval. The recovery process first records and checks
that the checkpoint contains the original form and answer, a pending continuation,
and no terminal result. The parent separately reads the server's committed label.

This injection is after the reply was received, not a lost reply before delivery,
SIGKILL at an arbitrary instruction, power failure, or machine reboot. Only these
new test processes and their disposable files are affected. Exceptional cleanup
kills only a process group that this harness created.

## Three server policies to compare

| Policy | Expected result to check, not an observed result until execution |
| --- | --- |
| Deliberately naive repeat | Reapplying the same original request creates a second label and a different effect ID. |
| Closed-round guard | No second label, but recovery receives ROUND_ALREADY_CLOSED rather than the original success. |
| Durable bound receipt | Return the original result without another label. Reject a subsequently changed answer under the same token. |

The receipt fixture stores the label, canonical request binding, and original
result in one SQLite transaction. It uses existing database facilities, not a
new checkpoint algorithm. The binding includes tool name, arguments and the full
answer object. True and numeric one differ; significant whitespace is retained.
A valid changed-note control tests that cached success cannot be reused for a
different answer. The two other policies are deliberate application controls,
not newly discovered upstream SDK defects.

## Reproduce

From a checkout in a disposable environment:

```sh
python -m pip install -r contributions/preserved-mcp-rounds/requirements.txt
(cd contributions/mcp-commit-gap && python -S -m unittest -v test_receipts)
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false \
  python contributions/mcp-commit-gap/probe.py --root /path/to/new-output
```

Use a new output directory and leave probe assertions enabled. Linux is the
intended fault-harness platform. Sixteen local standard-library store tests passed;
these are not SDK crash experiments. Full installed-SDK execution is pending at
preparation. Local package acquisition failed DNS, so the hosted workflow will
perform that part. Its read-only public Ubuntu job has a six-minute cap, and the
probe has a three-minute ceiling. It retains only synthetic JSON/logs, not databases.
Top-level dependency pins match PR35; the full resolved environment is recorded.

## Evidence and limits

The harness compares client calls with server observations, source hashes,
process ordering, abnormal exit codes, the parent-observed committed effect,
reopened graph state, pending-node replay, returned receipt and effect counts.
Every phase has a separate client and server. IP socket connections during the
exercise are blocked by a Python audit hook; dependencies are downloaded first.
This is not operating-system network isolation or independent certification.

The fixture's only effect is a row in the same SQLite database as its receipt.
A receipt written after an unrelated external API call would still leave another
commit gap. This demonstration does not solve that case, make arbitrary remote
effects exactly once, authenticate a server/user, or provide production token
retention, expiry, revocation, or concurrent-resume policy. All answers are
programmed fixtures, not genuine human consent. No model, provider key, private
checkpoint, or outside-project contact is involved.

Sources: [LangGraph checkpointers and durability](https://docs.langchain.com/oss/python/langgraph/checkpointers),
[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html),
[Python abrupt exit](https://docs.python.org/3/library/os.html#os._exit), and
[SDK manual continuation](https://github.com/modelcontextprotocol/python-sdk/blob/v2.1.1/docs_src/mrtr/tutorial002.py).
The earlier question-replay report remains credited to Totoro-qaq in the linked
history. New code uses the [existing MIT license](../../tools/evidence-mcp/LICENSE).
