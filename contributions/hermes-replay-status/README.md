# Proposed narrow fix: structured Hermes results are not interrupt prose

This is a patch contribution, not an installed Hermes update. Prepared with Zero
(ChatGPT) for Youngseok Oh's public project. It follows the source-level report
on the related upstream discussion:
https://github.com/NousResearch/hermes-agent/pull/84236#issuecomment-5626793539

## Change

The existing classifier scans all serialized text for interrupt words/numbers.
A normal result with `exit_code: 0` can therefore be rewritten as an UNKNOWN-effect
notice when stdout quotes interruption documentation. A read-file result with a
quoted marker can be removed from the replay list.

The patch parses valid JSON and checks the **outer integer exit_code**, plus an
interrupt indication in the output/error fields, instead of using arbitrary
occurrences elsewhere in that JSON. Current exit 130 and legacy exit -1 recovery
are retained. An exit 130 without an interrupt indication is not enough.
Successful output text and document contents remain data.

The old unstructured-text fallback is intentionally unchanged. Malformed JSON,
plain-text results and text wrapped by other tools may therefore still have the
old ambiguity. This narrow fix is not authenticated stop provenance or a claim
that all replay misclassification has been removed. Changing those older formats
needs a separate compatibility decision. In particular a JSON object without an
integer execution status is not treated as an interrupted command merely because
it quotes an interrupt marker.

## Apply for review

Base: upstream `6c3d4a4af70d76b7365bf19e9420ffdcbb9830ad`.
Original replay file blob: `7af23b143e3f3c8bbc01d09c98b7be535f910961`.

In a clean disposable checkout of that revision:

```sh
git apply --check /path/to/replay_cleanup.patch
git apply /path/to/replay_cleanup.patch
scripts/run_tests.sh tests/agent/test_replay_cleanup_structured_results.py tests/agent/test_replay_cleanup.py
```

The patch changes one production function/import and adds one test file. It does
not change the related PR's stop_kind work, database schema, provider policy,
account permissions, tool execution, or the Process Receipt package.

## Check evidence rather than assuming the patch works

`verify_patch.py` performs a before/after run in a disposable upstream checkout.
It imports the real upstream classifier, message builder and replay sanitizer.
No source-function stubs or AST extraction are used in that check. New tests must
produce assertion failures on the original source, not import/collection errors;
after applying the production change all 27 in-memory cases, the supplementary
8 database-restart cases and the existing replay test file must pass. Inputs are
synthetic. Each pytest file runs in its own process with a clean environment and
upstream conftest. This uses direct per-file pytest, not the full canonical wrapper.

The original real-import verification is recorded in PR #4 and run 34546225656.
It did not test database persistence. The supplementary test adds that distinct
boundary without changing the already published production patch.

### Supplementary database-restart regression

`test_replay_cleanup_sessiondb_roundtrip.py` is offered as a separate test file.
The verifier copies it into the disposable checkout's `tests/agent/` directory;
it is not silently included in the older `replay_cleanup.patch`.

For each of eight cases it constructs a real tool message, starts a Python process
to save the synthetic history through `SessionDB.replace_messages`, closes the
database and exits, then starts a DIFFERENT Python process. The second process
reopens that database, loads the conversation through SessionDB, and runs the real
replay sanitizer. It checks the next user's exact text, the original tool payload,
the appropriate successful/interrupted behavior, and unchanged stored history.

Case receipts record process IDs, actual module paths, expected/observed replay
outcomes, row counts and preservation checks in `db-*-roundtrip.jsonl`. No private
conversation is used. An unchanged database alone is not sufficient: the replay
list is separately checked, because correct storage can still feed wrong context.

To add the supplementary test to an already patched disposable checkout, copy
this file to `tests/agent/test_replay_cleanup_sessiondb_roundtrip.py`, then run it
with the upstream test runner. The existing production patch remains unchanged.
This test does not boot the gateway or send the resulting context to any model.
The presence of the test does not prove it passed; inspect an actual CI run.

The accompanying read-only workflow downloads pinned test dependencies and the
pinned source. It has no model/gateway, account credentials, periodic schedule or
access to a user's Hermes directory. Its returned `hermes-replay-status-evidence`
artifact contains the actual XML, stdout and per-case observations. Full live
user-session behavior and provider-side decisions remain outside the test scope.

## Rights and scope

Hermes source is MIT-licensed by Nous Research; its notice is retained in
LICENSE.upstream. The proposed patch and regression tests are offered under that
same license. No private conversation, private account data or credentials are
included. The upstream maintainer has not accepted or merged this patch merely
because it is stored here. No separate human or model review is claimed.
