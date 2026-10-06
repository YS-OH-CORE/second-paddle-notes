# Completed native Rust comparison

**Zero × Youngseok Oh | 6 October 2026**

The [actual hosted run 37400848427](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/37400848427) completed successfully. It ran harness commit `4442894179c7900c2f6823ac96828ed561c9de2f` using Rust 1.90.0 on Linux. This replaces the previously unexecuted status for the **isolated resolver-module tests**, not for full-project integration.

## Actual test outcomes

| Same eleven Rust tests | Original resolver runtime | Type-sensitive candidate |
|---|---:|---:|
| Original six tests | 6 passed | 6 passed |
| Five proposed regression/control tests | 3 passed, 2 failed | 5 passed |
| **Total** | **9 passed, 2 failed** | **11 passed, 0 failed** |

No tests were ignored or filtered out. The original runtime is unchanged before its test section; the same five new tests are appended to both variants. The candidate bytes match the previously prepared file exactly, SHA-256 `b37b59625c31ad3353cca5467ea15256c61fdd9d141c3353e3582e1802913dcd`. No change was made to the patch merely to get this run to pass.

The two baseline failures are:

- `different_json_types_with_equal_text_remain_separate_facts`: after JSON serialization/deserialization, a numeric fact ID `42` and a textual `"42"` retain only the newer textual record. The test expected both original records to remain, in score order.
- `supersession_stays_inside_each_json_identity_type`: four records representing two numeric versions and two textual versions retain only record `[4]`, instead of the latest record from each type `[2, 4]`.

The first baseline test stops on its first failing numeric/string pair. Its later boolean/string iterations were **not all reached in the baseline**. All iterations completed successfully on the candidate. The native result should not be inflated into three independently executed baseline collision reports.

These assertions express a **type-sensitive identity policy**, not a maintainer-approved contract. The observed grouping behavior is established; whether cross-type coercion is intentional remains a design question. This is an opt-in read post-processor. No disk deletion or cross-user access was tested or claimed.

## What was compiled, and what was not

The complete `current_fact_resolver.rs` module from `sattyamjjain/mnemo@3d26401f73bc41eaa352372fdb00bf41d0209565` was compiled as Rust. Its five supporting public type declarations were extracted verbatim from pinned upstream files, including their attributes and fields. They were placed in a small, explicit harness with the original module paths. Python fetched sources, applied the candidate patch and checked outcomes; it did not emulate the resolver.

This was **not the full mnemo-core crate**. The storage backends, embedding providers, public client/server transport and complete recall path were not built or executed. No external user database, model service or production configuration was used. The same Cargo.lock was used on both variants, with `serde 1.0.228`, `serde_json 1.0.145` and `uuid 1.18.1`; this harness lock is not the upstream project's dependency lock.

## Downloaded evidence was checked again

[Original artifact](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/37400848427/artifacts/11385072523): ID `11385072523`, 52,467 bytes, SHA-256 `af497e66b2267a0123fddffc629abafe388a522cd0be092329cb8c5e14c77912`.

The original ZIP was downloaded, its digest compared with GitHub's artifact metadata, and its ZIP CRC verified. Both raw compiler/test logs were separately recounted: eleven test identities in each, 9/2 versus 11/0, with the actual mismatch outputs inspected. The original module, previous candidate, original six tests, same five added tests, shared type files and dependency lock were compared byte-for-byte. This second pass is artifact analysis, not another Rust execution or independent human review.

The ZIP contains both logs, the generated harness sources, pinned original source files, all three lockfile copies, source license, and the run receipt. The GitHub artifact has a fourteen-day retention period; the downloaded ZIP is also included in the conversation's evidence package. No private archive, personal conversation or local credentials were published here.

## Next decision

If fact identifiers should retain JSON type, this candidate supplies a tested module-level change. If numeric `42` and textual `"42"` intentionally name the same fact, documenting that coercion or adding an explicit policy option may be more appropriate. Full-crate formatting, tests and storage/recall integration remain before an upstream patch could be represented as complete.

The source resolver belongs to the Mnemo contributors. The conditional candidate, additional tests and comparison harness were prepared by Zero (AI) under Youngseok Oh's direction. This result is not an upstream merge, new co-authorship credit, portfolio acceptance or endorsement.
