# External memory opt-out: fresh creation and manager reuse

Youngseok Oh × Zero | 25 September 2026 KST

Supplemental implementation feedback for [Hermes #121935](https://github.com/NousResearch/hermes-agent/issues/121935). The original contamination report and proposed opt-out are **fmunechi's** work. This is not another upstream feature PR, a test of the reporter's private patch, or a live memory-provider evaluation.

## Why check this boundary?

At upstream commit `749220ef0007f8d87bd1531f1c24b0fe93816385`, `_init_memory` first adopts a supplied `memory_manager`, then considers fresh provider initialization in an `elif`. The issue's illustrative environment-variable branch, composed immediately before that fresh-initialization branch, handles a fresh CLI agent but cannot run after the earlier adoption branch has already won.

This matters if the proposed opt-out is implemented as a common agent option, beyond the fresh CLI path described by the reporter. It is not evidence that the reporter's stated fresh-process workaround fails.

## Executed comparison

[Exact checker](check_init_boundary.py), source commit `f0f9be8c1882386724115f1b14fc065c484fd7f7` in this repository. Run with an already authenticated GitHub CLI and Python 3.10+:

```sh
python -B -S check_init_boundary.py
```

It fetches a single pinned public source file, checks its Git blob identity, selects only `_init_memory` with the Python AST, and compares three variants. The two changes are locally authored interpretations of the issue snippet: an `elif` at the fresh-creation branch and a guard preceding both manager adoption and creation. The real user's Hermes installation is not loaded or edited.

**Observed with the opt-out set to `1`:**

| Agent input | Unmodified initializer | Illustrative `elif` placement | Guard before adoption |
|---|---|---|---|
| No supplied manager | Manager created | No manager attached | No manager attached |
| Existing manager supplied | Existing manager attached | Existing manager still attached | No manager attached |

Four controls (flag absent, or existing `skip_memory=True`, each with fresh and supplied-manager inputs) retain the same observations across all three variants. In all 18 function evaluations the fake built-in store's load method is called once and the supplied configuration is unchanged. These cases explicitly request the built-in memory toolset. No unexpected warning was recorded.

**Important scope:** MemoryStore, provider loader/manager, configuration helpers, logger and tool injection are test doubles. The selected initializer's real control flow runs, not the full module or an AIAgent conversation. This observes manager attachment and initialization calls, not successful network suppression across an entire application. SOUL/rules/skill rendering, provider hook behavior, concurrent sessions, delegated processes, CLI argument plumbing and actual built-in file contents are not tested. A fake loader call is not proof of a real file read. No real user memory, provider request, model call or application setting was used.

## Interpretation

If the flag is intended to apply to shared initialization, evaluate it before accepting an injected manager as well as before constructing one. Do not close or mutate a caller-owned shared manager merely to keep this agent from attaching it. This comparison is a placement check, not a complete lifecycle patch.

Keep the contract narrow: disabling an external provider is not a universal read-only evaluation mode. The documented provider lifecycle includes context injection/prefetch as well as writes. A full provider ablation therefore changes available external-memory context; a read-context-preserving no-write evaluation is a different design. The built-in store and other learning/session paths remain separate concerns.

## Provenance

- Upstream source: `agent/agent_init.py`, commit `749220ef0007f8d87bd1531f1c24b0fe93816385`, Git blob `a3e3bd91d4482d14a977efc7e95f2f9262f814b4`.
- Full upstream file SHA-256: `b8fc783654b7b95fe5a29708c12cdbea6a609e8429f000702d57a3002fb73dd7`.
- Executed checker SHA-256: `7fc60899d4d86c9f2af0c572f46b8c92525b02c3aec0395d7c63840ae4fa889e`.
- Structured report SHA-256: `ec381a67351d2da5589010f5eb90a501a726012724aff903eb53a311214e257e`.
- UTC run start: `2026-09-24T20:59:28.863059+00:00`, Windows Python 3.12.10. Process exit 0, six scenarios / 18 function calls, no error entry in the report. The exact report bytes were copied back and their SHA-256 rechecked; that is artifact bookkeeping, not an independent replication.
- An initial public-source request from the assistant's separate working container failed DNS resolution before any test. The successful run used the already-authorized PC's GitHub CLI for public-source reads only. No credentials were read or printed and no extra package was installed.

Source and documentation checks: [external provider lifecycle](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers), [built-in memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory). Prior reports and the proposed feature retain their authorship. Fixture design, execution and writing: **Zero, an AI assistant, for Youngseok Oh (@YS-OH-CORE)**. No reviewer acceptance, deployed fix, or institutional endorsement is implied.
