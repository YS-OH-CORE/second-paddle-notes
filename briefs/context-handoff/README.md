# Before blaming the model, trace what reached it

**A research brief on preservation, delivery, use, and observation**  
Youngseok Oh × Zero · 28 September 2026  
[한국어](BRIEF.ko.md) · [Workroom](../../README.md)

**Status: synthesis of previously published checks and a proposed diagnostic method. No new model experiment, benchmark score, or upstream adoption is claimed here.**

An assistant fails to use a correction. Did its memory omit the correction? Did a conversion retain the words but discard who said them? Did the correct input arrive without affecting the choice? Or did our evaluator fail to inspect the candidate it received?

Those questions call for different repairs. Treating them as a single failure of intelligence can send an otherwise careful investigation toward the wrong component.

Our existing question, [A Rule Read Is Not a Rule Running](../../notes/15-a-rule-read-is-not-a-rule-running.md), concerns whether past corrections change later decisions. The following cases make the boundaries around that question more concrete. They do not establish an internal neural mechanism or reduce generative thought to rule compliance.

## 1. Same visible value, different origin

In a pinned Pydantic AI experiment, a wrapper that **inherited** its identity and a wrapper whose caller **explicitly supplied the same identity** exposed the same initial ID and deferral values. Their intended rebinding behavior differed: only the inheriting wrapper should follow the wrapped capability's later deferral setting.

The original reporter identified the origin-tracking direction. Our supplemental contribution was an explicit-equal-ID negative control, nested wrappers, repeated use of one Agent, and observations of the prepared first request. Unconditional re-adoption repaired transparent wrappers but changed explicit settings too. This is a software-origin distinction, not a model reasoning result. [P1]

**Review question:** can the next component distinguish an inherited value from an explicit instruction that happens to equal it? Equality of the public fields alone cannot answer that; other retained state may.

## 2. Valid conversion, lost relation

A pinned vLLM/Mistral test constructs two different histories: tool A returns image X while B returns Y; or A returns both images while B returns none. In the pre-v15 adaptation path, the histories become equal and both pass the real message validator. The images remain; their original ownership relation does not remain in that converted history. The v15 path preserves the distinct inputs. [P2]

This characterizes a compatibility tradeoff already disclosed by the upstream author. It is not a newly discovered vulnerability, and no inference server or model behavior was tested.

**Review question:** did the representation preserve the relation needed for the next question, not just every content item? An upstream archive may retain that relation even when the next consumer is not given it.

## 3. A setting on disk is not yet a setting in effect

A proposed Hermes/Honcho fix received an automated review asking for the actual configuration-loading path, rather than a test that injected the desired value directly. Our follow-up kept the real disk loader, provider, session manager, and startup migration logic, replacing only the remote SDK boundary. Four root/host/default configurations produced the expected startup-upload behavior. Deliberately bypassing the startup guard or ignoring the disk setting caused the expected negative cases to fail. [P3]

That is evidence about the **pinned proposed fix's local startup path**. It is not a live-service test, universal read-only mode, or proof about current main. In particular, observing the provider become ready matters: an inactive provider can produce zero uploads without honoring any setting.

**Review question:** did the intended value reach a functioning consumer and govern the observed operation?

## 4. A rejected output can still contain an observable proposal

Our small-model construction pilot initially returned only a format-invalid notice when a candidate used Markdown fences. The next version kept strict acceptance unchanged while separately inspecting the candidate's values and constraints. More specific observations then reached the model, but feasible constructions still did not improve. A later adequacy diagnostic found working elementary controls alongside uneven graph-task performance. We retired that model/task combination as the main probe. [P4]

This was an instrument correction, not a model improvement. A candidate can remain worth recording while failing a particular task. Conversely, recording or understanding its syntax does not make it a correct solution. The three development runs are not independent replications of one treatment.

**Review question:** is the measurement separating what was proposed, what can be inspected, and what actually satisfies the task?

## A simple limit on what a downstream system can recover

Let `C(h, q)` be **all information available to a decision rule** for history `h` and request `q`, including retrieved material, side metadata, and any retained state. Let `A(h, q)` be the set of acceptable immediate actions.

If two histories satisfy

```text
C(h0, q) = C(h1, q)
A(h0, q) and A(h1, q) have no common action,
```

no deterministic decision rule using only `C` can be correct in both cases. It receives the same input and must produce the same action. A randomized rule also receives the same information; for an equally weighted pair, its average chance of choosing an acceptable action is at most one half, because its probabilities on the two disjoint acceptable-action sets sum to at most one.

This is an elementary indistinguishability argument, **not a new theorem or a model-performance measurement**. Its assumptions matter. If both histories permit clarification, deferral, or the same safe action, the action sets may overlap and the claim does not apply. A retrieval request can acquire differentiating evidence and change `C`. A claim that only the displayed text matches is insufficient if the agent retains different state elsewhere.

