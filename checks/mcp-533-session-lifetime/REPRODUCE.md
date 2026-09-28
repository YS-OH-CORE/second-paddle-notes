# Reproducing the PR #533 evidence

The clean follow-up is [`95dd2e2c64c7173e5f3ddfada7b03512f88eef89`](https://github.com/YS-OH-CORE/conformance/commit/95dd2e2c64c7173e5f3ddfada7b03512f88eef89). The separate verification commit is [`b3c0471b8a49620fbf69daed8359becc41cb1a70`](https://github.com/YS-OH-CORE/conformance/commit/b3c0471b8a49620fbf69daed8359becc41cb1a70); it adds only the lab and its workflow above the clean follow-up.

The exact [capacity workflow](https://github.com/YS-OH-CORE/conformance/blob/b3c0471b8a49620fbf69daed8359becc41cb1a70/.github/workflows/pr-533-capacity.yml) records the complete CI preparation. Its successful [run 36393089365](https://github.com/YS-OH-CORE/conformance/actions/runs/36393089365) used Node 24.21.0, npm 11.19.0, and Go 1.25.14 on Linux. The TypeScript dependency was SDK 1.29.0; the unchanged Go SDK checkout was `827f90ba0c13edb546028df42fadc9f1211a4ff2`.

## Real SDK server capacity matrix

With those runtimes installed, these POSIX commands reproduce the checkout arrangement in a new directory. All repositories are public. The candidate and baseline share the one installed dependency tree, as in CI.

```bash
git clone --branch ci/pr-533-capacity-20260928 https://github.com/YS-OH-CORE/conformance.git verification
git -C verification checkout --detach b3c0471b8a49620fbf69daed8359becc41cb1a70
git -C verification worktree add --detach ../candidate 95dd2e2c64c7173e5f3ddfada7b03512f88eef89
git -C verification worktree add --detach ../baseline 7169291ec0b68eb370fddcd9947313ab0d5e4156
git clone https://github.com/modelcontextprotocol/go-sdk.git go-sdk
git -C go-sdk checkout --detach 827f90ba0c13edb546028df42fadc9f1211a4ff2
npm ci --prefix candidate
ln -s ../candidate/node_modules baseline/node_modules
node verification/.github/evidence/pr-533/run-capacity-evidence.mjs \
  --candidate candidate \
  --baseline baseline \
  --candidate-sha 95dd2e2c64c7173e5f3ddfada7b03512f88eef89 \
  --baseline-sha 7169291ec0b68eb370fddcd9947313ab0d5e4156 \
  --typescript-source baseline \
  --go-sdk go-sdk \
  --sdk-modes typescript,go \
  --output capacity-results
```

The output directory must not exist. The lab builds the existing conformance CLI in each checkout, builds the Go SDK's conformance server, and launches eight fresh server/proxy/CLI combinations. It uses the unchanged bundled TypeScript server from the baseline checkout. See [lab/README.md](lab/README.md) for the proxy's admission ledger, predefined assertions, and scope.

The retained run has 94 passing experimental assertions. Both SDKs produce the same table in [capacity-results.json](capacity-results.json): clean conditions have CLI exit 0, while **both deliberately failing conditions retain CLI exit 1**. A successful experiment does not turn those negative CLI verdicts into passes. The cap and method-error injection belong to the fixture.

## Isolating the additional late-handshake guard

The ordinary capacity matrix compares the pre-fix baseline with the combined author cleanup and follow-up. To isolate the follow-up, place its identical new regression onto the unchanged original PR head:

```bash
git -C verification worktree add --detach ../original a95deff303dc2221654fe4331daf657e0f2ac690
ln -s ../candidate/node_modules original/node_modules
cp candidate/src/runner/server.session-lifetime.test.ts original/src/runner/server.session-lifetime.test.ts
npm --prefix original test -- src/runner/server.session-lifetime.test.ts --disableConsoleIntercept
```

That command is **expected to fail with exit 1**. The original runner leaves the late session live and the healthy successor receives the fixture's capacity rejection. The copied test is the only new test file in this original-head comparison. [Final original-run command, source hashes, and exit](final-original-red.json) · [Failure output](final-original-red.log)

Run the same test alongside the original author's runner tests on the candidate:

```bash
npm --prefix candidate test -- src/runner/server.test.ts src/runner/server.session-lifetime.test.ts --disableConsoleIntercept
```

The recorded candidate result is 9 passed tests. The clean candidate also passed the repository's full check/build/test gate: [626 tests across 48 files](https://github.com/YS-OH-CORE/conformance/actions/runs/36391589358). The fixture uses the real SDK client and runner, with a minimal HTTP server holding the initialized acknowledgment; it is a separate test from the real server capacity matrix.

## Complete retained records

[raw-runs.tar.gz](raw-runs.tar.gz) contains 685 original files, totaling 12,444,827 uncompressed bytes. [raw-runs-manifest.json](raw-runs-manifest.json) lists every member's size and SHA-256. Every member was read back from the finished archive and compared to its source before publication.

The archive SHA-256 is `3922083afe161dd2ea8b10fe347fa11d832aa914b6fb17484f7e1e118ca20663`.

- `local-capacity-01/`: the failed first preparation run. The `tsx` CLI could not create its local IPC socket; all four server startups failed before a conformance CLI ran. Its executed source snapshots are preserved.
- `local-capacity-02/`: the complete successful local TypeScript matrix after switching to the installed `tsx` package's supported Node import loader. Its candidate is honestly recorded as original Git HEAD plus the final source overlay.
- `ci-capacity/`: the complete extracted CI artifact, including eight runs, all existing CLI result directories, HTTP journals, server/CLI stdout and stderr, commands, source/dependency/build manifests, and runtime records. Only build caches and binaries were excluded by the original CI upload configuration.
- `ci-logs/`: full standard-CI, capacity-CI, and failed candidate package-publication logs.

The original downloaded CI ZIP's SHA-256 was independently checked against GitHub's advertised artifact digest, `1fd2d09e013321e87a3be92e8e81bfe5141116f8982b4d90412f7cca11ab15b9`. The archive preserves its extracted member bytes, not the ZIP container itself. [CI identity and artifact metadata](capacity-ci-verification.json)

The initial `tsx` launch issue, intermediate development results, and separate package-publication failure remain visible. The package service rejected publication because its app was absent from the fork; no package-publication success or upstream adoption is claimed.
