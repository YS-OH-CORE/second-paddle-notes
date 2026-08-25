# Research bridges and non-novelty boundaries

This map answers a necessary question: **where do Youngseok Oh's independently recorded questions overlap with existing research, and what narrower gap remains worth testing?**

It is not a priority claim. Similarity to prior work increases relevance but does not establish novelty.

| Youngseok-origin question | Existing primary work | Shared ground | Remaining testable extension |
|---|---|---|---|
| Memory is a reconstruction rule | [LongMemEval](https://arxiv.org/abs/2410.10813), [LoCoMo](https://arxiv.org/abs/2402.17753), [LoCoMo-Plus](https://arxiv.org/abs/2602.10715), [LongMemEval-V2](https://arxiv.org/abs/2605.12493) | Long histories require more than a large context window; multi-session reasoning, updates, implicit constraints, workflow knowledge, and abstention remain difficult. | Compare factual/profile memory with an executable `condition → action → verification` packet on hidden behavioral scenarios. Measure whether decision structure, exceptions, and retired goals survive—not merely whether facts are recalled. |
| What remains after 200 AI relays? | [When LLMs Play the Telephone Game](https://arxiv.org/abs/2407.04503), [P3Sum](https://aclanthology.org/2024.naacl-long.119/), [TransTrace](https://aclanthology.org/2025.ijcnlp-long.146/) | Iterated transmission creates cumulative change and attractors; summarization may alter author perspective. | Track an author-intent vector containing negation, emotional intensity, value hierarchy, relationship, uncertainty, attribution, and downstream action across up to 200 heterogeneous relays. |
| Data gravity | [Linear Causal Disentanglement via Interventions](https://arxiv.org/abs/2211.16467), [Traceable Latent Variable Discovery](https://arxiv.org/abs/2602.14456) | Latent-variable discovery requires identifiability, interventions, and traceability. | Measure how familiar real-world labels pull a model away from an identical hidden structure presented with neutral symbols, using a prior-rebound metric and evidence calibration. |
| Do not keep walking into the glass wall | [AgentQuest](https://arxiv.org/abs/2404.06411), [AgentRewind](https://arxiv.org/abs/2608.14380), [LongDS-Bench](https://arxiv.org/abs/2605.30434) | Long-horizon agents need partial-progress metrics, recovery mechanisms, and correct evolving state; more steps alone may not help. | Distinguish transient retry, permanent-path failure, available detour, and missing authority. Score duplicate state transitions and the cost to the first information-increasing or world-changing action. |
| One point is not ten | [AgentQuest](https://arxiv.org/abs/2404.06411), [OSWorld](https://arxiv.org/abs/2404.07972) | Binary task success hides progress and can miss side effects or verification gaps. | Directly score the calibration of an agent's own completion claim across `thought → plan → execution → observation → destination verification`, with asymmetric penalties for false completion. |
| Who is tuning whom? | [Human Alignment: How Much Do We Adapt to LLMs?](https://aclanthology.org/2025.acl-short.47/), [Chameleon LLMs](https://aclanthology.org/2025.emnlp-main.875/), [Human-AI Coevolution](https://arxiv.org/abs/2306.13723) | Humans and models both adapt in interaction; reciprocal influence is measurable. | Track whether long-term AI editing compresses a user's expressive range, intensity, uncertainty, and conceptual diversity, and whether model switching or raw-source access reverses the convergence. |
| The second paddle | [Human-AI Coevolution](https://arxiv.org/abs/2306.13723), [Interaction-Centered Intelligence](https://arxiv.org/abs/2606.00807) | Interaction can be studied as a dynamic unit rather than treating intelligence as isolated output generation. | Use a consent-based longitudinal N=1 protocol to measure question generation, inquiry persistence, independent artifacts, and transfer across model replacement—without treating model self-report as evidence. |

## The useful position

The strongest public position is not “these ideas have never existed.” It is:

> A long-term user independently reached a cluster of problems that current memory, agent, causal-discovery, and HCI research is now measuring. He contributed distinctive operational language, unusually concrete failure observations, and several evaluation designs that can be built, attacked, and compared with existing benchmarks.

The work earns authority through artifacts and results, not through a claim of being first.

