# PR #410 identity validation evidence

This bundle records 20 runs through the existing MCP conformance CLI: five identity values, two protocol paths, and two code revisions. All expected named-check results and comparisons passed. The CLI performed scenario execution, generated the native reports, and selected its own exit codes.

| Revision | Commit |
| --- | --- |
| Baseline | `7169291ec0b68eb370fddcd9947313ab0d5e4156` |
| Rebased candidate | `eac19c4499ebb37ea359024be9aa4cd5c401c154` |

The recorded Node version is `v24.19.0`. `provenance.json` also identifies the SHA-256 digest of each executed CLI bundle. These are observations about this candidate and these fixtures, not a claim that an upstream change has been accepted.

## What was exercised

The client path uses a **synthetic raw HTTP client**. The existing command `client --scenario initialize --spec-version 2025-11-25` starts the scenario server and passes its URL to that client. The fixture sends an actual initialize request, consumes the response, and sends the initialized notification. The named check is `mcp-client-initialization`.

The server path starts the baseline checkout's **everything-server** directly with `node --import tsx`, avoiding the `tsx` CLI's IPC launcher. A **synthetic loopback HTTP proxy** changes only the identity value in successful `server/discover` result metadata. It preserves the complete result envelope and forwards other requests and responses to the original fixture. The existing command `server --scenario server-stateless --spec-version 2026-07-28` exercises this endpoint. The named check is `sep-2575-server-identifies-in-result-meta`.

This is an identity-field experiment with explicitly controlled fixtures. It is **not independent real-SDK compatibility evidence**. Any separate Go SDK or CI validation belongs to its own evidence record.

## Results

| Identity value | Client baseline → candidate | Server baseline → candidate |
| --- | --- | --- |
| Normal string fields | SUCCESS → SUCCESS | SUCCESS → SUCCESS |
| Empty `name` | FAILURE → SUCCESS | WARNING → SUCCESS |
| Empty `version` | FAILURE → SUCCESS | WARNING → SUCCESS |
| Truthy numeric fields (`42`, `7`) | SUCCESS → FAILURE | SUCCESS → WARNING |
| Both fields missing (`{}`) | FAILURE → FAILURE | WARNING → WARNING |

Each server run emitted 30 checks. Every server SUCCESS row above had 30 SUCCESS checks; every server WARNING row had 29 SUCCESS checks and exactly one identity WARNING. All 29 non-target server check statuses matched between baseline and candidate in each case. Client runs emitted the identity check and one unchanged INFO check. No unrelated FAILURE or WARNING was observed.

The client CLI exited 1 on its FAILURE cases and 0 on its SUCCESS cases. The **single-scenario server CLI exited 0 in every case, including the identity WARNING cases**. This is a remaining behavior of that command path. The candidate's change to the multi-scenario summary exit path is not exercised by this matrix. An exit code of 0 here must not be presented as proof that every identity check passed.

**Wire-schema observation:** These raw scenario paths emitted no wire-schema check rows in any of the 20 runs. The evidence establishes the named-check behavior and its surrounding CLI report. It does not establish an additional independent wire-schema validation result.

## Files and preservation

- `raw-identity-evidence.json` contains 104 original evidence files as text records: all 20 native `checks.json` reports, per-run CLI stdout/stderr and exact execution metadata, native client stdout/stderr, discovery response captures, matrix and candidate-build logs, and the upstream fixture log. Each record includes both its original and published SHA-256 digest.
- `identity-cli-results.json` contains the completed 20-run comparison, named checks, full status counts, non-target status comparisons, and recorded CLI exit codes.
- `provenance.json` identifies the executed revisions, Node version, and CLI bundle digests.
- `scripts/identity-cases.mjs` and `scripts/synthetic-initialize-client.mjs` are the executed fixture sources.
- `scripts/validate-identity-cli.executed.mjs` archives the executed orchestration source. Its filename was changed for clarity in this publication; its only content change is the path normalization described below.
- `scripts/validate-identity-cli.parameterized.mjs` is a separately labeled convenience copy for reproduction. **This convenience copy was not run.** Only its filesystem path configuration and related environment-variable presence assertions differ. `path-configuration.diff` shows the complete difference, and `source-manifest.json` records the source digests. Reversing the declared path substitutions was checked to recover the archived original exactly.

For publication, the **exact common scratch-workspace root prefix** was replaced with `<WORKSPACE>` in all original sources, logs, captured metadata, and summary text. This is a literal prefix replacement; timestamps, ports, check outcomes, request/response content outside those paths, and other text were preserved. Original-source hashes refer to the pre-normalization bytes. Published hashes refer to the UTF-8 text stored in the corresponding published record. `<WORKSPACE>` is a location placeholder, not an executable path.

## Reproduction

Prepare two local checkouts containing the baseline and candidate commits above. Each checkout needs the dependencies from its own checked-in `package-lock.json` and a CLI built from that checkout with `npm run build`. The recorded run used Node `v24.19.0`. Do not point both variables at the same checkout or reuse a CLI bundle built from a different revision.

From this publication directory, choose a **new, empty output directory** and run:

```sh
IDENTITY_BASELINE=/absolute/path/to/baseline-checkout \
IDENTITY_CANDIDATE=/absolute/path/to/candidate-checkout \
IDENTITY_OUTPUT=/absolute/path/to/new-identity-output \
node scripts/validate-identity-cli.parameterized.mjs
```

The convenience runner locates the two fixture scripts beside itself, invokes each checkout's existing CLI, starts the baseline everything-server and loopback proxy, and captures native CLI output beneath the chosen output directory. It asserts the fixed matrix above and equality of non-target check statuses. Expected conformance failures remain native CLI failures; they are not hidden with an expected-failure configuration. The orchestration's final success means the expected experiment outcomes were observed, including the deliberate malformed-identity cases.

The published result directories are embedded in `raw-identity-evidence.json`. Each object's `path` is relative to the original evidence directory, and its `text` is the complete normalized file content. They can be extracted to a separate directory without reconstructing results from the summary.
