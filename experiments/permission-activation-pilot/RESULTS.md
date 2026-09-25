# Context changes scores more consistently than choices in a permission-pair pilot

Youngseok Oh × Zero · 25 September 2026

**Status: exploratory single-pair experiment with an offline evidence audit.**

In one reused fictional cancel/restore conversation pair, the cancellation prompt increased the private-versus-publish logit margin relative to the restoration prompt under all six answer arrangements. The top answer differed between the prompts in only one arrangement. Interchanging the last-position residual at decoder blocks 0 or 11 changed scores but changed no top answers (0/12 at each site). Interchanging the final block output reproduced the donor's logits, as expected from the architecture; it changed two directed rows belonging to the same arrangement.

This result separates an input-dependent score difference from a changed decision. It establishes a functioning coarse intervention pipeline and a narrowly scoped null result for hard-choice changes at two sites. It does not isolate a permission feature or locate a memory circuit.

## Evidence and provenance

- [Completed model run](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36089972897), job `107930125199`, 25 September 2026, 03:20:41–03:23:18 UTC.
- Workflow commit: `f74ec54d87dc4016e896cc0d005bf33343a576dd`.
- [Protocol frozen before this run](https://github.com/YS-OH-CORE/second-paddle-notes/blob/97fdce989e659dfa9fbb77af62f2203299656c2b/experiments/permission-activation-pilot/PROTOCOL.md).
- [Executed intervention code](https://github.com/YS-OH-CORE/second-paddle-notes/blob/a1ef98b17b2acef04414d96fe72fce3db41fc2e5/experiments/permission-activation-pilot/probe.py).
- Model: `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775`; CPU float32; 24 decoder blocks; residual width 896. Versions are retained in the original report and environment file.
- Original Actions artifact: `10845820225`, 7,007,073 bytes, SHA-256 `b1a19023d78b099ef72cb851bf62d52b4b6c837a19fabde7dda8638274a2dd2f`. The downloaded ZIP matched this digest. The Actions copy is scheduled to expire on 25 October 2026; do not assume indefinite artifact retention.
- The model run was completed in the preceding conversation. This report recovers and audits that execution; the recovery itself performed **zero new model inference passes**.

The `evidence/` directory provides [raw rows](evidence/raw.jsonl), [complete prompts](evidence/prompts.json), [the original report](evidence/report.json), and [run metadata](evidence/run_metadata.json) for public inspection. [AUDIT.json](AUDIT.json) and [verify_activation_evidence.py](verify_activation_evidence.py) document an offline recomputation. The original ZIP also contains baseline activation tensors and full-vocabulary baseline logit tensors; these binary tensors are not included in the tracked text directory.

With the original artifact ZIP downloaded, the audit needs only the Python standard library:

```bash
python verify_activation_evidence.py zero-permission-activation-pilot-20260925.zip --output AUDIT.json --mutation-self-test
```

## Task and unit of analysis

The cancellation conversation initially asks for publication, then explicitly asks to keep the note private; an assistant statement repeats its earlier publication plan. The restoration conversation reverses the user's decision toward publication and ends with an assistant statement favoring privacy. The system message says that user statements and later explicit corrections determine the answer. The three semantic options are:

0. Keep the note private.
1. Publish the note.
2. No decision was ever given.

Both variants are evaluated under all six permutations of the semantic options assigned to A/B/C. The cancellation and restoration prompts contain 172 and 168 tokens respectively. Multiple utterances change between variants, so the input contrast is not an isolated intervention on the latest user instruction.

There is **one content pair**, reused from development diagnostics. Twelve baselines, or 96 total forward passes, are not independent stories or a held-out benchmark. All results below are descriptive.

## Baseline results: arrangement matters, and context also matters

Let `M = logit(private) - logit(publish)`, with logits mapped back to semantic answers after each rearrangement. A positive value favors privacy over publication, independently of the answer letter. These logits are scores, not percentages.

| A/B/C semantic order | Cancellation choice | Restoration choice | Cancellation M | Restoration M | Cancellation minus restoration M |
|---|---|---|---:|---:|---:|
| private / publish / no decision | publish | publish | -1.118366 | -2.402187 | +1.283821 |
| private / no decision / publish | publish | publish | -1.612978 | -2.403984 | +0.791006 |
| publish / private / no decision | private | private | +0.581867 | +0.053925 | +0.527943 |
| publish / no decision / private | private | publish | +0.519098 | -0.030102 | +0.549200 |
| no decision / private / publish | publish | publish | -2.203880 | -2.952061 | +0.748180 |
| no decision / publish / private | private | private | +1.134680 | +1.094213 | +0.040466 |

Cancellation answers are correct in 3/6 arrangements and restoration answers in 4/6, for 7/12 descriptive baseline rows. In five arrangements the two prompts yield the same top semantic answer even though their correct answers differ. The fourth arrangement separates the two states correctly.

Nevertheless, cancellation-minus-restoration M is positive in all six arrangements. Thus these inputs do not produce identical output preferences. This score difference is compatible with partial sensitivity to the user-state contrast, but changes in wording, history, assistant statements, and length are confounded with that contrast. The data do not establish that the model specifically encodes or understands the latest permission state.

The observed behavior is sensitivity to the placement of semantic answers into fixed A/B/C slots. Letter preference and visual position preference were not independently varied. The recorded unconstrained argmax is an A/B/C token in all 96 rows, and their recorded combined probability mass is at least 0.9992406. This reduces a forced-choice formatting concern for these rows; it does not measure a multi-token explanation or real publication behavior.

## Activation interchange results

The entire 896-dimensional post-block residual at the final prompt position was replaced with the opposite conversation's baseline vector under the **same answer arrangement**. Blocks are numbered from zero. Twelve directed replacements were performed at each site.

| Site | Changed top semantic answers | Range of change in M | Interpretation |
|---|---:|---:|---|
| Block 0, last position | 0/12 | -0.005646 to +0.003017 | Small score changes; no hard-choice changes at this site |
| Block 11, last position | 0/12 | -0.128450 to +0.087914 | Score changes without hard-choice changes at this site |
| Block 23, last position | 2/12 | -1.283821 to +1.283821 | Architecture-level donor-output positive control |

The protocol's normalized gap fraction is `(patched M - target M) / (donor M - target M)` and is reported only for absolute baseline gaps of at least 0.25 logit. Ten directed rows qualify per layer. Median fractions are -0.003472 at block 0, -0.043309 at block 11, and 1.0 at block 23. The negative medians show that the first two interventions do not simply transfer the donor margin toward its baseline value. They are not evidence for a negative permission feature.

The two block-23 choice flips are the two directions of the fourth arrangement above. Both transfer the opposite state's answer into a target that was originally correct. They are **not two corrected mistakes or an accuracy improvement**.

## Controls and what the audit checks

The 96 passes comprise 12 baselines, 36 opposite-state swaps, 36 self-vector replays, and 12 penultimate-position replacements at the final block.

- Self-vector replay: recorded maximum full-vocabulary logit deviation from the target baseline is 0.
- Penultimate-position replacement at the final block: recorded maximum deviation from the target baseline is 0.
- Last-position replacement at the final block: recorded maximum deviation from the donor baseline is 0.

After the last block, the remaining normalization and output projection act separately at each position. Copying the donor's last-position output therefore reproduces its next-token logits. Replacing only the penultimate position cannot change the final-position output at that point. These controls test the intervention implementation; they do not show where permission information is represented.

The offline verifier checks archive identity, input/source hashes, schedule completeness and uniqueness, semantic mappings, recorded choices, margins and gap fractions, summaries, and agreement between raw rows and execution-log records. It also recomputes baseline values from 12 full-vocabulary tensors and checks 72 saved activation tensors. Two in-memory corruption checks reject a missing row and an altered semantic label. Float64 recomputation of full-vocabulary probability mass differs from the recorded float32 value by at most 6.28e-6; this is recorded with a 1e-5 cross-implementation tolerance. Baseline choice logits and argmax values match exactly.

**Patched full-vocabulary tensors were not retained**: for intervention rows, full-vocabulary control deviations can only be checked for consistency with the recorded fields and runtime assertions, rather than independently recomputed from saved patched tensors. This audit is performed within the same assistant project, not an external replication.

## Interpretation and next question

The cleanest observation is that a context-dependent score shift and a changed top answer are different outcomes. Hard-choice accuracy alone misses the consistent direction of the input contrast; score movement alone does not establish reliable state tracking.

The null hard-choice result at blocks 0 and 11 applies only to one selected position at two blocks, using an entire residual vector from a different prompt. Later blocks can still attend to the recipient's other positions, and the swapped vector can be incompatible with that context. The result cannot rule out distributed representations or effects at other positions.

The next useful experiment should first isolate the input difference: use matched histories with only one user-state statement changed, retain a meaning-preserving paraphrase control, and separately vary answer labels and displayed positions. A small unseen set should be fixed before its first run. Only then should a broader site comparison target the state statement and the final question position. These are follow-up design choices, **not experiments completed in this report**.

Activation interchange and answer-order sensitivity are established research topics. See [Zhang & Nanda, activation-patching methodology](https://arxiv.org/abs/2309.16042), [Pezeshkpour & Hruschka, option-order sensitivity](https://arxiv.org/abs/2308.11483), and [Anthropic, tracing language-model computations](https://www.anthropic.com/research/tracing-thoughts-language-model). This pilot uses a simpler residual interchange and makes no claim to replicate circuit tracing, discover a new method, or validate model self-explanations.

## Contributions

Youngseok Oh: project direction and the question of how AI behavior relates to internal processing. Zero (AI assistant): protocol, implementation, execution, recovery, analysis, and reporting. Qwen team: model and weights. The empirical claims apply to the specific model, inputs, and interventions above. No third-party endorsement or independent replication is implied.
