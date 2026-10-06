# Typed fact identity: native Rust comparison

**Zero × Youngseok Oh**

## Completed result, 6 October 2026

[Native Rust results and original logs](RESULTS.md) · [Actual run 37400848427](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/37400848427) · [Policy question and reproduction sent to Mnemo #203](https://github.com/sattyamjjain/mnemo/issues/203).

The original resolver runtime passed 9 and failed 2 of the same eleven tests; the unchanged type-sensitive candidate passed all eleven. The original six tests passed in both variants. The downloaded artifact was checked against GitHub's digest and its logs recounted. This is a native **resolver-module** result, not a full mnemo-core or database integration result, accepted fix, or portfolio claim. The first baseline test stops on its numeric/string failure, so its later boolean iterations are not claimed as separate baseline observations. This documentation-only update does not rerun the tests.

## Candidate and method

The reviewed `sattyamjjain/mnemo` source at `3d26401f73bc41eaa352372fdb00bf41d0209565` converts string, integer and boolean fact identifiers to a string before grouping. Thus number `42` and string `"42"` can share an internal group. Whether this coercion is intended policy is not confirmed. The candidate preserves JSON type in the internal grouping key while leaving the output field's textual form unchanged.

The patch is the previously prepared candidate, SHA-256 `e6d2d8891ee47b3bfbe8b9d67435e71a1f905eba42a841f4e113d82b7115dfb4`. Its resulting module SHA-256 must be `b37b59625c31ad3353cca5467ea15256c61fdd9d141c3353e3582e1802913dcd`. This comparison adds no new policy or behavioral test. It runs the same five proposed tests on both the unmodified runtime and the candidate, alongside the original six tests.

## What is actually compiled

The complete resolver module is compiled as Rust. Its public `ScoredMemory`, `SupersededRecord`, `ScoreBreakdown`, `MemoryType` and `Scope` declarations are extracted verbatim from pinned upstream files, with their attributes and fields, into a small dependency harness. No sorting, grouping, timestamp or serialization operation is mocked or rewritten in Python. Python prepares inputs and reads compiler/test outputs only.

This is **not a full mnemo-core build**, database test, retrieval-system run, compatibility certification or proof that every externally supplied record reaches this function. The crate surrounding the module is our isolated harness. The dependencies are pinned in its manifest; realized transitive versions are retained in the same Cargo.lock used by both variants. Rust is fixed to 1.90.0. The original project's much broader dependency graph is not compiled.

A successful differential check requires exactly eleven real Rust tests in both variants, exactly the two mixed-type policy assertions failing on the original runtime, all eleven passing on the candidate, and the six original tests unchanged and passing. Compiler errors, missing tests or unrelated failures cannot satisfy that condition. The design is still conditional on a type-sensitive identity policy; a green run does not establish maintainer acceptance.

## Reproduction and authorship

Run `python3 run_rust_compare.py /path/to/new-results` with Rust 1.90.0, Cargo, Git and Python 3.10+ available. Network is used only to fetch checksum-checked public source and compiler dependencies. The resolver tests themselves use synthetic records, with no model, user memory, database, credentials or production service. One standard Linux job with a ten-minute limit is configured on this branch only. There is no scheduled workflow.

Original resolver and data types belong to the Mnemo contributors under Apache-2.0; the runner downloads and retains their LICENSE with the evidence. Our Apache-2.0 candidate patch, tests and harness were prepared by Zero (AI), under Youngseok Oh's direction. No independent human review, upstream authorship or endorsement is claimed. Full license text: https://www.apache.org/licenses/LICENSE-2.0 .

Source: https://github.com/sattyamjjain/mnemo/blob/3d26401f73bc41eaa352372fdb00bf41d0209565/crates/mnemo-core/src/query/current_fact_resolver.rs
