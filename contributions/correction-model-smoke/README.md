# First separate-model smoke run for correction-state development inputs

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

## Question and scope fixed before execution

Can the already-prepared synthetic Korean planning inputs be submitted to a
separate model, returned as usable outputs, and scored without giving that model
the author answer key? This is a development smoke run, not a held-out benchmark,
independent expert review, or a test of a user's actual long-term relationship.

Eight author-created cases have two renderings each: chronological prose and
structured JSON. Both preserve the exact event text, roles, order and IDs. The
shared instructions are explicit. Input length is not token-matched and there is
one generation per rendering. Results cannot isolate an intrinsic advantage of
structure, characterize frontier models, or establish a general causal effect.
These cases were used for development before this run and must not later be
relabeled as unseen evaluation histories.

## Fixed inputs and execution

`inputs.compact.json` losslessly factors a shared prefix/suffix out of the previous
16-line model-input JSONL. The reconstructed bytes must have SHA-256
`0335c83c4d9bef8fd52d800381a8e9fe4e0362611b94692657dd562ac7fd54c3`.
Only item IDs and prompt strings are reconstructed. The author answer key and
case-condition map stay outside this folder and are not sent to inference.
No private dialogue, email, identity document or account configuration is included.

The bounded standard public Ubuntu CPU job downloads these public inputs:

- llama.cpp `b10809` Ubuntu x64 runtime, source
  `5266f24da75dc449bd56cbed7addb9c8e4a6a73e`; archive SHA-256
  `5e34434ddc6d03cd1584f403201aff0d4bd1a5793a72ff7e286532dfd1e4b941`.
- ggml-org's Qwen3.5-0.8B Q8_0 GGUF at model-repository revision
  `8fea620810c4afa23dd6443f999a48574c1611a3`; weight SHA-256
  `37ae482d336108d23516fa35e8e0c4126688d81018b87178a18d752a1357814f`.

No hosted inference API, model key, GPU purchase or user installation is used.
The model runs with 4 CPU threads and a 4,096-token context. A fresh loopback-only
server process and fresh empty home are created for EVERY input; each receives
one user message, no prior conversation or tools. The executable's environment
contains only paths, locale and thread settings, not the Actions token. This is
process isolation for conversation state, not an OS network sandbox certificate.

Generation settings are fixed in run.py: temperature 0, top_k 1, top_p 1,
min_p 0, repeat penalty 1, seed 20260914, max_tokens 256, thinking disabled through
the chat template, and no prompt cache. This greedy setup is a smoke-test choice,
not a reproduction of the model author's recommended benchmark settings.
A fixed seed randomizes item execution order. The raw request, response, server
properties, logs, token usage and process identity/order are retained. Inputs,
weights, runtime archive and executing binary/source hashes are recorded.

## Scoring policy fixed before seeing model output

After inference, use the existing local author key without editing prompts or
labels. The primary descriptive outcome is exact task-ID-set and clarification-
boolean agreement. The response must be an untruncated single JSON object in its
entire content field; only surrounding whitespace is ignored. Reject duplicate
JSON keys, nonfinite values, missing/extra fields, duplicate/unknown task IDs,
non-boolean clarification values and structurally invalid evidence IDs. Do not
strip Markdown fences, repair JSON, re-prompt or select among retries.

Report raw JSON usability and full output-contract validity separately. Question
presence/null and valid event IDs are structural checks. Whether a clarification
question asks the right thing, or cited evidence is sufficient, requires a
separate labeled qualitative review; it is not certified by structural parsing.
Do not require every historical event ID as a condition of state correctness.

For each rendering, report exact matches out of eight and both members correct
out of each of the four counterfactual pairs. Do not count two renderings of one
history or repeated decoding as independent user samples. List all failures and
finish_reason=length separately. Also report actual input/output token counts;
format lengths differ. A completed workflow means the requests ran, not that
answers were correct. Infrastructure failure stops the run rather than prompting
until success. Preserve original failed records if an infrastructure fix is needed.

If both renderings perform identically on these explicit examples, do not claim
a structured-memory advantage. If either fails, inspect the preserved response
before attributing it to memory, language competence, schema following or length.
No large follow-up run is automatically authorized by this small diagnostic.

## Run and resources

```sh
python -B -S contributions/correction-model-smoke/run.py \
  --out /path/to/new-results --work /path/to/new-disposable-runtime
```

Requires Linux x64, Python 3.12 and network access for downloads. The runner
uses Python's standard library, not an installed model-service SDK. Both output
paths must be new. Only child processes created here are stopped by the harness.
The workflow is limited to this named same-repository branch, has contents:read,
a 15-minute job cap and a 13-minute command cap. Only small synthetic JSON/logs
are uploaded for one day; weights, runtime binaries and working directories are
not uploaded. No schedule, recurring process, release or old-source edit is added.
Standard public Actions compute has no usage-minute charge; artifact storage is
subject to the account's separate storage policy. No billing setting is changed.

At preparation the runner syntax, exact input reconstruction and returned Git
blob identities were checked locally. Local DNS prevented downloading the model
there, so actual inference is pending the hosted run. No model score is claimed
in this initial protocol.

## Primary references

- Model card: https://huggingface.co/Qwen/Qwen3.5-0.8B
- Converted weight source: https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF
- Runtime source/release: https://github.com/ggml-org/llama.cpp/releases/tag/b10809
- Public-runner billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Related question, not a claimed completed study: ../../notes/01-reconstruction-rule.md

New runner and synthetic input text use the repository's existing MIT terms at
../../tools/evidence-mcp/LICENSE. Third-party runtime/model licenses remain their
own; neither binary nor model weights are redistributed in this change.
