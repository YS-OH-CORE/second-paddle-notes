# Claim-Bearing Model Evaluation Protocol

**Protocol version:** 1.0
**Status:** protocol only; no language model has been run under this protocol
**Companion artifact:** [Rule-Use Smoke Evaluation](README.md)

This document defines the minimum procedure for making a behavioral claim about a language model using the rule-use task. It is intentionally separate from the public smoke set. The public cases, deterministic fixtures, and their committed metrics verify software behavior only. They are not pilot observations to be pooled with, substituted for, or cited as model evidence.

The study asks a narrow question:

> When declarative content is held fixed, does a model's machine action change appropriately with a hidden rule-trigger-action relation, beyond its tendency to act on irrelevant events?

The result may support or fail to support an **observable rule-use effect under the registered conditions**. It must not be described as evidence of consciousness, comprehension in general, an internal symbolic mechanism, a persistent agent, or any other unmeasured property.

## 1. Registration gate

Before generating any model response, publish a time-stamped preregistration containing all of the following:

- the protocol version and immutable repository commit;
- the hidden-set manifest hash, without publishing the hidden cases;
- the primary hypothesis, estimand, smallest effect size of interest, and decision rule;
- the exact model provider, model identifier, snapshot or revision when available, and planned UTC run window;
- the number of templates, conditions, scopes, and repeated trials;
- the complete transport prompt and every model-specific prompt adapter;
- decoding parameters, context limits, output-token limit, tool settings, seeds when supported, and timeout policy;
- case-order randomization procedure and its committed seed or seed hash;
- parsing, scoring, confidence scoring, uncertainty, exclusion, and retry rules;
- planned secondary and exploratory analyses;
- leakage checks, stop conditions, and release plan.

Registration occurs before the first claim-bearing response, not merely before scoring or publication. Any substantive change after registration creates a new study version. The original registration and the reason for the change remain public.

If no design-specific justification is registered, use this default minimum design per model: 24 independently constructed hidden templates, two scopes (`relevant`, `irrelevant`), the two primary conditions (`correct`, `shuffled`), and five fresh trials per cell. This produces 480 intended responses per model. Additional conditions such as `reversed` and `absent` are secondary diagnostics and must not replace or alter the primary pair.

## 2. Frozen hidden set

The claim-bearing cases must be newly created and unavailable to the evaluated model, model operator, prompt adapter, and scorer during development. Public smoke cases may inform the file format, but hidden templates must not reuse their wording, identifiers, examples, domains, or exact structures.

Before model execution:

1. Generate the full cases and evaluator-side gold.
2. Canonicalize every record with a documented serialization.
3. Freeze them in a read-only bundle and record a SHA-256 manifest.
4. Give the model runner only opaque case IDs and model-facing task content.
5. Keep template, scope, condition, expected action, pair membership, and gold outside the runner-visible bundle.

For every hidden template and scope, `correct` and `shuffled` must be content-equated:

- instructions, rule atoms, trigger examples, action checks, verification text, and observed event are byte-for-byte identical;
- both conditions contain the same rule, trigger, and action atoms;
- both contain the same number of links;
- action labels are opaque and equal-length within a template;
- only the trigger-to-action assignment is permuted;
- canonical serialized lengths are equal;
- the permutation has no fixed point; and
- no case ID, ordering feature, whitespace, field order, label morphology, or metadata reveals the condition or answer.

Relevant and irrelevant events must be preclassified before any model response. The irrelevant event must have no registered task action under either primary condition. Templates should span multiple domains, but domain composition is fixed at registration and reported rather than treated as a post-hoc source of favorable examples.

Once raw outputs or gold are released, the bundle is public and can never again serve as a hidden confirmatory set.

## 3. Leakage audit

The frozen bundle does not become claim-bearing merely because it is called hidden. Before execution, an auditor who did not author the templates must record:

