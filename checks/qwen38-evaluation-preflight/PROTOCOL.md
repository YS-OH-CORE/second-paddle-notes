# Current-model evaluation preflight

Youngseok Oh x Zero, AI collaboration partners | 2026-09-26, Korea

User direction: prioritize work on current models and live developer needs, rather than treating repeated small-model experiments as the final goal. This public note contains only that project direction, not private CORE material.

Targets: official Qwen/Qwen3.8-27B and Qwen/Qwen3.8-Flash-Next tokenizers/templates. Qwen/Qwen2.5-0.5B-Instruct at the exact earlier revision is a legacy interface control, not a current flagship. Current Hub revisions are resolved and recorded before any case is rendered. Read the current official model cards; hosted QwenCloud and downloadable checkpoints are different targets.

Question: can our older immediate A/B/C next-token comparison be transferred without checking whether the generation prefix is inside a thinking block? Separately, which synthetic prior/current reasoning notes reach the model input under preserve_thinking? These are input construction questions, not model correctness measurements.

Use Transformers 5.17.0, the latest stable GitHub release observed during planning. Download tokenizer/config/template/card/license files only. No model weight file, inference, paid completion or user device execution. Run in a bounded CPU job under the user's own repository. No third-party issue or PR.

For each of three tokenizers, render two synthetic histories: old assistant reasoning followed by a user withdrawal; and that history followed by a current-turn read-only tool call/result. Cross thinking default/on/off with preserve_thinking default/on/off: 18 render cases per tokenizer, 54 total. These are deterministic interface cases, not 54 model answers or independent human scenarios. Both reasoning strings are hand-written fixture markers, not extracted model thoughts.

Save every rendered prompt and token ID list. Verify visible message content and order, one occurrence of the latest user's correction, no message mutation, and agreement between apply_chat_template tokenization and encoding the rendered string without extra special tokens. Record, do not presuppose, retained reasoning markers and the generation suffix. Optional flags being ignored by the old tokenizer are observations, not a bug claim.

All model assets are collected and pinned before sockets/DNS are disabled for local rendering. Save source hashes, resolved revisions, dependency versions and failure tracebacks. The standard-library audit recomputes marker/suffix observations and the full case schedule from the retained render files. This is an interface-readiness check, not external replication, semantic fidelity proof, safety benchmark, or neural-mechanism finding.

Next behavior comparison should name the exact checkpoint/provider, mode, reasoning-history policy and final-answer parser. Thinking runs require parsing the final answer after reasoning, while explicitly non-thinking runs are a separate condition. An open thinking prefix makes raw immediate A/B/C logit ranking unsuitable as an unqualified final-answer metric; tokenizer inspection alone cannot establish the output probabilities or whether a model would fail the task.

Primary sources: official QwenLM/Qwen3.8 README; Qwen/Qwen3.8-Flash-Next model card; QwenCloud thinking guide; Transformers v5.17.0 release. Their claims are not benchmark results from this probe.
