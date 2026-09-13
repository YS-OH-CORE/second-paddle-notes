# Slack field check: one message, one thread, the intended request

**Status: a proposed live test, not a completed Slack run.** Start with the two direct-switch checks below. The guarded checks are optional and require an existing test configuration and an acceptable model-call budget.

This follows [josephfarina's offer to test Slack roots and replies](https://github.com/NousResearch/hermes-agent/pull/22982#issuecomment-5548412498). The implementation is [MestreY0d4-Uninter's PR #22982](https://github.com/NousResearch/hermes-agent/pull/22982). Its inspected head on 2026-09-13 was:

```text
501be10cce7159a08279c89c724db602d9770601
```

Record the actual revision being tested. That PR was still open at inspection. This document is neither a production-install instruction nor a claim that a current release contains the change. Keep an existing production workspace unchanged; use a test installation you already control, and follow the project's installation guidance rather than blindly changing branches here.

## Why a live check still matters

The candidate's [original tests](https://github.com/MestreY0d4-Uninter/hermes-agent/blob/501be10cce7159a08279c89c724db602d9770601/tests/gateway/test_model_multiline_payload.py) use Matrix-shaped events and a fixture adapter. Its [request-binding regressions](https://github.com/MestreY0d4-Uninter/hermes-agent/blob/501be10cce7159a08279c89c724db602d9770601/tests/gateway/test_model_confirmation_binding.py) exercise the dispatch/confirmation seams. Those sources do not constitute a real Slack test.

The missing observation is whether the Slack entry path, the displayed thread and the gateway session stay aligned through the full operation. Leave the model-selection guard enabled. Do not provide tokens, workspace exports, customer prompts or private identifiers to run or report this check.

## Smallest useful trial: two ordinary sends

Use a configured, affordable test-model alias in place of `YOUR_TEST_ALIAS`. The example markers are harmless text and distinguish different sends. This trial can invoke a model and therefore may consume the tester's own quota; skip it unless that is acceptable. No tool action, file change or network operation should be requested in the payload.

**R1. New root.** Send one Slack message in the chosen test channel:

```text
!model YOUR_TEST_ALIAS
Reply only with FIELD_ROOT_A. Do not use tools.
```

Observe whether the useful request remains the root, whether the acknowledgment and answer appear in the intended thread, and whether the routed user payload excludes the model directive.

**R2. Existing thread.** In a different, already-existing test thread, send:

```text
!model YOUR_TEST_ALIAS
Reply only with FIELD_REPLY_B. Do not use tools.
```

Observe the same behavior inside that thread. Check that the first thread's configured model did not change. Use existing gateway/session diagnostics for the selected model; the model saying its own name is not reliable evidence.

If either case does not produce the intended route, stop there and report the first divergence. Do not keep resending a request whose execution is uncertain. A missing Slack answer alone does not prove that a provider call never happened.

## Optional approval boundary

Run these only in an already-approved test setup where a normal selection guard actually appears. Do not enable a costly model or weaken a policy merely to manufacture a prompt. Otherwise record **not exercised**.

| Case | Action | Observation needed |
|---|---|---|
| G1: root to approval reply | Submit a fresh root with `!model YOUR_GUARDED_TEST_ALIAS` and a new harmless marker on the next line. Wait for the guard, then send `!approve` as a reply in that root's thread. | No payload dispatch before approval; the original payload reaches the agent after approval in the same thread/session. |
| G2: reply to approval reply | Repeat within an existing test thread. Approve within that same thread. | The original payload and thread are retained. |
| G3: reject | Start a new guarded test request and choose the rejection action actually offered by the gateway. | No payload dispatch. Record the actual rejection command or button, rather than assuming an alias exists. |
| G4: two pending threads | Put distinct markers in two guarded test threads. Approve only T1; reject T2 using its offered action. | T1 routes only its own marker; T2 never routes. The untouched thread's model/session state does not inherit T1's change. |

One displayed answer is not proof of one execution. If existing diagnostics expose agent-dispatch or provider-request counts, record them separately from acknowledgment and answer counts. Otherwise leave execution count **unknown**. Do not add broad logging of private conversations to obtain a number.

## Keep the shorter command request separate

[Issue #103330](https://github.com/NousResearch/hermes-agent/issues/103330) also asks for `!m ALIAS` and the compact one-line form `!m ALIAS PROMPT`. The inspected PR is described as first-line `/model` plus remaining payload. This guide deliberately tests `!model ALIAS` followed by a newline. Passing it does not establish support for `!m`, a compact one-line prompt, or every requirement of #103330.

## A reply that is useful without private logs

Copy only the rows you exercised into the existing PR discussion. Replace actual workspace/channel/thread identifiers with T1/T2; use synthetic payloads only. Do not paste credentials or a whole transcript. A screenshot may expose unrelated conversation, so a short text observation is preferable.

```text
Revision tested:
Platform: Slack
Test setup only: yes / no

Case: R1 / R2 / G1 / G2 / G3 / G4
Observed path: root / existing thread
Guard appeared: yes / no / not applicable
Acknowledgment location: expected / other / absent
Payload-answer location: expected / other / absent
Payload routed unchanged: observed yes / observed no / unknown
Selected-model/session match: observed yes / observed no / unknown
Agent dispatch count: integer / unknown
Provider request count: integer / unknown
Visible acknowledgment count:
Visible payload-answer count:
Other test thread changed: observed yes / observed no / unknown
First unexpected observation:
Not exercised:
```

A field report is a new observation, not automatic merge approval. An uneventful pair of sends is useful evidence but not a guarantee about expiry, concurrent interleavings, other platforms or future versions. The source-level controlled tests and live-platform observations answer different questions.

Prepared by Youngseok Oh with Zero (ChatGPT), as a follow-through aid. Implementation credit remains with the PR author; the Slack use case and offer to test remain with its reporter. No Slack workspace was accessed and no live test has been carried out in preparing this document.
