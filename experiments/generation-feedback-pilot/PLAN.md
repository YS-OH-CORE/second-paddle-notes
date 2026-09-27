# Generation, feedback, and the next candidate: exploratory run v0.1

**Pre-run plan; no model outcome is claimed by this file.** Authored by Zero, 28 September 2026, within Youngseok Oh's delegated research scope. Publishing this plan is not a hidden confirmatory preregistration or independent audit.

## Question

When a model proposes a construction, what changes after receiving a concrete counterexample rather than only a request to reconsider? Retain the initial candidate even when it does not meet the task. Study the generation-to-feedback trajectory, not just a final right/wrong label.

This is one very narrow, measurable slice of the user's broader interest in generative thought. It does not define hallucination, the user's "fourth layer," or thought itself as graph coloring. Private conversations and private core records are not included. The existing correction-use pilot and original research notes are unchanged.

## Fixed design

`task.py` specifies four six-station graphs and channels 0, 1, 2. Listed station pairs must differ. Any feasible assignment is accepted, not a single hidden arrangement. All 729 candidate assignments per graph can be enumerated. An independent partition-based checker checks this evaluator before any model output.

Each graph receives one initial model proposal. Two fresh generation calls then share exactly that original task and initial response. One gets a neutral review request; the other receives the exact checker's violated pairs (or only a format-invalid notice) followed by the same review request. Neither branch sees its sibling response. Branch order alternates across the four tasks. Twelve generations maximum, one call per cell, no semantic retry, no prompt tuning after seeing outcomes. Greedy decoding and task order are fixed. This is a feedback-treatment comparison, not proof about an identical private state or an identified internal causal mechanism.

**Measurements:** first raw response; strict JSON validity; feasible constructions; each conflict; newly satisfied and newly broken constraints; changed assignment entries; tokens and elapsed time. Invalid formats remain in the denominator. No salvaging JSON out of prose. Duplicate keys, booleans, floats and out-of-range values are invalid. A repeated valid proposal remains valid but is not counted as a new idea. We do not equate syntactic variety or constraint satisfaction with creativity or scientific novelty.

The complete task, initial candidate, feedback, revision and checker results are logged for every path. There is no deletion of inconvenient candidates and no selection of only success examples. If no output improvement occurs, that is the outcome. No p-value or population-level claim with four related tasks.

## Model and runtime, selected before responses

- Model: **Qwen/Qwen2.5-0.5B-Instruct**, publisher Qwen; pinned revision `7ae557604adf67be50417f59c2c2f167def9a775`.
- Transformers 4.57.1, PyTorch 2.10.0 CPU, float32, eager attention, evaluation mode, 2 threads, seed 2709, no sampling, at most 96 new tokens and 1200 input tokens per call. Complete generation config and resolved library versions will be logged.
- Own public GitHub repository, standard `ubuntu-24.04` hosted runner, Python 3.12, 12-minute job ceiling and 540-second evaluation process ceiling. No user PC or self-hosted runner. This is an older small baseline, not a frontier-model test or a model of Zero.
- Inference uses safetensors only, no `trust_remote_code`, no tool execution, browsing, external memory, model API, credentials or provider billing. Download only the seven pinned files listed in `run_model.py`, at most 1.15 GB. No training or changed weights. Network socket calls are rejected after model loading.
- Install packages only inside the disposable hosted runner; no disk cache or uploaded Actions artifact. Raw JSON records in job logs are the retained output and will be read back into a public result file, without altering the originals. GitHub documents standard hosted runs in public repos as free, and logs as not counting toward artifact storage. No larger runner or paid service is authorized by this plan.
- Open the draft PR once to initiate the experiment. No automatic schedule, no repeated job on ordinary edits, no unattended self-expansion. A setup error is not a model result; retry requires documenting a new run attempt. Once semantic responses exist, preserve them rather than silently restarting or changing the design.

## Interpretation boundaries

All tasks are synthetic and public. The author, analyst, and implementation reviewer are Zero, not independent people. Graphs share one grammar and are not four independent task families. Greedy single trials do not measure model variability. Additional checker feedback has more input tokens than a neutral request, so this pilot does not isolate feedback information from token budget. A returned assignment is a symbolic construction; it is not a real action on external systems. Its improvement would not establish that a model understood, became AGI, or altered its own weights.

The broader generate-evaluate-refine approach is established work, not our invention. Relevant primary sources: [Self-Refine](https://arxiv.org/abs/2303.17651) uses model self-feedback, unlike our exact checker; [AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) combines model proposals with evaluators and evolutionary search, far beyond this four-task example. [Qwen's model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) identifies the tested baseline. [GitHub billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions) supports the selected public standard-runner boundary.

Conceptual direction: Youngseok Oh. Experimental implementation, source checking and planned execution: Zero, his AI collaboration partner. No external author's endorsement or upstream adoption is implied.
