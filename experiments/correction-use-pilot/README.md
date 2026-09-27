# Correction recall versus next routing choice

**Status: public instrument prototype, not an LLM result, hidden benchmark, or completed preregistration.**

A small companion to Youngseok Oh and Zero's existing [A Rule Read Is Not a Rule Running](https://github.com/YS-OH-CORE/second-paddle-notes/blob/6415703ffdcd2133c62e8d669432ac11cfd2057f/notes/15-a-rule-read-is-not-a-rule-running.md) and [rule-use experiment](https://github.com/YS-OH-CORE/second-paddle-notes/tree/6415703ffdcd2133c62e8d669432ac11cfd2057f/experiments/rule-use-eval). The existing experiment and its results are unchanged. This prototype isolates a different observable contrast: recalling a current user correction versus applying it to a subsequent routing choice.

**No language model was called. No user's computer or private memory was used.** All execution was in the ChatGPT working container with Python's standard library.

## The concrete question

A user originally routes category coral to tray A and category indigo to tray C. Later the user changes only coral to tray B.

Give the same history to two fresh contexts:

- Recall query: which tray is currently assigned to coral?
- Choice query: a coral item arrives; select its destination.

The probes use the same machine-readable answer grammar. Do not ask the recall question first in the choice context: that would rehearse the rule before measuring its spontaneous use. A second control asks about indigo, whose assignment was never changed. A third places the proposed coral change in an assistant-authored record rather than a user-approved one.

The study target is an *observable query-dependent discrepancy*. Different answers in separate contexts would not prove that one execution consciously knew a rule while ignoring it, nor identify an internal mechanism.

## What exists now

`pilot.py` builds 576 **public synthetic requests**, or 288 recall/choice pairs. These are enumerations of four surface domains using one simple routing grammar, six destination permutations, two query phrasings, three history conditions, two scopes, and two probes. They are not 576 independent tasks, completed model responses, or a validated hidden corpus.

`test_pilot.py` verifies matching histories, equal-length update/reaffirmation stimuli, counterbalanced answer positions, author and scope controls, strict parsing, complete inventories, and scoring behavior. The scorer refuses missing or duplicate predictions instead of quietly changing the denominator.

Four deterministic programs check the instrument:

| Program fixture | Recall accuracy | Choice accuracy | Scope-adjusted update sensitivity: recall / choice |
|---|---:|---:|---:|
| Follow current user assignments | 1 | 1 | 1 / 1 |
| Always use the original assignments | 5/6 | 5/6 | 0 / 0 |
| Recall current assignments but choose using old assignments | 1 | 5/6 | 1 / 0 |
| Follow the last target regardless of author or requested category | 1/3 | 1/3 | 0 / 0 |

These intentionally simple programs were written to have those properties. The outputs demonstrate that the scoring instrument can distinguish the four fixtures. They are **not** observations about an AI system. In particular, the 48 recall-correct/choice-wrong pairs from the third program are not 48 model failures.

## Run without installations

Python 3.10+:

```sh
python -B -m unittest -v test_pilot
python -B pilot.py --out a-new-output-directory
```

The output directory must not exist. It contains model-facing requests, separate evaluator gold, program-fixture outputs, metrics, and a SHA-256 manifest. The runtime makes no network requests, installs no packages, calls no model, and does not execute the returned action codes.

This prototype supports analysis through the Python `score(requests, gold, outputs)` function. It is not yet a provider runner. Only opaque request IDs and `payload` may be sent to an evaluated model. Gold, pair IDs, labels, and other cases must stay outside the evaluated context. Each raw first response is a single JSON object such as `{"action_id":"D0123456"}`; malformed answers count as invalid rather than being repaired from prose.

## Prior work and the narrower contribution candidate

The generic knowing-doing distinction is **not claimed as our discovery**. Closely related primary sources are:

- Schmied et al., *LLMs are Greedy Agents* (2025): decision-making failures and knowing-doing gaps, including bandit and game settings. https://arxiv.org/abs/2504.16078
- Cheng et al., *Model-Adaptive Tool Necessity Reveals the Knowing-Doing Gap in LLM Tool Use* (May 2026): model-specific tool necessity, observed tool invocation, and hidden-state probing. Particularly relevant: Appendix B shows that explicit self-assessment is itself a prompt change. https://arxiv.org/html/2605.14038v2
- Wu et al., *LongMemEval* (ICLR 2025): long-history question answering, including knowledge updates and abstention. https://arxiv.org/abs/2410.10813
- Anthropic, *Reasoning models don't always say what they think* (2025): whether verbalized reasoning faithfully acknowledges influential hints. That is not the same measurement as recalling and applying a dated user correction. https://www.anthropic.com/research/reasoning-models-dont-say-think

The candidate extension is the combination of **a user correction, its limited scope, its actual author, independent recall/choice probes, and counterbalanced arbitrary destinations**. This is a research direction, not a novelty certification; related-work coverage remains incomplete. The current task is deliberately easy and may produce no gap in capable models.

## Boundaries and next gate

The present records are short, explicit, and already supplied to the decision-maker. They do not measure long-term storage, retrieval quality, cross-session identity, free-form explanation quality, or real tool execution. The second query measures a routing-choice proxy, not a file write or external action.

Before collecting model evidence, resolve the requirements in `PROTOCOL.md`: independent design review, a separate exploratory run plan with model identity and cost ceiling, fresh stateless trials, raw-output retention, and appropriately held-out templates. Do not merge these public software checks into the original claim-bearing protocol's results or label them a completed preregistered study.

Conceptual motivation: Youngseok Oh's existing public question. Design, code, literature comparison, and execution: Zero (AI collaboration partner), within Youngseok's delegated project direction. No claim that Youngseok personally wrote or reviewed every code line, or that any cited author endorses this instrument.
