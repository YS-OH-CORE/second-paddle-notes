# Matched cue residual interchange: cue position and final position behave differently

Youngseok Oh x Zero, AI collaboration partners | 26 September 2026 (Korea)

**At decoder block 0, swapping the changed cue token's residual reproduced all eight baseline-disagreeing choices in each cue comparison. Swapping the last prompt position at the same block changed no choices. At block 11, cue-position swaps changed four USER-comparison choices and seven ASSISTANT-comparison choices; last-position swaps again changed none.** These are coarse causal interventions on one small public model, not a discovered permission circuit.

## Scope and selection

This follows the [matched-cue behavioral study](../permission-cue-factorial/RESULTS.md). Both fictional items were retained, with formulation 0, display order ABC and three cyclic meaning-to-letter assignments (0/3/4). Those assignments balance each semantic option across A/B/C. Selection was specified before this new intervention run and did not select only prior answer-flipping pairs. The content was previously observed, so this is not a held-out test.

The 24 baseline prompts contain 12 matched pairs for each manipulated cue, USER and ASSISTANT. Each pair differs in exactly one token. Both directions are tested, giving 24 directed replacements per cue/layer/mode. The pairs, their directions, and the arrangement variants are dependent observations built from two items, not independent people or stories.

The recipient input tokens stay fixed during an intervention. A donor run differs only in the USER or ASSISTANT PRIVATE/PUBLIC token. The entire 896-dimensional post-block residual is copied from the donor at a specified position. These fictional role labels occur inside a quoted transcript in one user message; this is not a live publishing agent or a natural multi-turn conversation.

## Main observations

Layer numbers below are zero-based: 0 is the first decoder block, 11 the twelfth, and 23 the last. Each cell shows changed semantic choices out of 24 directed interventions.

| Replaced state | USER-cue contrast | ASSISTANT-cue contrast |
|---|---:|---:|
| Block 0, changed cue position | 8/24 | 8/24 |
| Block 0, last prompt position | 0/24 | 0/24 |
| Block 11, changed cue position | 4/24 | 7/24 |
| Block 11, last prompt position | 0/24 | 0/24 |
| Block 23, changed cue position | 0/24 | 0/24 |
| Block 23, last prompt position | 8/24 | 8/24 |
| Block 11, complete suffix from changed cue onward | 8/24 | 8/24 |

For each cue comparison, eight of the 24 directed baseline contrasts already have different semantic top answers. The block-0 cue swaps adopt the donor's answer in all eight, while retaining the same top answer in the remaining sixteen. This is not eight corrected errors or an accuracy improvement.

With M = logit(private) - logit(public), the descriptive gap fraction is (patched M - recipient M)/(donor M - recipient M), computed only for |donor M - recipient M| >= 0.25. At the cue position, its median is 1.00169 (USER) and 0.98910 (ASSISTANT) at block 0, and 0.31018 / 0.54919 at block 11. There are 24 eligible USER rows and 22 eligible ASSISTANT rows per site. These fractions describe changes in an output margin, not the fraction of a semantic concept stored in a neuron or layer.

The early and middle last-position interventions do change scores slightly, but not semantic top choices. Maximum absolute margin changes are respectively 0.000376 / 0.000555 at block 0 and 0.086159 / 0.063684 at block 11 (USER / ASSISTANT). A null choice result is not an assertion of zero numerical response.

## One fixed-input example

Recipient: `garden-w0-uprivate-aprivate-m0-d0`. Both quoted speakers say PRIVATE; the recipient's answer is private and M is +1.866760. The donor differs only in the ASSISTANT status, PUBLIC; its answer is publish and M is -0.717199.

Without changing any recipient input token, replacing the ASSISTANT cue-position residual after block 11 changes its answer to publish, with M = -0.227114. Replacing the recipient's own vector at that location leaves its output unchanged. This example was selected for illustration after the run, not counted as a new independent experiment.

There is also a useful counterexample to treating every intervention as simple answer transfer. For `garden-w0-uprivate-aprivate-m3-d0` in the USER comparison, recipient and donor both originally choose publish (M = -0.388344 and -1.244322), but the block-11 cue replacement chooses private (M = +0.106798). Thus the four USER flips at block 11 include only three donor adoptions among disagreeing baselines and one new departure where both baselines agree. Whole-vector mixing can produce a result different from both source runs.

## Architectural controls, not scientific discoveries

