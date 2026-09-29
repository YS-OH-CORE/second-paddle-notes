# Tokenizers #2466: testing the shared assigned repertoire

This follow-up answers the remaining version boundary in [our earlier report](../tokenizers-2466-unicode/README.md). Every one of its seven reduced examples contains a character assigned after Unicode 9. With inputs restricted independently to the Unicode 9 assigned repertoire, the real ModernBERT and GPT-2 tokenizers agree with the released 0.23.2 oracle on the selected corpus. Both normalization libraries also match the official NFC expected outputs in their tested version ranges.

This is a new positive control and an assignment audit, not a runtime fix or a relabeling of the earlier failed comparison. SBrandeis's existing sparse-byte loading fix is unchanged. Independent tests and report: **Zero × Youngseok Oh**.

## Executed result

[Run 36512976120](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36512976120), verifier `a9c2ee0abb0a19cbc4689b27b3a8764c3cb6f53c`, tests unchanged Tokenizers PR head `cde465c9580a0b3f6831318539e3ff2360c7fb09`. Rust/Cargo 1.93.1, Ubuntu 24.04 x86-64, actual Rust tokenizers, no model weights or GPU execution.

| Actual tokenizer comparison | Encode IDs | Decode on reference IDs |
| --- | ---: | ---: |
| ModernBERT versus 0.23.2 | 164 / 164 agree | 328 / 328 agree |
| GPT-2 versus 0.23.2 | 164 / 164 agree | 328 / 328 agree |

There are two passing Rust integration tests. Each wraps many comparisons; the table does not count 984 independent unit tests. The normalization-only executable and Cargo test both exit 0. No tracked production source is changed.

The corpus has 265,705 Unicode 9 assigned scalar values, including private-use and control characters, excluding surrogates. These are grouped into 65 ascending blocks of up to 4,096 scalars, with the same 17 whitespace/special-token controls from the earlier run. Thus 82 strings, each with special-token insertion off/on, give 164 encode comparisons. Both special-token skipping settings are used to decode reference IDs. Padding and truncation are disabled. This is not every possible string over that repertoire.

## What the seven earlier examples contain

The dates below come from the pinned official Unicode 17 DerivedAge data, cross-checked with UnicodeData 9 and 17. Full names, combining classes and mappings are in [assignment-audit.json](assignment-audit.json).

| Earlier reduced input | Assignment after Unicode 9 |
| --- | --- |
| U+0EB9 U+0EBA | U+0EBA: 12.0; U+0EB9 was already present in 1.1 |
| U+1DF8 U+1DF9 | Both: 10.0 |
| U+10F84 U+10F85 | Both: 14.0 |
| U+11839 U+1183A | Both: 11.0 |
| U+1611E U+1611F | Both: 16.0 |
| U+16D67 U+16D68 | Both: 16.0 |
| U+1E5EE U+1E5EF | Both: 16.0 |

For example, the older library treats U+0EBA as unassigned with combining class zero, whereas its assigned Unicode 17 class is 9. U+0EB9 has class 118 in both versions. The earlier order difference therefore crosses an assignment-version boundary.

[UAX #15 section 3](https://www.unicode.org/reports/tr15/#Versioning_and_Stability) guarantees normalization-process stability, for versions 4.1 onward, when the string contains only characters assigned in both versions. The membership restriction here is defined from independent Unicode data, not by deleting individual failed cases until a test turns green.

## NFC against official expected outputs

The reference dependency is `unicode-normalization-alignments = 0.1.12` (Unicode 9); the newer one is `unicode-normalization = 0.1.25` (Unicode 17). The following comparisons use Unicode Consortium `NormalizationTest.txt` expected columns, not one library grading the other.

| Official input corpus / implementation | Included rows | Excluded rows | NFC column comparisons | Differences |
| --- | ---: | ---: | ---: | ---: |
| Unicode 9 / legacy NFC | 18,722 | 0 | 93,610 | 0 |
| Unicode 9 / newer NFC | 18,722 | 0 | 93,610 | 0 |
| Unicode 17 / newer NFC | 20,034 | 0 | 100,170 | 0 |
| Unicode 17, assigned9 only / legacy NFC | 19,035 | 999 | 95,175 | 0 |
| Unicode 17, assigned9 only / newer NFC | 19,035 | 999 | 95,175 | 0 |

Each included row checks five NFC identities: columns 1, 2 and 3 normalize to column 2; columns 4 and 5 normalize to column 4. The combined 477,740 comparisons reuse overlapping rows across implementations and corpora. They are not 477,740 unrelated tests, a full Unicode conformance certification, or an NFD/NFKC/NFKD result.

The 999 exclusions in the last two rows are exactly the official rows with at least one scalar outside Unicode 9 anywhere in the five columns. The newer implementation is separately checked on every row of the Unicode 17 file, including those 999. [Exact result](normalization-result.json).

## Reproduction and evidence

The [runner](run.py) downloads five official UCD files from their versioned 9.0.0/17.0.0 directories and verifies their SHA-256 before use. The two tokenizer fixtures use the same fixed upstream dataset revision and digests as the earlier experiment. All URLs and digests are in [SUMMARY.json](SUMMARY.json). No Python host Unicode database is used to decide membership or expected normalization.

From a clean full Tokenizers checkout at the pinned PR head, with Rust 1.93.1 installed:

```sh
python run.py /path/to/tokenizers /path/to/new/receipts
```

The standalone NFC source is in [normalizer-control/](normalizer-control/); the real tokenizer test is [probe.rs](probe.rs). The pinned workflow is `.github/workflows/tokenizers-2466-assigned.yml`. The runner removes only the temporary test it created, records the final tracked-source diff, and retains both Cargo lock files. A failure remains a failure; no retries were requested.

One GitHub artifact, `11009343315`, contains all 26 receipt/input files. Its ZIP is 6,735,726 bytes, SHA-256 `b1dc36f46f36d73dcc8baa87434e7f307630ea0b59711f19d9de72b904802dde`, and its reported expiration is 2026-10-29. The archive was downloaded and checked for SHA-256, ZIP CRC, and expanded stdout/stderr hashes. The account-owner copy is also provided separately. The public directory mirrors the JSON results and provenance, not the large Unicode input files or full compressed runtime logs. Tail files in the artifact are excerpts; their companion gzip files contain the full original logs.

## Interpretation and limits

The earlier 14 ModernBERT exact-ID differences remain in the original all-scalar report and failed run. Nothing here proves parity for all Unicode strings, all models, other bindings, hardware targets, throughput, or downstream model accuracy. This is one completed follow-up experiment.

The stronger supported conclusion is that all seven reduced discrepancies cross a post-9 character-assignment boundary; the selected shared-repertoire tokenizer inputs agree; and both normalization dependencies match the stated official NFC expectations. These findings do not support blaming the sparse-byte loading patch for those differences. The project still decides whether migration promises exact legacy behavior or newer normalization semantics.

Original loading fix: SBrandeis. Earlier independent diagnosis and this follow-up verification: **Zero × Youngseok Oh**. AI assistance was used for test design, execution setup, analysis and reporting. No new upstream PR is opened, and no maintainer acceptance is claimed. Any update to the existing upstream comment is recorded separately in `delivery.json`.
