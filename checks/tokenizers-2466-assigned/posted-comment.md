**Follow-up with official Unicode data (29 September):** all seven reduced examples contain post-Unicode-9 assignments (10.0, 11.0, 12.0, 14.0 or 16.0). On an independently defined assigned9 corpus, ModernBERT and GPT-2 each agree with 0.23.2 on **164/164 encode comparisons and 328/328 reference-ID decode comparisons**. The corpus is 65 assigned-repertoire blocks plus the prior 17 controls, not all strings.

Both NFC libraries also match their tested official `NormalizationTest.txt` expectations: all 18,722 Unicode9 rows for the legacy implementation, all 20,034 Unicode17 rows for the newer one, and the shared-repertoire cross-version checks. The newer implementation separately covers the 999 Unicode17 rows excluded from the older-repertoire comparison. [Exact counts, assignment audit, code and preserved results](https://github.com/YS-OH-CORE/second-paddle-notes/blob/ff9bd3aecafd97c8c110020c038c5fdffd3823e6/checks/tokenizers-2466-assigned/README.md) | [Run 36512976120](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/36512976120).

This supports treating those seven examples as repertoire-version differences, not a defect demonstrated in this loading patch. No production code was changed. The earlier all-scalar exact-parity failure below is retained.

AI-assisted CPU verification at `cde465c9580a0b3f6831318539e3ff2360c7fb09`: the pinned ModernBERT fixture now loads; the inspected base fails on `0xC0`. I also found a separate version-sensitive boundary in comparison with the 0.23.2 oracle, not evidence of a defect introduced by this patch.

Small example with the unchanged fixture, specials/padding/truncation off:

```text
input:  U+0EB9 U+0EBA
0.23.2: [34556, 119, 34556, 120]
PR:     [34556, 120, 34556, 119]
```

I reduced seven differing Unicode blocks to two-scalar examples. For all seven, removing only NFC in a diagnostic fixture makes old/new IDs agree. An isolated dependency check, with no tokenizer or vocabulary, reproduces the decoded strings exactly: `unicode-normalization-alignments 0.1.12` reports Unicode 9.0.0; `unicode-normalization 0.1.25` reports 17.0.0. The NFC source and workspace lock are unchanged by this PR. A stable `e + U+0301` control agrees in both.

The broader corpus covers all valid scalar values in 272 blocks plus 17 extra strings, not every possible string. With specials off/on, ModernBERT has 14 differing encode comparisons out of 578; GPT-2 has none. All 1,156 decode comparisons per loaded fixture agree on reference IDs. The strict candidate parity job remains red.

[Reproducer, exact fixture hashes, counts, reductions and three execution links](https://github.com/YS-OH-CORE/second-paddle-notes/blob/cb40a3915a3db937c5c1e13ecdfaf590962d625d/checks/tokenizers-2466-unicode/README.md).

Since the corpus includes scalars unassigned in the older Unicode version, exact old-release parity is stronger than Unicode's cross-version normalization guarantee. Should the oracle distinguish these NFC-version cases from tokenizer regressions? This need not block the loading fix. No runtime change or full-compatibility claim is proposed.

Zero × Youngseok Oh
