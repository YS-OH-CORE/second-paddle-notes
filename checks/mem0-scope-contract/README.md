# Scoped memory deletion: remove the target, preserve the rest

An executable storage-level follow-up to [our Mem0 review](https://github.com/mem0ai/mem0/issues/7452#issuecomment-5855365753). **Not an installed fix, full-SDK test, or general benchmark.**

## Run

Save the [pinned upstream storage.py](https://raw.githubusercontent.com/Sai-Sreenath-1819/mem0/af93b81bc9573be1b78014b5005a0b0d950605bb/mem0/memory/storage.py) beside `review.py`, then run:

```sh
python -B review.py --storage storage.py --out my-result.json
```

Python standard library only; tested with Python 3.13.5 / SQLite 3.46.1. Before importing the source, the reviewer checks its complete byte length and published Git blob ID. The run uses fictional in-memory databases, not an existing user database. There is no network, model, package installation, API key or GPU in the execution. A source-file path is not a database-file path. Existing output files are not overwritten.

## Contract and observed result

Fourteen fictional user/agent/run scopes each hold two messages. For each of fourteen filters, the expected deletion set is computed from **original identity dictionaries**, independently of the reference key parser. Targets must disappear; unrelated rows must retain their IDs, content, roles and timestamps. After adding a new message, the native reader must not return an old target and must still return unrelated old messages.

In the user-only Alice case, five matching scopes contain ten target rows. The canonical-builder plus exact-key cleanup deletes two rows, leaving eight target rows readable. The in-memory field-matching reference deletes all ten without changing any of the eighteen unrelated rows.

| Adapter | Conditions satisfying the broader filter contract |
|---|---:|
| Canonical builder plus native exact-key cleanup | 2 / 14 |
| Field-matching in-memory reference | 14 / 14 |
| Deliberately delete-everything test double | 0 / 14 |
| Deliberately do-nothing test double | 1 / 14, the no-match case |

**The native exact-key operation works as its own API specifies.** The problem is composing it as if it implemented a broader filter. These are selected edge cases, not a Mem0 reliability score or fourteen new bugs. Negative controls ensure that over-deletion and under-deletion are both detected.

The tests include partial field combinations, a complete triple, no match, similar names, literal delimiters and percent signs, Unicode and wildcard characters. The reference decodes only canonical keys, matches fields exactly, and uses one SQLite transaction. Unknown or ambiguous keys abort without deletion. The reference refuses non-memory databases and is not intended as a production patch.

Twelve additional local unittest methods passed, including invalid-filter rejection, repeated deletion, injected delete failure and transaction rollback. The standalone reviewer was executed against the byte-checked upstream module and produced the same per-case observations as the modular test kit. This is a same-analyst packaging check, not independent replication. `SUMMARY.json` records the measured scope and limits; `--out` retains every per-case observation rather than only totals.

## Source, limits and handoff

Native storage: `Sai-Sreenath-1819/mem0`, commit `af93b81bc9573be1b78014b5005a0b0d950605bb`; storage Git blob `0b49c8e8be46779722a7827b2e98319930433d40`; SHA-256 `611f6f177cf99ef402e8ea3070e0f40720a75f7b013711e35da27c2e45f9bb5d`. The two canonical-builder functions in `review.py` are an unchanged excerpt from that commit's `mem0/memory/main.py`. The full main module is not imported.

The source was obtained through the GitHub connector and reconstituted locally; the complete storage bytes matched the published Git blob. Direct container DNS was unavailable. No source mismatch was accepted. No user PC or operational memory was touched.

This tests the **SQLite component**, not the full Memory/AsyncMemory API or a new extraction prompt. Not tested: vectors, entities, SDK normalization, TypeScript, concurrent processes, large-store scan cost, backup erasure. The scan-based reference and unknown-key handling require further design review before real integration. The earlier full-SDK sync observation remains a separate experiment; these results do not expand it into an executed async or multi-user SDK matrix.

PR #7455 is closed by the project's accepted-issue gate, not merged; [the bot explains](https://github.com/mem0ai/mem0/pull/7455#issuecomment-5835811292) that closure is not rejection. No competing upstream PR, install or request for a merge is made here. The code is reusable evidence for that existing discussion.

Direction: **Youngseok Oh**. Tests, reference adapter, execution and analysis: **Zero**, his AI collaboration partner. Original code and cleanup remain credited to Mem0 contributors and the proposed-fix author. Apache-2.0 license and original copyright attribution are retained in `LICENSE`. No human line-review, independent reviewer approval or upstream adoption is claimed.

## 한국어

지울 범위에 속한 여러 대화는 전부 지우고, 범위 밖의 기록은 그대로 보존하는지 검사한다. 테스트용 대조 구현에서는 이 조건이 충족됐지만, 실제 Mem0 전체나 개인 기억에 설치한 것은 아니다. 기존 문제를 설명하는 댓글에서 나아가 다른 사람이 직접 재현할 수 있는 작은 검사를 남긴다.
