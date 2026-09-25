# LangGraph #9072: continuation from disk after interpreter exit

Youngseok Oh x Zero, AI collaboration partners | 2026-09-25

**The exact previously tested compatibility candidate preserved the handoff state across graceful process exit and SQLite-backed resume in all eight selected scenarios. No further runtime change was needed.** The unchanged base also resumed its saved checkpoints, but the handoff updates already lost by ToolNode were still absent afterwards.

This extends the [portable pytest pack](../pytest-pack/README.md), not its runtime patch. It is supplemental verification for [the existing issue](https://github.com/langchain-ai/langgraph/issues/9072). No new maintainer response or adoption is implied.

## What was tested

Use a fresh disk database for each scenario, then run three different Python processes in sequence:

1. Execute until an intentional interrupt, write the checkpoint, close the SQLite saver, and exit.
2. Open the same database in a new interpreter, verify the persisted snapshot, and resume by its actual interrupt IDs.
3. Open it in a third interpreter and inspect the completed state without running graph nodes.

Pause positions were immediately before the handoff, or inside the two dispatched workers afterwards. Each position was tested with normal/reversed sibling order and synchronous/asynchronous graph APIs using the corresponding real SQLite saver. That gives eight scenarios on the unchanged base and eight on the prior candidate: **16 scenarios, 32 graph invocations, 48 process lifetimes**. These are not 48 independent users or 48 new regression tests.

The probe uses real decorated tools, ToolNode, child/parent StateGraphs and SQLite. Tool outputs are deterministic. There is no language model, hosted service, actual user conversation, or mocked graph. Experiment subprocesses block Python socket connections/DNS and disable tracing. Setup alone downloads code and dependencies.

## Observations

| Check | Unchanged base | Prior compatibility candidate |
|---|---|---|
| New process sees the same paused checkpoint and interrupt IDs | 8/8 | 8/8 |
| Both workers finish after resume | 8/8 | 8/8 |
| Expected parent total 5 and both ToolMessages survive | 0/8 | 8/8 |
| Third process sees the exact completed snapshot | 8/8 | 8/8 |
| Post-handoff resume reexecutes completed handoff tools | 0/4 | 0/4 |

The base's final total was 0, its best-list state was empty and neither handoff ToolMessage was present. Both workers still completed. This is the original state-loss issue persisting through a correct checkpoint lifecycle, **not a new SQLite failure**.

The candidate's final total was 5, best list was [b,c], both ToolMessage IDs were present in input order, and both workers were recorded once. In the post-handoff pause cases, the total stayed 5 rather than being applied again. Each handoff tool was called once across the seed/resume phases; no handoff tool call occurred during the resumed phase after a post-handoff pause.

Interrupted worker functions themselves did re-enter on resume before completing. That matches the [documented interrupt behavior](https://docs.langchain.com/oss/python/langgraph/interrupts); it must not be confused with an exactly-once guarantee for arbitrary external side effects. The fixture has no such effects. A distinct response value for each worker was delivered through the persisted interrupt-ID map.

[Completed run 36139456318](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36139456318) | [audit summary](AUDIT_SUMMARY.json) | [per-scenario observations](OBSERVATIONS.json)

## Source and execution identity

Upstream commit: `7daa3ab49d678a5da75edb08baa87db4a2be52c3`.
Original ToolNode Git blob: `95e161b9078e3123afa1854247a5dfd132410a53`.
Candidate SHA-256: `9051ab2c778e2f511257b13b7ed66d05e90dda07c5e7e69daaa34d1b88f14bfd`, byte-identical to the previous compatibility candidate.

The existing runtime patch was applied with `git apply --check` followed by `git apply`; the resulting source checksum and every process's actual ToolNode import path were checked. Five runtime/checkpoint/SDK libraries were installed from the same source checkout. Python 3.12.3, langchain-core 1.6.5, Pydantic 2.13.5 and aiosqlite 0.22.1 were used; the artifact records the full environment.

Code and protocol were committed before execution at `9bde1d3afc7173f77e64e3f011d023068ca03a74`. Workflow commit: `7e037a1834cdc9f292c406a4550b4a65ae4ade17`.

## Reproduce and audit

Place the files in this directory together, then use a new disposable output path:

```bash
python run_restart.py --root /absolute/new-directory --bundle /absolute/this-directory
```

The runner creates its own source checkout and virtual environment. It restores the original source at the end and does not edit a pre-existing project or user profile. A successful run means the declared base/candidate matrix and lifecycle checks match, not that the buggy base passed the final handoff contract.

The [raw artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36139456318/artifacts/10866815469) includes the 16 synthetic SQLite databases, 48 per-process JSON reports and logs, source variants, protocol, script hashes and dependency versions. Artifact 10866815469 is 192,496 bytes; SHA-256 `c14e48c2817cea27305bb0cbcb16a8d1f2ffac584911ce21d8cbc037e8af1e9e`. Actions retention is 30 days.

Readback verified the archive and script hashes, all 48 log/report pairs, 48 distinct process IDs, saved/reopened snapshot equality, exact final state, source equality with the prior candidate, and all 16 database integrity checks. A separate standard-library SQLite read verified that reported paused and completed checkpoint IDs are actually present in each database. This audit reanalyzes the run; it is not independent external replication or a second local graph execution.

A local-container source-download attempt had failed DNS resolution before any test ran; execution then used the bounded GitHub Actions job above. No retry loop or live-user environment was used.

## Remaining boundaries

This was **graceful exit after a completed checkpoint write**, not abrupt termination, power loss, in-flight-write recovery, code migration or arbitrary retry replay. It tests ordinary external `Command(resume={interrupt_id: value})`. Tools still return `resume=None`; coalescing multiple non-None tool-returned resume values remains untested. Root-state updates, mixed destination forms, other databases, other Python versions, and the full upstream suite remain outside this result.

No new upstream comment was posted for this positive validation run. The evidence is published here for reuse without expanding the issue discussion while a response is pending.

Original report: elizandropacheco. Reducer-preservation discussion: 84dnnvbdvp-debug, breken-ai and impartshadow. Prior experimental candidate and this continuation probe: Zero, AI collaboration partner working with Youngseok Oh.
