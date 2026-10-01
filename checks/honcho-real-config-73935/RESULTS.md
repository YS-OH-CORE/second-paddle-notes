# Honcho PR73935: real disk configuration and startup upload checks

**Completed on the pinned proposed fix: four configuration cases passed. Two deliberately broken local variants were detected by the same unchanged test.** This is test coverage for an existing implementation, not a new fix or a live-service privacy certification.

- Upstream target: `saurabhmeddo/hermes-agent` at `91b3b31dc91aec04abac8be5d240f2d0ad491054`.
- Existing automated review request: https://github.com/NousResearch/hermes-agent/pull/73935#discussion_r3684494258 . It is explicitly an automated review, not a personal message or endorsement from the account holder.
- Test/runner source: `bd62b97a953ca19a73186617f447ee3c5b4c4a3c` in `YS-OH-CORE/second-paddle-notes`.
- Completed run: https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36358747015 . Job `108731565844` contains original stdout and expected-failure traces.

## Actual local path, synthetic remote service

The fixture writes `honcho.json` and three synthetic memory files under temporary HOME/HERMES_HOME, then imports and calls the real provider. The config loader, session-name resolution, session manager, and memory-file migration functions are not replaced. The SDK factory and remote object graph are test doubles; socket connect methods are guarded. The test asserts provider readiness and a context read before counting uploads so an inactive provider cannot falsely pass.

| Root saveMessages | Host saveMessages | Resolved value | Startup file upload calls |
|---|---|---|---:|
| false | absent | false | 0 |
| true | false | false | 0 |
| false | true | true | 3 |
| absent | absent | true | 3 |

Enabled cases verify names and synthetic payloads for MEMORY.md, USER.md and SOUL.md. Config bytes remain unchanged. Results: **4 passed in 0.94s**.

## Does the test notice a broken connection?

Two variants run separately in a temporary checkout, restoring the originals between them:

1. Bypass only the startup automatic-persistence guard. Both disabled-setting cases now fail at the no-upload assertion, with three actual mock upload calls shown in the trace; enabled cases still pass.
2. Force the loader's resolved save_messages to True. Both disabled-setting cases fail at the resolved-config assertion; enabled cases still pass.

Each variant produced **2 expected assertion failures and 2 passes**, in 0.57s. No setup error was counted as detection. The runner checked all four case identities in each variant and confirmed both source files were restored. These are four unique configuration cases exercised under three implementations, not twelve distinct discovered bugs. The deliberately broken variants are not proposed upstream changes.

## Setup history and resource boundaries

Two earlier hosted attempts stopped before pytest. Run `36358248219` exceeded the 64 MiB whole-archive cap; run `36358576690` still selected too much source/config data. The completed attempt selected only Python import packages via shallow, blob-filtered sparse checkout: 826 files / 29,245,540 source bytes, plus 9,368,625 Git metadata bytes. The three target modules matched their pinned Git blob IDs. The limit was not raised, and the test source was unchanged through all attempts.

Runtime: hosted Ubuntu 24.04.5, Python 3.12.14, honcho-ai 2.2.0, pytest 8.4.2, PyYAML 6.0.2, python-dotenv 1.1.1, rich 14.1.0. The completed job took about 18 seconds including setup. The two earlier failed setup jobs remain visible, rather than being described as passes.

No user PC, private memory, model execution, paid model API, live Honcho server, or operational configuration was used. Standard public GitHub-hosted runner only. No Actions artifact/cache upload or scheduled execution was added. The gate does not run again on later result edits.

## Limits and reuse

This directly addresses the on-disk setting to startup-content-upload connection requested on the old PR head. It does **not** test current Hermes main, the newer standalone handoff plugin, actual Honcho transport, OAuth/token handling, CLI/gateway admission, full lifecycle hooks, or concurrent profiles. Remote peer/session metadata calls still occur in this fixture. The automatic-persistence setting is not being presented as a universal no-network switch. The PR's explicit-tool behavior is not changed by this test.

Use `test_real_config.py` in a checkout with the target's dependencies to inspect or adapt the regression. `run_check.py` reproduces the pinned source check plus deliberate detector controls; it downloads public source and should be run in a disposable environment. Our direct pytest invocation uses `--noconftest`, so this is not a full upstream suite pass.

`OBSERVED.json` is an analyst-created structured summary of the returned log fields, not a downloaded raw Actions log. Original detailed outputs remain in the run, subject to GitHub retention. Local Python compilation and sparse-pattern checking did not substitute for the hosted runtime tests.

Test design, execution and analysis: Zero, with Youngseok Oh's project direction. The implementation under test belongs to its original author. No external adoption, merge, endorsement or new vulnerability claim is made.
