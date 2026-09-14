# Read-only CLI verification, 2026-09-14

Prepared by Youngseok Oh with Zero (ChatGPT).

[Run 34803598911](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/34803598911)
passed at executable head `c06e7452a899577bfe1d31bb6d6b64e6e958cae2`.
Twenty-six standard-library unit tests and four fresh CLI readbacks passed.
This is not a new response-loss or MCP experiment, not 26 provider operations,
and not evidence that the skill was installed or selected in a user's Hermes.

| Existing object / input | Observed status | Exit | GET requests |
| --- | --- | ---: | ---: |
| PR44 failed-checker marker, read via current provider branch | content_match | 0 | 4 |
| PR44 retry marker, read at its immutable commit | content_match | 0 | 3 |
| Same retry marker, deliberately wrong expected digest | content_conflict | 2 | 3 |
| Nonexistent path in that immutable tree | absent_at_snapshot | 3 | 2 |

Total: twelve GET requests; no provider writes, retries or marker creation.
Every output had retry_authorized=false. The wrong-digest and absent-path rows
are read-only controls, not conflicting files created for a new experiment.
The observed snapshot in all four rows was
`29e8975d172e53a48983a8a4a9c7104b98f1cb14`.
The older file matched even though its creation commit was no longer branch head.

The local command also returned unknown / TRANSPORT_UNAVAILABLE (exit 4) when
DNS could not resolve GitHub. It did not convert that failure into file absence.
The unit suite separately checks 404/403/429, truncation and malformed records.

## Returned bytes inspected

Artifact `10332710982`: 5,232 bytes, seven JSON/log members, SHA-256
`ebd644bfe69d08183c85ecb8b4ba7a08e85b6f789ff22f8522467d023a9acc1e`.
Downloaded readback checked ZIP CRC, each separate result against summary.json,
expected identities against the example intents, all exit/status pairs,
retry_authorized=false, the 26-test log, and the executing reader's source hash.

Reader SHA-256:
`a800e8a327d2d2b8531e9807ba9d42a8f6d20f611182a4c2a35c75ba1aac4349`.
Git blob: `c9818b4fc07cd2501bddf16868b86d29a86047ff`.
The runtime hash matched the local 9,450-byte source and connector source readback.
This archive inspection is not another live execution or independent certification.

## First run and preparation corrections

Run `34803368570` failed after its original 23 unit tests passed. The first live
CLI invocation reported LOCAL_INPUT_OR_CONFIGURATION, not a provider outcome.
Its artifact `10331962251` is retained as a failure: 1,442 bytes, SHA-256
`576ed7eaa8d2c4a91a42f752b734d1f30d5221b76a6a32ac0b519f0379df704f`.

Review found an unnecessarily narrow alphanumeric-only token validator. Tokens
are now opaque bounded visible-ASCII header values; controls and whitespace are
still rejected. Fixed diagnostic codes survive the CLI boundary, and three
configuration regressions test opaque-token syntax, missing explicit credentials,
and the public default ignoring environment tokens. No real token was inspected
or printed. The first coarse diagnostic alone cannot uniquely establish the
original token's shape. The corrected authenticated read-only run passed.

A mistakenly shortened new README was restored before the successful run; both
intermediate commits remain in history. No force update, old source replacement,
provider marker modification or user-environment change was used to repair it.

## Boundaries

Content correspondence at a pinned snapshot is the result. It is not recovery
of the lost HTTP response, attribution to a particular write, an execution count,
or permission to retry. Absence at one snapshot does not prove non-execution.
Hermes integration is an opt-in skill package, not a tested live installation.
See SKILL.md and README.md for limits and operation.