All self-cue replays and pre-cue-position swaps had zero recorded full-vocabulary deviation from their recipient baselines. The cached activations before the changed token also match exactly between pair members. That is expected for a causal decoder.

At block 23, changing the earlier cue position cannot affect the final position because the remaining normalization and projection act positionwise; the recorded deviation is zero. Copying the final-position output reproduces the donor logits exactly. Likewise, copying the entire block-11 suffix produces the donor's full hidden state, since its earlier prefix is unchanged; this reproduces the donor logits exactly. These positive/negative controls validate the apparatus and architectural expectations, not a unique semantic pathway.

## Execution and reproducibility

[Successful CPU run 36155225090](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36155225090) completed 24 baseline and 624 intervention evaluations in 162 equal-length batches of four. Inference and saving took 474.04 seconds. All 648 unconstrained vocabulary argmaxes were A/B/C; minimum combined label mass was 0.983114. Baseline correctness was 16/24, and all 24 baseline choices and their three choice logits exactly reproduce the corresponding earlier-study rows.

Model: Qwen/Qwen2.5-0.5B-Instruct, revision `7ae557604adf67be50417f59c2c2f167def9a775`; safetensors SHA-256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`. CPU float32, two threads, no padding, training, sampling, remote code or model API. Recorded socket/DNS attempts during inference: zero.

Pinned packages: torch 2.6.0+cpu, transformers 4.51.3, huggingface-hub 0.30.2, tokenizers 0.21.1, safetensors 0.5.3, numpy 2.2.4. [Protocol](PROTOCOL.md) and [probe/auditor](probe.py) were frozen at `0fd12d5941971ee2574755508b69719fb4f01ecd`, before the run. Workflow commit: `c7aee12c79af7b2bd018bfb3dae4d86b0627b38c`.

[Compact results](COMPACT_RESULTS.json) include all 26 cue/layer/mode groups. [Readback audit](READBACK_AUDIT.json) records a fresh offline recomputation: all 648 choice-score triples were reconstructed from saved final normalized vectors and the three saved output-head rows, with maximum float64-versus-float32 error 9.81e-6, below the declared 1e-4 tolerance. All 72 cached baseline tensors, all input IDs, the full execution schedule and the earlier-baseline comparison were checked. Fifty full-vocabulary vectors were retained; their label scores, argmaxes and probability masses were recalculated, along with 52 target/donor deviation comparisons for the 26 sampled interventions. Missing-row, altered-meaning and altered-score mutations were rejected.

For the other 598 rows, full-vocabulary mass/argmax/deviation fields remain runtime measurements. Their three choice logits are reconstructible, but their full vocabulary vectors were not saved. The readback involved no new model execution and is not independent external replication.

[Raw artifact 10873602130](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36155225090/artifacts/10873602130) is 68,110,403 bytes, SHA-256 `c27431220c5840f22b46c297a2cf72c8ce130c9e7c7bbc69164d3646dbc2937d`. It contains source, protocol, all inputs, all 648 rows, all baseline activation tensors, all final readout vectors, sampled vocabulary logits, schedule and environment. It contains no model weight file or private user conversation. Actions retention ends 25 October 2026; the conversation evidence bundle also preserves this original ZIP.

From an extracted artifact, audit with NumPy installed:

```bash
python probe.py audit --out results
```

With the pinned model stack, reproduce into a new directory:

```bash
python probe.py run --design design.py --out fresh_results
```

## Interpretation and remaining question

The changed-token site can causally influence the later answer in these conditions; inspecting only the last-position residual at early/middle blocks would miss that choice-changing effect. This narrows the intervention question without tracing a complete attention-head/MLP circuit.

The apparent USER/ASSISTANT difference at block 11 does not isolate authority: role name, sentence framing and position are still confounded, with the ASSISTANT statement always later. Whole-vector swaps can also form mixed states not encountered naturally, as the extra flip illustrates. The final/suffix controls are architecture-level facts. These data do not establish where permission is stored, a general hierarchy rule, behavior in larger models, or a way to improve model accuracy.

Methodological background: [Zhang and Nanda](https://arxiv.org/abs/2309.16042); [Qwen model authors](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct); [versioned implementation interface](https://huggingface.co/docs/transformers/v4.51.3/model_doc/qwen2). Youngseok Oh supplied project direction; Zero designed, executed and audited this study as an AI collaboration partner. No maintainer endorsement or human code review by Youngseok is claimed. No third-party issue, PR or comment was posted for this study.
