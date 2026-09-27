# Design audit and next-run gate, version 0.1

Prepared 2026-09-27 by Zero. **This is not authorization to incur charges, start background jobs, send private memory to a provider, or claim an empirical result.**

## 1. What the existing study does and does not establish

The existing protocol is designed to measure behavioral sensitivity to structured rule-trigger-action links. Its public smoke generator supplies one action request per case, with evaluator gold held at the original task target when links are shuffled. That is an intentional link-sensitivity contrast; it should not be reinterpreted as ordinary correctness against every manipulated instruction.

It does **not** independently measure recall and next choice. A model could follow the supplied shuffled mapping, receive a lower original-target score, and nevertheless exhibit accurate conditional instruction following. No update to the old data or old metrics has been made. This companion has a separate task and answers according to the currently authoritative content.

Reviewed original source at commit `6415703ffdcd2133c62e8d669432ac11cfd2057f`: `experiments/rule-use-eval/build_dataset.py` and `MODEL_EVALUATION_PROTOCOL.md`. The latter explicitly requires frozen inputs, source/model identification, independent leakage review, cost ceilings, and statistical analysis before a claim-bearing run. This companion has not passed those gates and does not silently substitute for them.

## 2. Three distinguishable observations

1. **Recall:** report the current assignment using a direct factual question.
2. **Choice:** select a destination for a new item without first reciting the assignment.
3. **Effect:** in a later extension, observe an actual benign sandbox action and its result. This stage is not implemented here.

Giving recall and choice in the same conversation risks rehearsal, answer anchoring, and extra inference budget. The proposed observational pilot uses fresh contexts with identical history and independent probes. This avoids that particular cue, but it also means the two responses come from distinct executions. A paired mismatch is not proof of a single latent mental state or causal mediation.

As a future separately randomized intervention, compare choice-only versus recall-then-choice versus an equally budgeted neutral intermediate question. Such an experiment would measure a prompting treatment, not reveal what the untreated model was privately thinking. It is deliberately not bundled into this first prototype.

## 3. Primary contrasts and controls

The primary matched history conditions are `user_update` and `user_reaffirm`. Only one equal-length destination value in the second user record changes. All other stimulus content, including answer options and query, is identical within a matched unit. Equal UTF-8 length is checked; equal model token count is **not** established and must be audited for the chosen tokenizer.

`assistant_proposal` is a source-attribution diagnostic, not a length-matched primary control. Its new destination is not user-authorized. The unaffected category is a scope control, not a missing-knowledge case.

Record separately for each probe and condition:

- first-response exact-label accuracy;
- invalid-response rate;
- probability of selecting the new target;
- current-recall/old-choice mismatches in paired queries;
- errors applying a proposal without user approval;
- errors transferring a scoped change to the unaffected category.

Define the descriptive scope-adjusted update sensitivity for each probe:

```
[P(new target | user_update, touched) - P(new target | user_reaffirm, touched)]
-
[P(new target | user_update, untouched) - P(new target | user_reaffirm, untouched)]
```

This distinguishes responding to the relevant update from indiscriminately switching every request. Always report component rates and accuracy: a single contrast must not conceal invalid outputs or source/scope errors. A positive recall-minus-choice accuracy difference is query dependence, not a claim about consciousness or an internal activation mechanism.

The public generator has four surface domains using one task grammar. Label permutations and phrasings are paired variants, **not independent semantic clusters**. No confidence interval or p-value about LLMs can be obtained from the deterministic fixtures. A future inferential run needs genuinely independently authored scenarios and cluster-aware uncertainty, fixed before outcomes.

## 4. Data separation and novelty limits

All records are fictional. No private core, family information, personal account data, or real conversation is included. Current user observations motivated the direction but have not been converted into new verbatim public quotations.

Request IDs are hashes to avoid obvious condition names; because this set and generator are public, those hashes provide no secrecy or contamination protection. The evaluated context may receive only its own `payload`; an external runner may keep `request_id` for bookkeeping. It must not receive gold, conditions, pair membership, another request, program outputs, or the protocol text containing answers.

All three destinations appear equally often as the correct answer within each domain/condition/scope/probe/wording group. Arbitrary destination labels reduce common-sense answer shortcuts, but the simple structured task remains vulnerable to general template solving. It cannot establish broad natural-language understanding.

A held-out set must use new templates, names, phrasings, and structures, not merely change the salt or option labels. A model-accessible published corpus is never described as hidden. Related work contains both knowing-doing studies and long-memory updating tests; the particular combined design still needs novelty review, and null results remain legitimate outcomes.

## 5. Safety, compute, and stop rules

This turn ran software fixtures only, in the ChatGPT container. No remote desktop, GPU, installed package, language-model endpoint, payment, or scheduler was used. Returned labels are never dispatched as commands.

Before the **first exploratory model response**, create a separate dated run sheet naming model and revision if exposed, provider route, prompt adapter, context/output budgets, allowed cost and request ceiling, trial count, randomization, logging, timeout, and retry rules. No provider or access route is selected by this prototype. Public dry runs are exploratory and are not retrospectively made confirmatory.

Before any **confirmatory** model response, meet the original protocol's appropriate gates or publicly register a justified new protocol. Do not silently relax its requirements because they are inconvenient. The original self-report probability contract is not implemented by this companion's one-label response grammar.

Stop for input/gold leakage, version drift, missing raw responses, unregistered retries, changed score code, or exceeded budgets. Preserve first semantic responses including wrong, refused, or malformed outputs. Missing inventory prevents a valid aggregate result; future partial transport failures require a separately frozen intention-to-test ledger, not dropping records.

## 6. Readiness decision

Ready now: inspect the design, regenerate public records, run software fixtures, and challenge the scorer.

Not ready now: claim a new LLM phenomenon, contact researchers claiming such a result, run a confirmatory benchmark, infer a hidden mechanism, or deploy changes to a user's operational memory.

The next useful work is a design review followed by a **small, explicitly budgeted exploratory model run**. Another round of packaging alone will not answer the scientific question.
