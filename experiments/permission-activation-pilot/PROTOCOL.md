# Permission-pair residual interchange: exploratory protocol v1

Youngseok Oh × Zero | 25 September 2026

## Question and status

Can a small, reproducible internal-state intervention be connected to the existing memory pilot without treating a model's self-description as evidence of its mechanism? This is **an instrumentation and exploratory mechanistic pilot**, not a held-out benchmark, novel activation-patching method, discovered memory circuit, or proof of consciousness.

Youngseok's current direction is to understand AI behavior and internal phenomena, not only contribute software fixes. The chosen operational question concerns the gap between a stated user decision and a model's next-token answer preference. This is Zero's experimental interpretation of that direction, not a quotation of a theory already established by Youngseok.

The prior answer-order diagnostic reused eight fictional cases and found option-order sensitivity. We deliberately reuse its **permission_cancel / permission_restore** pair in the chronology view only. Selection is informed by the prior development findings. This pair cannot become held-out by calling the present protocol frozen.

## Frozen inputs and intervention grid

- Model: Qwen/Qwen2.5-0.5B-Instruct, revision `7ae557604adf67be50417f59c2c2f167def9a775`, weight SHA-256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
- Existing fixture script SHA-256 `9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4`. Original statements, system message, question, and answers are unchanged. The two conversations are not a single-token or equal-length manipulation.
- Exhaust all six A/B/C answer orders; align outcomes by semantic answer, not letter. Two prompt variants × six orders = 12 baselines, **one content pair**, not 12 independent stories.
- Capture post-decoder-block residual vectors at zero-based blocks **0, 11, 23**, final and penultimate prompt positions. These sites are chosen before this run. No adaptive layer search.
- For each baseline target and each selected block: replace its final-position residual with the opposite conversation's vector under the same answer order (36 passes); replay its own vector at the same site (36 self-controls).
- At the last block only, replace the penultimate-position vector with the opposite conversation's penultimate vector (12 wrong-position controls).
- **96 forward passes total:** 12 baseline + 36 donor swaps + 36 self-controls + 12 wrong-position controls. One deterministic CPU float32 run per cell; no sampling, fitting, answer-based retries, or extra sites after viewing results.

This swaps the **entire 896-dimensional vector**, not an isolated intent feature. At intermediate blocks the remainder of the target prompt is still available through later attention. The intervention could transfer many correlated features, including wording, position, prompt length or output preference. It does not by itself identify why an unmodified model makes a mistake.

## Metrics and fixed controls

Record full prompts/token IDs, A/B/C logits, semantic choice, unconstrained argmax and A/B/C probability mass. Primary continuous contrast: logit(keep private) minus logit(publish). Record the intervention shift and donor-minus-target baseline gap. Report a gap fraction only when the absolute baseline gap is at least **0.25 logit**; do not discard other cells or present undefined ratios as zero. Use descriptive per-site results, not population significance.

Self-vector replay should preserve the full next-token logit vector within maximum absolute error **1e-4**. Replacing the penultimate output at the final block should leave the final-position logits unchanged because no later cross-position mixing remains. Replacing the final output at that same block should recover the donor logits within the same tolerance. **This last result is an architecture-level positive control, not discovery of a causal memory circuit.**

Any control/runtime failure stops the run and preserves completed rows. A setup-only correction may be made with the failure retained; prompts or sites are not tuned to obtain a desirable result. Null, tiny, reversed or option-dependent intermediate effects are acceptable observations. Parameter versions and hook removal are checked; no weight update is performed.

## Evidence and scope

Retain code, protocol commit, environments, raw observations, baseline activation and logit tensors in safetensors, and source/model identities. Do not upload the model weights. All text is existing fictional test data; no real user history, login, API key, personal computer, model endpoint or tool action is involved. Public sources and weights are downloaded during setup; inference uses local weights with a Python socket guard, not an OS network sandbox.

One ordinary GitHub CPU job with a finite timeout. No recurring task or ongoing autonomous process. No external issue comment or claim of authority is warranted solely by a passing instrumentation check.

## Prior methods and interpretive boundary

Activation interchange is existing interpretability work, not ours. Zhang and Nanda discuss sensitivity to metrics and corruption choices: https://arxiv.org/abs/2309.16042. Their findings motivate retaining controls and not overinterpreting a single patching result. Anthropic's https://www.anthropic.com/research/tracing-thoughts-language-model explains why visible self-explanations and internal mechanisms should not be identified with one another; this pilot is not their circuit-tracing method or a replication of their findings.

Pinned model configuration: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/7ae557604adf67be50417f59c2c2f167def9a775/config.json.

Prior development report: https://github.com/YS-OH-CORE/second-paddle-notes/blob/dbd48bbb31b0e03f2855f196e79bc809822fdd38/experiments/memory-cpu-pilot/OPTION_ORDER_REPORT.md.

Question direction and public collaboration: Youngseok Oh. Protocol, code, execution and analysis: Zero (AI assistant). Weights: Qwen team. No endorsement or independent replication is implied.
