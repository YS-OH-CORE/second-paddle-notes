# Diagnose the PR50 floor before testing memory formats

Prepared by Youngseok Oh with Zero (ChatGPT), 2026-09-14.

PR50 returned valid JSON but zero task-set agreement in both renderings. This
follow-up is a small development diagnostic of that failure, not an expansion of
the benchmark, an improved-memory claim, or a correction of the previous scores.

## Twelve predetermined inputs

The same two cancellation histories are used: A and B are assigned, then only A
or only B is cancelled. The opposite valid task must remain. Six groups each
contain two prompts. Ten prompts involve planning; two only test literal copying.

| IDs | Condition | Difference from comparison group |
| --- | --- | --- |
| T01,T02 | Korean, labeled events, original four-field contract | Exact byte-identical repeats of PR50 prose D01/D02. |
| T03,T04 | Korean, labeled events, next_tasks only | Delete the three other requested output fields, retaining the original next_tasks definition and all history/rules. |
| T05,T06 | Korean, no explicit event/order prefixes, next_tasks only | Remove event labels/order numbers; retain roles, utterances and chronological line order. |
| T07,T08 | English, labeled events, next_tasks only | Author translation of T03/T04; not independently adjudicated. |
| T09,T10 | English, no event/order prefixes, next_tasks only | Same prefix removal as in Korean. |
| T11,T12 | Korean / English literal JSON copying | Copy a supplied one-field object; no planning inference. |

Each planning pair has different correct task IDs. A constant B answer cannot
pass a pair. The copy controls deliberately provide the object to copy, and are
never counted as evidence of task-state understanding. No extra hint is added
that says which task is correct in the planning prompts.

The compact input source and runner from PR50 are pinned by SHA-256 and left
unchanged. The new loader constructs only item_id/prompt_text rows and checks
all reconstructed bytes before downloads. The author key is not read by the
runner; the model receives only one prompt, with no tools or file access.
New input SHA-256: c63a3a6c888c12cef617242d4c8a322e73c7a89d146c5b387612095b62d8c562.

## Execution kept the same

Import PR50's runner only after matching its original SHA-256
71ea1dbaacf566e180452b304f33cecf2a1f98e72e143cf0db58f54bd19d1aa4.
Use its unmodified execute(), download constants, and generation settings:
Qwen3.5-0.8B Q8_0 at fixed model revision, llama.cpp b10809, 4 CPU threads,
4096 context, greedy temperature0/top_k1, max256 output tokens, thinking disabled,
no prompt caching. Each of the twelve prompts starts a new server and empty HOME.
No prior output or author's expected answer is sent. Runtime warnings remain logged.
No independent equivalence check against the original model implementation is
implied. Download hashes and binary/source identities are recorded again.

One named same-repository branch; standard public Ubuntu CPU runner; contents:read;
10-minute job and 9-minute command ceiling. No dependency installs, paid inference
API, model key, GPU, private dialogue, or user-PC/profile installation. Only small
synthetic logs/JSON are retained for one day, not weights or binaries. No cache or
recurring task. Standard public-runner minutes are free under GitHub's policy;
artifact storage has a separate policy, so this is not a guarantee about the
account's aggregate invoice. No billing setting is changed.

## Scoring fixed before observing outputs

A complete untruncated content field must parse as one strict JSON object. Do not
strip fences, repair JSON, translate IDs, re-prompt, or select the best retry.
Primary descriptive score for every group: exact task-ID set, ignoring ordering
but rejecting duplicate/unknown IDs and wrong types. Report output-contract
validity separately. For the two full-contract anchors also report the original
joint task/clarification-boolean score; the other prompts do not request that
boolean and are not directly comparable to PR50's joint metric.

Report each opposite-cancellation pair, raw output, usage, finish reason and
inference settings. Compare the two exact-repeat anchor outputs with the original
response contents. If they differ, retain the discrepancy; do not choose a
favorable replicate or conceal it. The copy controls get their own score.

The local scorer was fixed before the new run: SHA-256
087c2dcdb94645ac14b62503b895a90efb98e978030891285811ae6cadfb69c3.
Author key SHA-256: 003107f16abf5413e2bc1e23278129ff15db22e85c440cb78c1e0290876b8040.
Seven local parser/scorer checks passed. These are software checks, not model
responses. The frozen scorer/key will accompany the returned original evidence.
This is not independent preregistration or human review.

## How outcomes change the next decision

- If the original anchors fail but shorter-output versions pass, do not attribute
  the original floor solely to lost history. Simplifying the requested report may
  be enough for these examples. Removing fields also changes length and the output
  demand; it does not isolate one neural mechanism or a pure length effect.
- If removing event labels changes results, examine competing identifier cues.
  This supports a prompt-level sensitivity on these two cases, not a universal
  diagnosis of every previous failure.
- If only the English versions work, language/wording is an alternative explanation
  to memory-format effects. Translation is itself a manipulation and is not
  independently validated here.
- If planning still fails while literal copying works, this model/setup has not
  cleared the entry requirement for this study. Stop expanding the memory test.
- If literal copying also fails, examine basic model/runtime behavior before any
  substantive interpretation. A hosted job completing is not evidence of competence.

There is one generation per input, two source histories, unequal token counts,
explicit task rules and no held-out evaluation. The chosen manipulations do not
establish a population effect or the overall value of long-term human-AI memory.
No next model run is automatically started based on a favorable or unfavorable
score. Preserve the previous negative result unchanged.

## Reproduce

From the repository snapshot containing the unchanged PR50 source:

```sh
python -B -S contributions/correction-task-diagnostic/diagnose.py \
  --out /path/to/new-results --work /path/to/new-disposable-runtime
```

Linux x64, Python3.12 and public download access are required. Both directories must
be new. Local preparation checked source syntax, exact anchors, prompt invariants,
and scorer edge cases; local DNS prevented model acquisition. Hosted execution
is pending at the protocol's creation.

References: ../correction-model-smoke/README.md and RESULTS.md;
https://huggingface.co/Qwen/Qwen3.5-0.8B ;
https://docs.github.com/en/billing/concepts/product-billing/github-actions .
New text/code follow ../../tools/evidence-mcp/LICENSE. Model/runtime terms remain
their own. No binary or weight is redistributed.
