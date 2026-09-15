# MCP #505: Go SDK execution results

Recorded 16 September 2026. Research direction: Youngseok Oh. Verification code and analysis: Zero (ChatGPT).

## Executed scope

[Run 35035058977](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/35035058977) completed successfully. Tested verifier: `009878803b2805b3c31aeadecec52091672138fb`; source SHA-256 `52b7e1057b58b568f75a26852dc402666d4bcd0904ac2bc1681b8ea1c40cc0ff`.

Conformance: `modelcontextprotocol/conformance@7169291ec0b68eb370fddcd9947313ab0d5e4156`.
Go SDK: `modelcontextprotocol/go-sdk@fbd36cb7870176bfc3e8e423df697cf110d0f927`.
Node 22.16.0 and Go 1.25.0. The original lockfiles were retained. `go mod verify` passed.

Unlike the preceding TypeScript bundled-fixture test, this run builds the separately maintained Go SDK's own everything-server and uses the SDK's native `mcp.NewStreamableHTTPHandler`, actual HTTP and the unmodified upstream conformance CLI. The Go diagnostic source describes itself as mirroring the TypeScript fixture's behavior; this is a separate language/library execution, not independent experimental design or human review.

The conformance patch was NOT changed. Its SHA-256 remains `6b54c4129d72691775a01c911515dee4bc59036262a957e3f9bf61c0bac7faa9`.

## Results, including deliberate failures

| Go server mode / scenario | Original conformance CLI | Same CLI with the previously tested patch |
|---|---|---|
| Unmodified request-state fixture | 3/3 checks successful, exit 0 | 3/3 successful, exit 0 |
| Synthetic completion missing marker | Incorrect target SUCCESS, exit 0 | Target FAILURE, exit 1 |
| Synthetic `IsError: true`, missing marker | Incorrect target SUCCESS, exit 0 | Target FAILURE, exit 1 |
| Synthetic `IsError: true`, marker retained | Incorrect target SUCCESS, exit 0 | Target FAILURE, exit 1 |
| Unmodified multi-round fixture | 4/4 successful, exit 0 | 4/4 successful, exit 0 |
| Unmodified tampered-state fixture | 2/2 successful, exit 0 | 2/2 successful, exit 0 |

There were 12 CLI executions and 36 check records. Three FAILURES are the intended negative-control outcomes, not a falsely reported all-green suite. All 12 wire-schema checks passed; they report 52 validated JSON-RPC messages and no violations. Every target scenario's first-round prerequisite remained successful. The raw tool result in each before/after pair was identical; only the target check's interpretation changed.

The three bad server modes are deliberately injected controls, not observed bugs in the unmodified Go SDK. Each changes only one diagnostic handler's text or `IsError` field. The Go SDK library, HTTP transport, registration and JSON-RPC handling are unchanged. The unmodified source is restored, and the resulting checkout is clean. The modified handler variants and the original file are preserved in the artifact.

The positive tampered-state fixture is a diagnostic, not a proof that the SDK's test fixture supplies production-grade cryptographic state integrity. Neither this run nor the marker proves that general property.

## Retained evidence and independent inspection of its structure

Original artifact `10422569318`, 130254 bytes, SHA-256 `bd35080c25f238ade4d148274bd6d767a5a72c07b851eb798d26854f60d645bd`. Downloaded and opened, not inferred from the workflow badge.

The retained evidence was checked against the exact verifier bytes and commit, original Go Git blob `c532d438f0575e7eefbbe0b8f22a07874cdab239`, unchanged patch hash, all 12 raw `checks.json` files, the three expected nonzero CLI exits, before/after response equality, and the one-handler-only source mutations. These are local artifact-inspection checks, not a second CI run or an independent reviewer.

The previous TypeScript/full-suite workflow also reran automatically for this PR update and succeeded as run `35035058796`. Its job status was checked, but that duplicate run's assertion artifact was not re-audited for this document. The detailed 630-test result remains attributable to the prior inspected run `35029898838`; counts are not added together as independent evidence.

## Contribution status

This closes the missing separately supplied SDK execution step for the narrow candidate. The existing upstream issue is [#505](https://github.com/modelcontextprotocol/conformance/issues/505). No new upstream PR, maintainer acceptance, merge or deployment is claimed. The user's verification PR remains draft. No private records, credentials, live model calls, paid-runner configuration or existing main-branch changes are involved.

New verifier code follows Apache-2.0 contribution terms; retained Go source and dependency files preserve their existing notices and license. Artifact retention is one day on Actions; the original-byte copy is also preserved in the user-delivered archive.
