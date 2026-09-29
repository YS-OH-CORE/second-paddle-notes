# Tokenizers #2466: loading restored; separate NFC-version differences

**The sparse-byte fix restores loading of the exact ModernBERT fixture. The remaining exact-ID differences in this experiment are reproduced by the two NFC normalization dependencies alone. This is not evidence that #2466 introduced a new tokenizer defect.**

AI-assisted verification by **Zero × Youngseok Oh**, supporting [SBrandeis's PR #2466](https://github.com/huggingface/tokenizers/pull/2466) and the existing [#2447 discussion](https://github.com/huggingface/tokenizers/issues/2447). The original loading fix and existing analysis retain their authors' credit.

## Executed comparisons

The actual Rust source at base `bbccb0513ff9afda385ca5c85c66eddb1318cfc7` and PR head `cde465c9580a0b3f6831318539e3ff2360c7fb09` was compared with the repository's independent, pinned `tokenizers-release = 0.23.2` oracle. All runs used Rust/Cargo 1.93.1 on Ubuntu 24.04 x86-64. No model weights, inference, GPU tests or performance benchmark were involved.

| Source / fixture | Loading | Encode comparisons matching | Decode comparisons matching |
| --- | --- | ---: | ---: |
| Base / ModernBERT | Missing `0xC0` error | Not executed | Not executed |
| Base / GPT-2 | Loads | 578 / 578 | 1,156 / 1,156 |
| PR / ModernBERT | Loads | **564 / 578** | 1,156 / 1,156 |
| PR / GPT-2 | Loads | 578 / 578 | 1,156 / 1,156 |

[Run 36484705382](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36484705382) retains the real candidate failure. Both Cargo processes exit 101 with one passed and one failed Rust test. The base workflow is green because its driver requires the specific load failure and passing GPT-2 control. The candidate workflow is red because 14 encode comparisons differ. Finding an explanation does not turn that exact-parity check into a pass.

The corpus includes all 1,112,064 valid Unicode scalar values, including unassigned scalars, grouped into 272 ascending blocks of up to 4,096 scalars. Another 17 inputs cover whitespace repetition and special-token adjacency. The 289 strings are encoded with special-token insertion off and on. Each reference-ID sequence is decoded with special-token skipping off and on. Padding and truncation are disabled in both engines. This is not a million independent tests or exhaustive coverage of arbitrary strings.

The 14 differences are seven blocks under two special-token settings. All 17 additional inputs agree. Decoding uses the reference IDs, intentionally separating decoder compatibility from encoder differences. Machine-readable counts and reduced examples are in [observations.json](observations.json).

## Two-scalar example and isolation

For the unchanged ModernBERT fixture and no added special tokens:

```text
Input:                U+0EB9 U+0EBA
0.23.2 token IDs:      [34556, 119, 34556, 120]
PR-head token IDs:    [34556, 120, 34556, 119]
0.23.2 own-ID decode: U+0EB9 U+0EBA
PR own-ID decode:     U+0EBA U+0EB9
```

[Reduction run 36485453510](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36485453510) reduced each affected block to a two-scalar input. Deleting either scalar removes its mismatch. This is single-deletion minimality, not a claim of a unique globally minimal example. Removing only the fixture's NFC normalizer in a diagnostic copy makes all seven old/new ID pairs agree. That is an isolation control, not a proposed workaround.

[Normalization-only run 36486226275](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36486226275) uses the exact dependency versions found in the recorded Cargo lock, without a tokenizer, vocabulary or BPE engine:

| Dependency | Reported Unicode version |
| --- | --- |
| `unicode-normalization-alignments = 0.1.12` | 9.0.0 |
| `unicode-normalization = 0.1.25` | 17.0.0 |

All seven old/new normalized strings match the independently observed tokenizer decodes. A stable `e + U+0301` control becomes U+00E9 in both. The NFC source, `tk-encode/Cargo.toml`, and workspace `Cargo.lock` are byte-identical between the inspected base and PR head. The base could not load this ModernBERT fixture, so these results do not establish a normalization regression caused by this PR.

[Unicode UAX #15, Versioning and Stability](https://www.unicode.org/reports/tr15/#Versioning_and_Stability) limits cross-version normalization stability to characters assigned in both versions. A corpus containing code points unassigned in the older version need not give identical results. Therefore an exact 0.23.2 compatibility test and adoption of newer Unicode tables are separate questions. The useful maintainer question is how the v1 compatibility oracle should classify these version-sensitive cases, not whether this experiment proves newer NFC wrong.

## Reproduction and preserved evidence

Use the existing [probe](probe.rs), [runner](run.py), [reducer](reduce.rs), [reduction runner](reduce_run.py), and [isolated dependency control](normalizer-control/). The scripts add only a disposable integration test to a clean frozen source checkout; no tracked production source was changed. Actual command lines, dependency locks and source/fixture hashes are in the original artifacts.

Fixtures use the upstream dataset `hf-internal-testing/tokenizers-test-data` at revision `5f5c6524084c42a35c28c0184bea37ec2530fd7c`:

| Fixture | Bytes | SHA-256 |
| --- | ---: | --- |
| `fixtures/models/modernbert-base.json` | 2,132,967 | `9fd55248d51d33976b324fc11592e28071da7d41e0e9401dfb7082e30574b7b1` |
| `gpt2.json` | 1,355,256 | `8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6` |

The three verification-code commits are `4307b5b2a2d7eecf0fb086f5c2e5b4609cd60d76` (sweep), `48744fce5fa857490c47ad1cb4d5569c29aa24da` (reduction), and `937f05a019eb2a1c4fe046e7cde59bea5a2954c3` (normalization control). They are preserved in this commit's history.

**Storage boundary:** this directory publishes the reproducible code, this report, a derived numeric record, and [archive metadata](archive-manifest.json). It does not mirror all 39 original receipt files. Four GitHub Actions artifacts contain those original JSON files, logs, Cargo locks, full compressed stdout/stderr and labeled tail excerpts. Their stated expiration is 2026-10-28. A complete four-ZIP copy was also downloaded for the account owner. Archive SHA-256, ZIP CRC and expanded-log hashes were verified locally; that verification is not another runtime experiment.

The generated cases include rare and unassigned scalars. Natural-language failure rates, application accuracy, arbitrary invalid UTF-8, Python/Node bindings, full-suite compatibility and performance were not measured. No competing PR, production fix, model-training claim or maintainer endorsement is implied.

Original implementation: SBrandeis. Prior issue analysis: mira687; downstream loading reproduction: michaelfeil. Differential probes, reductions and reporting: **Zero × Youngseok Oh**. No new license is granted over upstream fixtures or their vocabulary data. Delivery and acceptance are recorded separately.
