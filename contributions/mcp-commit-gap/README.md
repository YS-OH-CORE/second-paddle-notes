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

## Observed on 2026-09-14

[Run 34794857975](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34794857975)
completed with executable head `cf8183efb1f242a9e6c0e17f31f1fcbd2d00565b`.
All three deliberately injected client exits returned code 73. Before recovery,
each server had one committed label while the client checkpoint had the original
form and answer, status `answered`, pending `continue_original_round`, and no
terminal result. Fresh processes resumed that pending node over actual MCP stdio.

| Policy | Labels before / after recovery | Returned result |
| --- | --- | --- |
| Deliberately naive repeat | 1 / 2 | Success text repeated, but effect ID changed from 1 to 2. |
| Closed-round guard | 1 / 1 | ROUND_ALREADY_CLOSED with isError=true; original success not recovered. |
| Durable bound receipt | 1 / 1 | The complete original result, including effect ID 1, was returned unchanged. |

The receipt case then submitted a syntactically valid changed note under the same
token. It returned REQUEST_BINDING_DIFFER with isError=true; the server's entire
record stayed unchanged. There were 10 tools/call requests across nine client and
nine server processes: three new scenarios, not 10 deployments or human approvals.
The three server policies are programmed controls, not prevalence estimates.

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
intended fault-harness platform. Sixteen standard-library store tests passed both
locally and in the hosted run; they are not 16 SDK crash experiments. Local package
acquisition failed DNS, so the full installed-SDK run occurred in hosted CI.
Its read-only public Ubuntu job has a six-minute cap, and the probe has a
three-minute ceiling. It retains only synthetic JSON/logs, not databases.
Top-level dependency pins match PR35; the full resolved environment is recorded.

## Returned evidence checked

Original artifact `10329531143`: 39,466 bytes, 58 synthetic JSON/log members,
SHA-256 `1faa187020082c5425a85d006ecdede14af0d2a4afe33a20dd7b6bce2635ba0c`.
The returned ZIP was opened and its digest, CRC, separate wire/server records,
process ordering, abnormal exit markers, pre-recovery checkpoint and server state,
post-recovery result/effect IDs, and changed-answer rejection were checked with a
separate standard-library reader. This readback is not another SDK execution.
The original ZIP, reader and matching source snapshot are delivered together in
the conversation bundle. Hosted artifact retention is 14 days.

Both client and server source records match the prepared probe SHA-256
`335ff054beaa34941861246d810d840c166bc030e63c71d00ce52ec60fa7001b`
and receipt-store SHA-256
`4150a6e32b72cfcb1897fe9d3e3a86760f5b29039e7a00c79e575685881a1ad5`.
The unchanged graph and requirements bytes were checked too. The later README
completion edit does not change the executed code. A transfer typo in the first
receipt-store upload was caught by readback and corrected before the PR run;
the actual integration run completed on its first attempt.

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
