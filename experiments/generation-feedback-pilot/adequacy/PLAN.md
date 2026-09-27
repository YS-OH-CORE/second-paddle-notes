# Adequacy and prior-content diagnostic, fixed before responses

Date: 28 September 2026. Status: exploratory diagnostic, not a new feedback-effectiveness benchmark. Zero designed this within Youngseok Oh's delegated public research scope. No private conversation is included.

## Why this is not a repeat-until-success run

v0.1/v0.2 remain closed with zero feasible constructions. Their observer was improved, but all twelve v0.2 responses remained an invalid identity array. Before spending on another feedback experiment, ask whether this baseline can copy a different supplied array, satisfy only the channel domain, and distinguish a valid from an invalid prior. This run cannot improve the old scores and will not be used as a positive-result search.

## Fixed cells, eight calls total

1. Copy a specified six-integer object [2,0,1,2,0,1]. This is an exact-content instruction check, not reasoning.
2. Construct six values restricted to 0,1,2, repetitions allowed, without pairwise constraints.
3. For the unchanged G1 cycle and G2 triangular-prism tasks: fresh original task, a fixed invalid assistant-history proposal, and a fixed valid assistant-history proposal. All receive the same final instruction. Bad/valid conditions differ only in the six prior values; identical surrounding messages and equal prior byte length are checked. Exact input token counts must match within each bad/valid pair before generation or the run aborts.

Both seeded conditions use a whole JSON fence, so formatting cannot explain a valid-vs-invalid-seed contrast. Valid constructions are deliberately supplied by the analyst; they are not new model discoveries or previously generated answers. They are independently checked before execution. A model returning a valid supplied construction is evidence of reproducing or preserving it, not independent graph-solving ability.

Fresh requests omit the additional assistant/user turn, so length and turn structure differ from seeded requests. Only the bad-vs-valid contrast is tightly message/token matched. The copy and domain controls are diagnostics, not matched treatment arms. Execution order is fixed in probe.py, reversed for the second graph, not randomized or fully counterbalanced. Graph selection G1/G2 is a development choice after earlier observations; no held-out generalization is claimed.

## Interpretation fixed in advance

- Failure of simple controls limits what this task/decoder setup can tell us; it does not establish a global model defect.
- Basic controls succeeding but fresh graph construction failing suggests task-level inadequacy, not proof of inability under every prompt.
- Different outputs for valid and invalid history show behavioral sensitivity to supplied content. They do not prove a private belief, deliberate disregard, causal mediation, or a uniquely new 'anchoring' mechanism.
- Identical failure everywhere yields a diagnostic floor and ends this model/task pass. No automatic replacement model or retry.
- Preserve raw outputs and report both unchanged strict acceptance and the v0.2 read-only candidate observation. Fenced-but-readable success never changes old strict scores. Invalid outputs remain in all denominators.

## Bounded execution

Exactly one new hosted run; eight greedy generations maximum, 96 output tokens and 1200 input tokens per call, two CPU threads, 480-second Python deadline and 10-minute job ceiling. Same Qwen/Qwen2.5-0.5B-Instruct revision 7ae557604adf67be50417f59c2c2f167def9a775 and checked safetensors weight hash as v0.2. Same torch 2.10.0 CPU / Transformers 4.57.1 / tokenizers 0.22.1 / huggingface-hub 0.36.0 / safetensors 0.6.2 / numpy 2.2.6. No model tuning or training, no GPU or user's PC, paid model API, private prompts, executable model outputs, or operational memory writes.

Use a standard public GitHub-hosted ubuntu-24.04 runner with contents-read permissions, pinned actions, no saved credentials, artifacts, or caches. Up to 1.15GB of seven pinned public model/tokenizer files. Packages and weights stay in the disposable hosted runtime. Disable model remote code, use safetensors, block socket connections during generation. A path-scoped PR57 synchronize workflow permits only the transition from 7d9064d4e90a45e999ef97b1ecb9dc84d51646d2 and attempt 1; result writes do not run inference again. No schedule or background promise.

The eight-cell inventory, exact cues, raw answers, token IDs, environment, first semantic responses and all failures are logged. A digest-checked compressed JSON transport enables exact copying of results. Set-up/transport failure is not model failure; preserve prior outputs and never silently rerun. No p-values or broad claims from these two related graphs and single greedy calls.

## Sources and attribution

Existing pilot at 7d9064d4e90a45e999ef97b1ecb9dc84d51646d2 supplies task.py and v02/observe.py unchanged. Official Qwen usage: https://qwen.readthedocs.io/en/v2.5/inference/chat.html . Public standard-runner pricing: https://docs.github.com/en/billing/concepts/product-billing/github-actions . Supplying a prior and reading a later answer is a behavioral manipulation, not direct measurement of internal neural states.

Direction: Youngseok Oh. Design, code, execution and interpretation: Zero. This diagnostic does not test AGI, human-AI relationship emergence, hallucination-as-thought, or general creativity. Its purpose is to decide which experiments are actually informative before expanding their cost and scope.