The practical lesson is narrower than “a better model cannot help”: **do not ask inference alone to recover information that the evaluated interface does not distinguish.** More capable retrieval or a better representation can help by changing that interface.

## A diagnostic sequence for the next experiment

Before choosing a larger model, retain an inspectable trace of the synthetic source history, transformed memory, actual request, proposed action, executed action where applicable, and feedback. Sensitive production traces require separate authorization; these case studies do not require private conversations.

| Check | Required comparison | What it does not establish |
|---|---|---|
| Task adequacy | Full, unambiguous context and simple controls are usable by the chosen baseline. | General capability across other tasks. |
| Information preservation | Distinct histories with different required choices remain distinguishable at the evaluated interface, or recoverable by permitted retrieval. | That the model actually uses the distinction. |
| Behavioral use | Keep relevant facts and resources comparable; change attribution or correction links and observe the relevant choice plus unrelated controls. | Direct access to internal reasoning. |
| Execution fidelity | Compare the proposed operation with what the downstream tool actually performs. | Correctness of the original choice. |
| Observation coverage | Preserve raw candidates and expose separate format, content, and outcome observations, with positive and negative controls. | Automatic success from richer feedback. |

A finite collision search can disprove preservation for a tested pair; failure to find a collision does not prove universal preservation. Passing all checks is still not a general intelligence criterion. This sequence is a design proposal derived from the cases, not a newly completed evaluation.

## Relation to existing work

W3C PROV-DM represents attribution, derivation, entities, activities, and agents explicitly; provenance as structured information is not our invention. [R1] State-abstraction research studies which information can be condensed while retaining useful decision behavior; our elementary argument is not a replacement for its formal guarantees. [R2]

LongMemEval evaluates several long-term memory abilities and distinguishes indexing, retrieval, and reading. [R3] AMemGym studies interactive memory evaluation with structured state evolution. [R4] These works already go beyond a simplistic “remember more text” objective. We have not run either benchmark, and a limited source review cannot establish that our proposed sequence fills a unique gap.

**The contribution of this brief is the source-linked cross-case distinction:** loss before inference, delivery to a real consumer, behavioral response, and evaluator coverage should not be counted as interchangeable evidence. It offers a focused point of entry for collaboration rather than another leaderboard or a claim that our broader ideas are proved.

## Evidence and primary references

**P1.** [Pydantic origin/equal-ID check and scope](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1c21cd31f0ae48be124661349924dae3b41c47fa/checks/pydantic-8728/README.md). Original diagnosis/proposal: adtyavrdhn; supplemental execution: Zero with Youngseok Oh. Target and environment are specified in the record.

**P2.** [Exact image-attribution contrast](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1f89094fd2ac9c9846c852079d7118b9e94381ca/checks/vllm-58823-mistral-validator/test_provenance_boundary.py) and [execution scope](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1f89094fd2ac9c9846c852079d7118b9e94381ca/checks/vllm-58823-mistral-validator/README.md). Upstream renderer change remains its contributor's work.

**P3.** [Honcho disk-to-startup test results](https://github.com/YS-OH-CORE/second-paddle-notes/blob/228f6ad2feedf0d5ac9520c2cb4b28b73eab2ab2/checks/honcho-real-config-73935/RESULTS.md). Original implementation: saurabhmeddo; test-only follow-up: Zero with Youngseok Oh. Earlier setup failures remain documented.

**P4.** [Observation follow-up](https://github.com/YS-OH-CORE/second-paddle-notes/blob/7d9064d4e90a45e999ef97b1ecb9dc84d51646d2/experiments/generation-feedback-pilot/v02/RESULTS.md) and [adequacy diagnostic](https://github.com/YS-OH-CORE/second-paddle-notes/blob/1a9b0ab448c5a3dc644ac5155daaf00e819a3531/experiments/generation-feedback-pilot/adequacy/RESULTS.md). Development observations, not hidden confirmation or a test of AGI.

**R1.** [W3C PROV-DM](https://www.w3.org/TR/prov-dm/). 2013 Recommendation.  
**R2.** Abel, Hershkowitz, Littman. [Near Optimal Behavior via Approximate State Abstraction](https://proceedings.mlr.press/v48/abel16.html). ICML 2016.  
**R3.** Wu et al. [LongMemEval](https://arxiv.org/abs/2410.10813).  
**R4.** Cheng et al. [AMemGym](https://arxiv.org/abs/2603.01966). 2026 preprint; reference here is to its stated evaluation approach, not independently verified results.

---

Conceptual direction and long-running questions: **Youngseok Oh**. Synthesis, argument, source review, and writing: **Zero, his AI collaboration partner**. This text is not a verbatim user statement or an independent review. Existing contributors retain credit; no institutional endorsement is implied. No private archive was published to make this brief. No new model run accompanied it.