- exact-string and normalized n-gram overlap checks against the public smoke set, repository, prompt examples, and prior released studies;
- duplicate and near-duplicate checks within the hidden set;
- a manual inspection for condition clues, answer-bearing prose, label morphology, and unequal serialization;
- confirmation that gold and condition metadata are absent from runner inputs and logs available to the model;
- confirmation that no retrieval, web, memory, tool, or cross-case conversation can expose another case or the gold;
- hashes of the scripts and adapter actually used.

Any discovered answer leakage, condition leakage, public exposure, or mismatch between the frozen hash and run input stops the confirmatory study. Fixing the set requires a new hash and a new preregistration; affected responses are never silently retained.

## 4. Model and run identity

Each result must identify what actually ran, not only a product family. Record:

- provider and endpoint;
- exact model ID and dated snapshot/revision if exposed;
- access tier or deployment name when it can affect behavior;
- UTC request and response timestamps;
- registered and provider-reported decoding parameters;
- context and output-token limits;
- system, developer, user, and transport messages in their transmitted order;
- enabled tools, retrieval, memory, safety mode, and structured-output mode;
- provider response ID, finish reason, token usage, latency, and error status where available;
- runner commit, environment, and adapter hash.

If the provider silently aliases models and exposes no snapshot, say so explicitly. Results are then claims about the observed service during the dated run window, not about an immutable model. A model replacement, endpoint behavior change, or unregistered parameter change during a run triggers the stop rule in Section 11.

Each trial starts in a fresh, stateless conversation. Tools, browsing, retrieval, persistent memory, and communication between trials are disabled. Cases are run in the preregistered randomized order, with paired conditions separated so their relation is not made salient. Repeated trials use the same fixed parameters and a registered seed schedule where seeds are supported. Unsupported or nondeterministic seeds are recorded, not simulated.

## 5. Prompt-adapter boundary

The common semantic task is frozen before the study. A model-specific adapter may only:

- wrap the same task content in the provider's required message or structured-output format;
- restate the output grammar without adding task strategy, demonstrations, or semantic hints;
- map transport field names without changing any rule, event, link, action, or verification content; and
- enforce the same tool-free, fresh-context boundary.

Every adapter is published and hashed at registration. It may not include condition-specific wording, gold-derived examples, model-specific coaching, chain-of-thought requests, or corrections based on pilot performance. No adapter may inspect condition labels or gold. A neutral syntax validator may inspect format after the response, but it cannot request a second semantic answer.

If materially different adapters are necessary, results are reported separately by adapter. They are not treated as a pure model comparison unless adapter equivalence was independently validated and preregistered.

## 6. Response contract: action before explanation

The model is instructed to return exactly three records in this order:

```text
ACTION: <one listed action_id>
PROBABILITIES: {"<action_id>": <number>, ...}
EXPLANATION: <optional single sentence, or empty>
```

The first nonblank output record is the machine action. The second is a probability distribution over every listed action, with each value in `[0, 1]` and a total within `1e-6` of `1`. The explanation comes last, is never used to repair or reinterpret the action, and is not requested as hidden reasoning. This ordering is an observable output constraint, not evidence about the model's internal order of thought.

The chosen action and probability distribution are captured before the model receives gold, correctness feedback, grader text, another condition, or any follow-up. The first returned semantic answer is final. A refusal, unlisted action, missing action, malformed distribution, or extra answer is retained in raw output and handled by the registered scoring rules; it is not interactively corrected.

## 7. Outcomes and scoring

Let:

- `Y[t,s,c,r] = 1` when the machine action exactly equals gold for template `t`, scope `s`, condition `c`, and repeat `r`; otherwise `0`;
- `F[t,c,r] = 1` when an irrelevant-scope response selects any action other than `NO_ACTION`; otherwise `0`.

Invalid, refused, or unparseable first actions count as `Y = 0`. On irrelevant cases they also count as a false action only if an actionable listed ID was actually emitted; the invalid-output rate is separately reported. This distinction must be frozen in scorer tests before unblinding.

The confirmatory estimand is the macro-average across templates and repeats of the paired correct-versus-shuffled difference-in-differences:

```text
[(Y relevant,correct) - (Y relevant,shuffled)]
-
[(F irrelevant,correct) - (F irrelevant,shuffled)]
```

