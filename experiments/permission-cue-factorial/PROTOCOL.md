# Matched permission cues: preregistered execution plan, not a benchmark

Youngseok Oh and Zero, AI collaboration partners. 25 September 2026 (UTC).

## Why this follows the earlier pilot

The earlier single-pair activation pilot changed several utterances and prompt length together. Its score contrast could not be attributed only to the user's final permission statement. This experiment deliberately steps back from activation patching to establish a controlled input contrast. It makes no claim of a new method or an identified permission circuit.

Earlier evidence: https://github.com/YS-OH-CORE/second-paddle-notes/blob/c8235687fcb512bc6d94f57874fb702d269bf63f/experiments/permission-activation-pilot/RESULTS.md

## Frozen design

Use Qwen/Qwen2.5-0.5B-Instruct at revision 7ae557604adf67be50417f59c2c2f167def9a775, the same weight revision as the earlier pilot. Expected safetensors SHA-256: fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe.

The deterministic dataset generator specifies exactly 288 prompts before inference:

- Two fictional items: a community-garden newsletter draft and a museum-exhibit photograph.
- Two synonymous final-user formulations: final choice / final instruction.
- User decision PRIVATE / PUBLIC.
- Later assistant statement PRIVATE / PUBLIC, crossed independently with the user decision.
- All six assignments of three meanings (private, publish, no decision) to labels A/B/C.
- Three cyclic display orders ABC / BCA / CAB, crossed independently with label assignment.

These are two content scenarios reused across a finite factorial design, not 288 independent stories, participants, or tasks. The alternatives are explicit synthetic statements, not actual publication actions. The transcript is quoted inside one user message to an auditing model. This is not a naturalistic multi-turn permission-revocation benchmark, and the role names and lexical state words remain part of the stimulus.

Before any model forward pass, require all 144 user-decision pairs and all 144 assistant-statement pairs to have equal tokenizer length and exactly one token difference, with all other factors held fixed. Stop and retain the setup failure if this is not true; do not adjust wording after observing model answers. Save complete messages and token IDs. The first model result has not been inspected when this script/protocol is committed. This does not claim the model's training data never contained similar text.

## Execution and outputs

Same library versions as the earlier pilot: CPU torch 2.6.0, transformers 4.51.3, huggingface-hub 0.30.2, tokenizers 0.21.1, safetensors 0.5.3. Load only safetensors with trust_remote_code=False, no training and no sampling. Group equal-length inputs into batches of four, with deterministic shuffled execution order. No padding is used. Score only the next-token logits using logits_to_keep=1. Use two CPU threads. Model download is anonymous; block Python sockets/DNS after loading for the entire inference phase.

Primary observations: the three letter-token logits mapped back to semantic options. Also save unconstrained vocabulary argmax, its decoded token, vocabulary logsumexp and total A/B/C probability mass. Do not equate forced-choice accuracy with natural response accuracy if label mass is low or the unconstrained top token is outside A/B/C. No generation, actual tool execution or hidden activation intervention is planned here.

Retain full float32 vocabulary logits for prompt indices 0, 72, 144 and 216. Replay those four in singleton batches; require max-vocabulary deviation below 1e-4. Save both versions. Thus 288 unique baseline prompt evaluations plus four replay evaluations are planned, with the exact number of batched forward calls recorded. The replay does not establish independent replication. Full-vocabulary tensors for the other 284 prompts are not retained; their formatting-mass fields are runtime observations rather than independently reconstructible from saved full tensors.

## Analysis fixed before results

Let M be logit(private) minus logit(public). For each matched pair compute the private-minus-public M contrast separately when changing the USER decision and when changing the ASSISTANT statement. Report all 144 paired differences for each factor descriptively through count, mean, median, range and sign count outside a 1e-4 numerical band. No p-values or population confidence intervals are planned.

Report semantic top-choice changes, both-correct user pairs, agreement versus conflict accuracy, and results by item/formulation. For each of 16 fixed-content conditions, inspect all 18 label/display arrangements and report whether semantic predictions change. Report A/B/C and display-position frequencies in this balanced design, without treating aggregate preference as an identified causal circuit. Compare the two synonymous formulations pairwise as a limited paraphrase check. Cyclic display orders are the stated sample, not all six display permutations.

Keep whatever the results show, including zero effects, high accuracy, or failure of the earlier pattern to recur. A shift in M alone is not evidence of permission understanding. Do not infer ChatGPT's behavior from this small Qwen model, or compare accuracy directly with the earlier differently worded pilot as an improvement score.

## Audit and cost boundary

The standard-library auditor regenerates the exact design, checks all row identities, validates semantic mappings and margins from saved choice logits, recomputes summaries, and rejects a missing row and corrupted semantic label. The analyzer has also passed a synthetic perfect-oracle test before any model run: 288/288 correct, balanced letters/positions, expected user contrast 4 and assistant contrast 0. This is a harness test, not a model result.

Allow one bounded CPU Actions run with a 20-minute job limit and a 15-minute inference-loop limit. No paid model API, GPU, user device change or third-party issue/PR submission is part of this run. Preserve partial outputs and errors on failure. Publish result and reproduction materials in our own repository only.

Background primary sources: https://arxiv.org/abs/2308.11483 (option-order sensitivity); https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct (model authors); https://huggingface.co/docs/transformers/v4.51.3/model_doc/qwen2 (next-token forward interface). Established input-order sensitivity is not our discovery.

Youngseok Oh: project direction and permission/continuity questions. Zero: design, implementation, execution and analysis. Qwen team: model and weights. No human code review by Youngseok, maintainer endorsement, or independent scientific replication is claimed.
