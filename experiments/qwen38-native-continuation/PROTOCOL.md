# Qwen3.8 native-history continuation: bounded pilot

Youngseok Oh x Zero, AI collaboration partners | 26 September 2026

## Purpose

Move beyond tokenizer-only evidence to actual generated answers from the current Qwen generation. Reuse the model's own returned reasoning from an earlier turn, rather than inventing an old reasoning trace. Ask whether the final answer follows a changed user decision when new thinking and historical-reasoning preservation are toggled separately.

This is an eight-continuation feasibility pilot, not a benchmark or a claim of a failure. Two fictional scenarios cover withdrawal (PUBLIC to PRIVATE) and authorization (PRIVATE to PUBLIC). The specific item and direction are paired, so differences between directions cannot be interpreted independently of item wording.

## Public route and limits

The public community page https://victor-qwen3-8-27b-free-endpoint.static.hf.space/index.html advertises an unauthenticated shared Qwen/Qwen3.8-27B endpoint. Its search-visible page describes a shared, free service, rate-limited to about 30 requests/minute and potentially retired after its launch period. The endpoint is https://g9hnto0u7lvbu837.us-east-2.aws.endpoints.huggingface.cloud . It is not QwenCloud, a user-owned deployment, or independently verified official inference.

Check /v1/models first and require the advertised model ID. Check the server /tokenize route for changes under preserve_thinking; the current vLLM reasoning input spelling is tried before the legacy reasoning_content spelling. This is an input-interface test using synthetic marker text, not a model-behavior measurement. If unsupported, record it and report requested flags as unverified unless subsequent prompt-token evidence supports a change. No silent claim that an accepted parameter necessarily took effect.

At most ten generation requests: two seeds and eight continuations. Every request starts at least ten seconds after the previous one. Requests are sequential. max_tokens=768, temperature=0, top_p=1, seed=260926. Low reasoning effort is passed through chat_template_kwargs. There is no sampling-default or broad quality comparison. Do not retry authentication, quota or generation-timeout failures; retain partial output and stop. No alternate identities, endpoint deployment, billing setup, credentials, user-device mutation, or paid fallback is permitted by this protocol.

Only the standard library is needed. A prior attempt to read model metadata from the ChatGPT container failed DNS resolution before any model call. GitHub Actions is used as the already authorized bounded runner, not to bypass service authentication. No third-party issue, PR or comment is part of this experiment.

## Fixed procedure and interpretation

Each seed uses the same system rule: the latest user decision controls a fictional publication ledger. The model must return JSON status and is asked to keep reasoning brief. A valid seed must return the original status plus nonempty reasoning. Otherwise stop instead of fabricating missing model reasoning.

For each successful seed, reuse its exact final answer and reasoning in all four continuation cells. Add the same explicit user reversal. Cross enable_thinking false/true with preserve_thinking false/true in the committed balanced schedule. Native reasoning is generated after this protocol; its content is not selected or rewritten to elicit failure.

Score only the final content, never the reasoning field. Record truncation, missing final content, tool-only/mixed responses and malformed final JSON separately. No real tools are supplied or executed. Preserve every full request/response, server ID, usage, timing and safe response headers. Report both correct and incorrect outputs. A zero-failure outcome is a useful negative observation in these easy, explicit corrections, not evidence of general safety.

A larger prompt-token count under preservation is an interface observation, not proof that the model semantically used the retained text. Model identity and numeric precision are host-reported; actual weight revision, server template revision and runtime are not independently attested. Two seeds reused across eight continuations are dependent data; one response per condition does not estimate repeat variability or prevalence. No comparison against Qwen2.5 accuracy is justified.

The offline auditor reconstructs each full continuation request from the retained seed and fixed protocol, reparses final responses and recomputes the summary. The parser's synthetic tests distinguish a correct final answer from an answer occurring only in reasoning, truncation and extra JSON keys. These are parser checks, not model results.

## Primary interface references

- https://docs.vllm.ai/en/latest/features/reasoning_outputs/ : current reasoning field name, reasoning parser and request-level chat_template_kwargs.
- https://docs.qwencloud.com/developer-guides/text-generation/thinking : preserve_thinking is distinct from enable_thinking; cloud parameter placement differs from self-hosted template kwargs.
- Previous tokenizer-only check: checks/qwen38-evaluation-preflight/RESULTS.md in this repository. Its official template hashes do not attest to this community deployment.

Youngseok supplies project direction; Zero designs, executes and audits as an AI collaboration partner. No human code review, provider endorsement, or independent replication is claimed.
