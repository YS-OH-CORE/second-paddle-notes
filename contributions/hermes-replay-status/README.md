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
after applying the production change all 27 new cases and the existing replay
test file must pass. Inputs are synthetic, and each pytest file runs in its own
process with a clean environment and upstream conftest. This verification script
uses direct per-file pytest, not the full canonical wrapper or the full suite.

The accompanying public workflow downloads pinned test dependencies and the
pinned upstream source, then runs only those tests. It starts no model, gateway,
user session or external account. Inspect an actual run and its returned
`hermes-replay-status-evidence` artifact; the presence of the workflow is not a
successful result. At initial publication, full-import CI results were pending.

Tests cover structured normal results quoting interrupt markers, exact versus
substring status codes, genuine and legacy interrupt recovery, the real message
constructor and replay output, input-list preservation and the next user turn.
No SessionDB persistence or live resume behavior is established by these tests.

## Rights and scope

Hermes source is MIT-licensed by Nous Research; its notice is retained in
LICENSE.upstream. The proposed patch and regression tests are offered under that
same license. No private conversation, private account data or credentials are
included. The upstream maintainer has not accepted or merged this patch merely
because it is stored here. No separate human or model review is claimed.