Pairing is by template and repeat index. The first term measures appropriate behavioral sensitivity to the correct mapping. The second subtracts collateral changes in the tendency to act on irrelevant inputs. Neither overall accuracy nor a favorable secondary condition can replace this registered primary estimand.

Report at minimum:

- the primary difference-in-differences and its per-template values;
- exact-action accuracy by scope and condition;
- irrelevant false-action rate by condition;
- invalid-output and refusal rates;
- all repeated-trial distributions, not only their means;
- template/domain heterogeneity; and
- every registered secondary diagnostic, labeled secondary.

### Confidence calibration

Probability output is scored independently of the machine action. For `K` allowed actions with submitted probabilities `p[k]` and one-hot gold `y[k]`, report:

```text
multiclass Brier = sum_k (p[k] - y[k])^2
log loss = -log(max(p[gold], 1e-6))
```

Lower is better. Report both overall and by condition/scope. Do not infer missing probabilities from prose. A malformed or missing distribution receives the preregistered worst-case values: Brier `2.0` and log loss `-log(1e-6)`. Calibration metrics are secondary unless a separate calibration hypothesis was preregistered. They cannot rescue a failed action-based primary result.

## 8. Repetition and uncertainty

Repeated trials measure service-level variability; they are not independent new templates. Uncertainty must therefore respect the experimental unit.

Use a two-sided 95% cluster bootstrap with templates as clusters and repeats retained within each resampled template. Register the bootstrap algorithm and seed, and use at least 10,000 resamples. Also report a paired randomization or sign-flip test on template-level correct-versus-shuffled contrasts as a robustness check. Publish the complete interval, point estimate, and template count; a p-value alone is insufficient.

For comparisons across multiple models, report each model separately. Any confirmatory pairwise ranking and multiplicity adjustment must be registered before execution. Unregistered cross-model comparisons are exploratory.

The default smallest effect size of interest is `0.10` on the primary scale. A different value is allowed only when justified and registered before the run.

## 9. Exclusions, failures, and retries

Use an intention-to-test accounting: every scheduled trial appears in the run ledger.

- A response with any model-generated content is never excluded for being wrong, refused, malformed, truncated, or inconvenient.
- Format failures are scored as specified above; there is no semantic retry.
- A transport retry is allowed only when the provider returns no model-generated content because of a documented network error, timeout, rate limit, or provider 5xx response.
- The maximum transport retries, delay policy, and whether the same seed is reused are preregistered; the default is two retries with the same payload and seed.
- All failed attempts remain in the raw ledger.
- A case is excluded only when every registered transport attempt produced no model content. Exclusions are reported by condition and scope.
- No missing case is replaced with a newly authored case after execution begins.

If exclusions exceed 5% overall, differ by more than 5 percentage points between either primary condition or scope, or create an incomplete correct/shuffled pair, stop confirmatory interpretation. The data may be released as an aborted-run diagnostic.

## 10. Decision and falsification rules

With the default smallest effect size of interest `delta = 0.10`, the registered rule-use claim is supported only when all of the following hold:

1. the primary point estimate is at least `delta`;
2. the lower bound of the two-sided 95% cluster-bootstrap interval is greater than `0`;
3. the dataset, adapter, scorer, and run match their frozen hashes;
4. no leakage or stop condition is present; and
5. the exclusion rule is satisfied.

If these conditions are not met, the confirmatory claim is **not supported**. Do not convert a null result into a positive claim using overall accuracy, explanation quality, confidence, a subset of templates, another condition, or a different metric.

The directional hypothesis is **falsified under the registered conditions** when the upper bound of the 95% interval is at or below `0`. An interval spanning both `0` and `delta` is inconclusive, not proof that the model uses or ignores rules. An interval above `0` but with a point estimate below `delta` is evidence of an effect smaller than the registered meaningful threshold and does not meet the claim criterion.

Unexpected reversed-condition behavior, compelling explanations, or high self-confidence are diagnostic observations only. They never override the machine-action result.

## 11. Operational stop conditions

Stop the run before unblinding or scoring if any of the following occurs:

