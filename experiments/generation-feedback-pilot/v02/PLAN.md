# v0.2: feedback observability, not retrospective score repair

Pre-response exploratory plan, 28 September 2026. Zero's design within Youngseok Oh's delegated research scope. This is not a confirmatory preregistration, independent audit, or validation of a philosophy of thought.

## Why another bounded run

The completed v0.1 run on four small graphs delivered only `format_valid=false` because all initial proposals were fenced and contained out-of-domain values. It did not deliver the intended constraint-specific information. We retain its raw outputs, parser and all zero strict scores unchanged. This revision tests the immediate measurement bottleneck with the same baseline, rather than buying a larger model or retrying until success.

## Fixed treatment comparison

Use all four v0.1 **initial** raw responses from `../OBSERVED.json`, verified against the existing public blob, as fixed seeds. None is regenerated or selected by success. For each, start three independent calls with the unchanged original system, task, and seed, followed by one cue:

1. **coarse**: the exact v0.1 `format_valid=false` feedback and neutral review request.
2. **format_explicit**: a specific Markdown-fence observation and the same neutral review request.
3. **layered**: the same fence observation plus the actual out-of-domain entries, allowed values, station/value distinction, and equal-value pairs. No corrected assignment or solved example is supplied.

All observations are computed, not model-judged. Rotate the three execution orders across cases as implemented; with four tasks this is not a balanced order factorial. Each branch receives only its own seed and cue, never a sibling output. Maximum twelve new model generations, one per cell, greedy, no semantic retry. This measures a prompting treatment on reused failed seeds, not a latent thought process.

## Separate observation from acceptance

`observe.py` first records the **unchanged v0.1 strict evaluation**. It then inspects either one bare JSON object or one complete JSON fenced object, and reports decoding, schema, six-integer values, out-of-domain entries and equal-value pairs separately. No prose search, missing-value invention, clamping, key repair or executing model outputs. Duplicate keys, bools and floats do not become valid six-integer proposals. Unavailable observations remain null.

An extracted, feasible candidate in a fence can have diagnostic feasibility true while strict feasibility stays false. Equal-value pairs are observable even for invalid channels but do not establish overall feasibility; the domain and valid-edge subset are explicitly retained. Preserve every candidate, including repeated or invalid outputs. This diagnostic was fixed after seeing v0.1 but **before new v0.2 outputs**. Never mix the two score regimes.

Primary descriptive outcomes: strict feasible count, readable candidate count, domain-valid count, diagnostic feasible count, raw candidate change, input/output tokens and time. Report all twelve cells. Four graphs share one task grammar; no p-values or broad generalization. More diagnostic text has more tokens, so information, specificity, explanation and input length are not isolated causes. A floor result ends this small-baseline pass; do not silently change model or prompts and overwrite it.

## Source and runtime

Parent research head `86a6e321257ec131a3d4fe942a59170965b7d259`; unchanged task SHA-256 `18954a7d51f2068f56e06aa9861b23d8495e9c8f9ae8bf4d81767a6635314f88`; seed file SHA-256 `19e4d57529ec33882760991a11310dfa6ac77c5d8336735e27ee9ce877ff8cf3`.

Same Qwen/Qwen2.5-0.5B-Instruct revision `7ae557604adf67be50417f59c2c2f167def9a775`, weight hash checked against v0.1. PyTorch 2.10.0 CPU, Transformers 4.57.1, tokenizers 0.22.1, huggingface-hub 0.36.0, safetensors 0.6.2, numpy 2.2.6. Float32, eager attention, two threads, seed 2709, greedy, 96 new tokens and 1200 input tokens per cell. No finetuning, paid endpoint, model tools, private record or user's PC.

Standard GitHub-hosted public Ubuntu runner, Python 3.12, 12-minute job and 540-second inference-process caps, at most 1.15 GB of the seven pinned model/tokenizer files. Safetensors only, no remote model code; socket calls blocked during evaluation. Dependencies remain in the disposable runner. Permissions contents-read, credentials not persisted, no artifact/cache upload or private secrets. Public standard-runner pricing is documented at https://docs.github.com/en/billing/concepts/product-billing/github-actions . No larger runner or paid API authorized.

A path-scoped synchronize event on existing draft PR57 initiates this version once when source is added. Result-only edits do not initiate it. No schedule or future unattended work. Record any setup failure separately; do not restart semantic trials silently.

## Verification and result retention

Before inference, ten observer tests run. One checks all 32,768 bare/fenced representations over four graphs and channel candidates 0..3; domain correctness is checked separately from relations. This is software verification, not 32,768 model trials or independent semantic cases. Additional tests preserve all twelve old strict results and refuse duplicate/missing result inventory.

Every cue, raw response, output token ID sequence, input-token count, prompt hash, package/model digest and diagnostic appears in logs. A gzip/base64-encoded JSON copy with SHA-256 supports exact result transfer without manually retyping outputs. This public research-data transport is neither a model output command nor an executable payload. No upload artifacts consume storage. Full logs remain subject to GitHub retention.

Generate/feedback/refine is established work, e.g. Self-Refine (https://arxiv.org/abs/2303.17651); our checker is deterministic rather than model self-feedback. This small follow-up contributes a inspectable measurement example, not a new general algorithm, novelty certificate, AGI finding or model benchmark.

영석의 생성적 사고 관점을 이 과제의 성패로 판정하지 않는다. 처음 후보를 보존하면서 관측할 수 있는 내용을 되돌려주는 방식을 시험한다. 원래 기록은 그대로 두고, 새 관측과 새 모델 실행은 별도로 남긴다.
