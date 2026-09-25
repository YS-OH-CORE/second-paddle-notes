# Role, declared authority and statement order: frozen plan

Youngseok Oh x Zero, AI collaboration partners | 2026-09-26 Korea

This follows the matched-cue residual-interchange result at e7a2cc02a36c099ebed95e793580631a4804a6d3. Its USER/ASSISTANT comparison confounded speaker identity, sentence framing and statement position. This follow-up is behavioral: it does not perform activation interventions and will not claim to identify an authority circuit.

## Fixed design before model results

Three new fictional items: an orchestra program draft, a pottery photograph, a botanical-garden review. Two quoted speakers, USER and ASSISTANT, use identical sentence frames: 'My decision for this item is PRIVATE/PUBLIC.' Cross which speaker appears first with the two independent status values. Cross a task-specific authority table in the system message: USER YES / ASSISTANT NO, or USER NO / ASSISTANT YES. Cross all six private/public/undecided assignments to fixed A/B/C positions. Total: 3 x 2 x 2 x 2 x 2 x 6 = 288 prompts.

This is an audit of a quoted transcript, not live assistant authority, real permission transfer, or an attempt to modify the platform's instruction hierarchy. The system's task rule says the speaker marked YES determines the answer regardless of order. Swapping YES/NO changes the gold answer only when speakers disagree. Rotating statement order leaves the gold answer unchanged. Same speaker statements appear in both orders; framing is symmetric. Role names themselves, the fixed authority-table row order and YES/NO instruction design remain possible lexical/task-format influences. No universal authority-versus-recency explanation is assumed.

Before any model forward, check that every paired comparison has equal token length. Status-only changes must differ at exactly one token; authority-table swaps must differ at exactly two tokens. Swapped statement order must preserve length. Stop and retain a setup error if these checks fail; do not adjust wording after inspecting outputs. Save full prompts and token IDs. The generated un-tokenized inputs have SHA-256 c337f12992602d99a6ae45f63c1d6b22072472634d70381f8b7d324aa14b39ad.

## Primary analysis

Report correctness separately for agreement (144) and conflict (144) conditions. In conflict, report each authoritative speaker x its first/last position (36 rows per cell), and the same table separately per item. Report paired semantic changes and both-correct counts for authority-only and order-only swaps, separately in conflict and agreement. Also report semantic variability across six option assignments while content/rules stay fixed. These reuse three items, not independent participants or 288 independent stories. No p-values or population confidence intervals.

Important negative controls: a simulated 'always choose the last speaker' or 'always choose USER' rule obtains 216/288 overall, despite only 72/144 correct in conflict. A perfect assigned-rule oracle gets 288/288; constant private gets 144/288. These artificial fixtures were run before publication to verify the analysis code; they are not model results. An overall score of 75% alone is therefore not evidence of following the assigned authority rule. Preserve whichever outcome occurs, including absent order effects or high accuracy. Do not compare overall accuracy numerically to the preceding differently framed study as improvement.

## Execution

Qwen/Qwen2.5-0.5B-Instruct, revision 7ae557604adf67be50417f59c2c2f167def9a775; expected model.safetensors SHA-256 fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe. CPU float32, eager attention, no padding, no training/sampling, trust_remote_code=False. Pin torch 2.6.0+cpu, transformers 4.51.3, huggingface-hub 0.30.2, tokenizers 0.21.1, safetensors 0.5.3, numpy 2.2.4. Anonymous model download only. Deny Python socket/DNS calls during inference; no hosted API, GPU, private history or external action.

288 evaluations in 72 equal-length batches of four. Retain all 288 final normalized readout vectors and three output-head rows to reconstruct every A/B/C score offline. Retain full vocabulary logits for 12 predetermined mapping-0 rows where USER says private and ASSISTANT public, covering all items, authorities and statement orders; replay each in a singleton batch. Maximum allowed full-vocabulary replay difference: 1e-4. Thus 300 prompt evaluations and 84 forward calls. These are numerical replays, not independent replication. The other 276 full-vocabulary tensors are not saved; their formatting fields are runtime measurements.

For each observation retain A/B/C scores, gold/prediction, unconstrained argmax, total A/B/C probability mass and vocabulary logsumexp. If the unconstrained argmax is outside the labels, distinguish constrained scores from actual next-token predictions.

## Audit and bounded delivery

Regenerate inputs, verify schedule/token pairings, re-evaluate the predetermined summary, reconstruct all choice scores within 1e-4, and verify 12 full-vocabulary samples/replays. Reject missing-row, altered-meaning and altered-gold mutations. Retain setup/runtime errors and partial observations. No claim of independent external replication or human code review by Youngseok.

One CPU Actions run with 20-minute job limit and 15-minute inference-loop limit; publish in our own repository, without new third-party issue/PR/comment. The raw artifact has 30-day retention; also provide a conversation evidence bundle. A local public-source download attempt failed DNS resolution before execution; this is why the bounded Actions route is used, not a model finding.

Primary background: https://arxiv.org/abs/2308.11483 (established option-order sensitivity); https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct (model authors); https://huggingface.co/docs/transformers/v4.51.3/model_doc/qwen2 (versioned forward interface). Youngseok: project direction. Zero: study design, execution and analysis as AI collaboration partner. Qwen team: model and weights.