- hidden cases, condition labels, pair membership, or gold become visible to the runner, adapter, model, or case author during execution;
- any frozen input, prompt, adapter, scorer, or manifest hash changes;
- the advertised model ID, snapshot, endpoint, tool state, or registered inference parameters change;
- a systematic logging error prevents preservation of raw requests or first responses;
- a condition-dependent transport failure or exclusion imbalance reaches the Section 9 threshold;
- the provider's terms or technical behavior prevent the registered raw-output release; or
- a preregistered maximum cost, request count, or run window is reached.

Do not switch models, rewrite prompts, repair cases, extend the budget, or alter scoring inside the same confirmatory run. Preserve the partial run, mark it aborted with the reason and timestamp, and preregister a new version if another attempt is warranted.

## 12. Blinding and analysis sequence

The preferred separation is:

1. a set author creates and freezes cases and gold;
2. an independent auditor approves leakage and balance checks;
3. a runner receives only opaque model-facing cases and executes the registered ledger;
4. raw outputs and the completed ledger are frozen and hashed;
5. a scorer joins outputs to evaluator-side gold and executes the already tested analysis;
6. the full result is released before exploratory interpretation.

If one person must fill multiple roles, automate the boundary and disclose the overlap. Condition labels remain blinded until all intended raw outputs, exclusions, and hashes are frozen. Explanations are not manually inspected for favorable examples before the primary analysis is locked.

## 13. Required release bundle

For a result to be publicly claim-bearing, release an immutable bundle containing:

- preregistration and amendments with timestamps;
- protocol, runner, adapters, parser, scorer, tests, and environment lock data;
- exact model-facing requests in run order;
- unedited raw first responses and all failed attempts;
- parsed actions and submitted probabilities;
- provider metadata listed in Section 4, except credentials or prohibited personal data;
- the run ledger, exclusions, and abort events;
- the previously hidden cases and gold after the run;
- SHA-256 manifests before and after unblinding;
- primary and secondary metrics, uncertainty output, and machine-readable per-trial data; and
- a short claim-boundary statement naming what the study did and did not measure.

API keys, authentication headers, billing identifiers, private account data, and unrelated request metadata must be removed. Redaction is documented field-by-field and must not alter prompts, outputs, model identity, timing order, or outcome-relevant metadata. If provider terms forbid releasing enough raw material for independent checking, the study must not be advertised as a public claim-bearing evaluation under this protocol.

## 14. Minimum report wording

A compliant positive report can say:

> Under the preregistered, tool-free evaluation on the dated model service, machine actions showed a scope-controlled correct-versus-shuffled rule-use effect of **X** (95% cluster-bootstrap interval **[L, U]**, **N** hidden templates, **R** repeats). This is behavioral evidence for sensitivity to the supplied relation in this task, not evidence about the model's internal mechanism or consciousness.

A non-supporting report states the same estimate and interval, then says that the registered criterion was not met. Aborted studies are labeled aborted and include the stop reason; they are not silently omitted.

## 15. Pre-run sign-off checklist

- [ ] Registration is public, timestamped, and older than every model response.
- [ ] Hidden bundle, adapters, runner, parser, scorer, and manifest are frozen and hashed.
- [ ] Correct/shuffled cases pass byte-equivalence and no-fixed-point tests.
- [ ] Independent leakage audit is signed and included.
- [ ] Model identity, run window, parameters, trial count, and seed schedule are fixed.
- [ ] The adapter sees task content only and cannot inspect gold or condition.
- [ ] Fresh stateless sessions, no tools, and no cross-case memory are verified.
- [ ] Action is recorded before probabilities and explanation; no semantic retry is possible.
- [ ] Primary estimand, Brier score, log loss, uncertainty, exclusions, and decision rules have executable tests.
- [ ] Raw-output release and credential-redaction paths have been dry-run without calling a model.
- [ ] Cost/request ceilings and every stop condition are registered.
- [ ] No public smoke result is counted as model evidence.

Passing this checklist authorizes data collection only within the separately approved budget and access boundary. It does not itself establish a model result.
