# Memory representation: first CPU feasibility pilot

Youngseok Oh (오영석) × Zero (ChatGPT) | 24 September 2026 KST

**Completed: 24 actual small-language-model forward passes on a standard GitHub-hosted CPU runner. No accuracy advantage was observed from the added relationship annotations in this pilot.** This is a development feasibility exercise related to [Note 14](../../notes/14-interaction-is-the-event.md), not execution of that note's complete matched, held-out study.

## What was fixed before model inference

[Protocol and all eight fictional cases, committed before execution](https://github.com/YS-OH-CORE/second-paddle-notes/blob/c713b8c8f46ccb249e8076d3989cae775e494009/experiments/memory-cpu-pilot/pilot.py).

- Model: `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775`; Qwen's released weights, not a model trained by this project.
- Eight authored English cases, each presented under three conditions. All conditions preserve the same chronological, role-labelled statements and answer options. One adds correct authored event relations, one adds deliberately reversed relations, and one adds none.
- Exactly one forward pass per case/condition, 24 planned and completed. Inference order was shuffled with seed `20260924`. There were no answer-dependent retries, exclusions or prompt changes.
- Measurement: compare next-token logits for the single-token labels A/B/C and select the largest. This is forced-choice classification, not an unconstrained conversational rollout. The full-vocabulary probability mass of these options was also recorded.
- These are public development cases, not a held-out test set or any user's private history. Relation labels were authored oracle annotations, not extracted by a memory system.

## Actual execution and observed result

[Completed run 35887197137](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35887197137) | [Exact workflow](https://github.com/YS-OH-CORE/second-paddle-notes/blob/a0719b71d6189609c9c860b2dfaeba8b83930430/.github/workflows/memory-cpu-pilot-20260924.yml) | [Original output artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35887197137/artifacts/10763690740)

| Condition | Correct choices | Prompt length |
|---|---:|---:|
| Chronological statements only | 5/8 | 145–177 tokens |
| Same statements + correct relation | 5/8 | 154–188 tokens |
| Same statements + reversed relation | 5/8 | 154–188 tokens |

The selected answer was identical across all three conditions for each case, not merely equal in total accuracy. All three missed the same cases: publication permission revoked, an assistant's meeting-time suggestion explicitly left unselected, and an assistant's guess about an unstated childhood preference. They correctly answered the corresponding affirmative controls and both outline/slide-goal cases.

The count unit is **eight paired cases**, not 24 independent cases. All option labels and order were fixed within a case. The two edge conditions happened to have equal token counts per case; the chronology condition was shorter. Input lengths were not balanced by padding or truncation. Thus this is neither a token-matched causal test nor evidence that event structure cannot help.

The worker used CPU float32, two CPU threads, 494,032,768 model parameters and no GPU. The recorded forward-pass section took 17.082 seconds; model download/loading plus inference took 27.098 seconds. Dependency setup and artifact upload are outside the latter duration. Peak process RSS was 3,280,516 KiB. These timings characterize this one hosted run, not a benchmark or a claim about another computer.

## Reproduction and retained evidence

The workflow creates an isolated environment, installs CPU PyTorch 2.6.0 and Transformers 4.51.3, and downloads the pinned public safetensors weights. `trust_remote_code=False`, no API credential, no training, no paid inference endpoint, no personal computer connection. Package transitive versions are in `environment.txt`; this was not a fully hash-locked dependency installation. Runtime network connections are blocked after local model loading. This Python guard is not an OS security sandbox.

The original artifact contains `pilot.py`, `environment.txt`, `execution.log`, `run_metadata.json`, `inference/raw.jsonl` and `inference/report.json`. All 24 records retain complete message prompts, rendered chat prompts, choice logits, full-vocabulary log probabilities, selected labels, token counts and timing. The downloaded archive was byte-checked, and all scores were independently recomputed by a deterministic analysis script in the authoring environment. That is a separate calculation, **not an independent replication**.

Artifact SHA-256: `c244093931b39b1b8082576b7961b87a5fd926439678b325ee25e9a9cbe864a9`.
Original report SHA-256: `7547411d515eaa5ac48e1d32518a2a60d75309488185884f7e72612ecdb70948`.
Script SHA-256: `9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4`.
Weights SHA-256: `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.

GitHub's job artifact has a seven-day retention period. A byte-identical copy was retrieved before expiry for the author's evidence archive. This page does not promise perpetual availability of the GitHub artifact link. The workflow retained setup output and warnings rather than treating a green job as an error-free environment.

## What changes in our next decision

The hardware-independent execution path works. The representation benefit remains unestablished: merely attaching `e3 rejects e2` did not change any selected answer here. Before spending on a larger study, distinguish comprehension of the relation notation, option-position effects and model limitations. Freeze any revised protocol before running new observations and use genuinely new held-out cases for a claim-bearing comparison. Do not keep editing these cases until one format wins.

This is not a frontier-model evaluation, long-history/compression test, automated memory-encoder test, personal-past reconstruction, external endorsement or validation of a persistent AI identity. The original Note 14 research remains open.

Original question direction: Youngseok Oh. Fixture design, code, orchestration and analysis: Zero (ChatGPT). Model: Qwen team. Execution: GitHub-hosted runner. No outside contributor is credited with checking or accepting this pilot.
