//! Independent normalization-only check of the seven observed tokenizer differences.
//! Zero × Youngseok Oh. This does not change the tokenizer or its dependencies.
use serde_json::json;

fn codepoints(s: &str) -> Vec<String> {
    s.chars().map(|c| format!("U+{:04X}", c as u32)).collect()
}
fn main() {
    let pairs = [
        ("\u{0EB9}\u{0EBA}", "\u{0EBA}\u{0EB9}"),
        ("\u{1DF8}\u{1DF9}", "\u{1DF9}\u{1DF8}"),
        ("\u{10F84}\u{10F85}", "\u{10F85}\u{10F84}"),
        ("\u{11839}\u{1183A}", "\u{1183A}\u{11839}"),
        ("\u{1611E}\u{1611F}", "\u{16123}"),
        ("\u{16D67}\u{16D68}", "\u{16D68}\u{16D67}"),
        ("\u{1E5EE}\u{1E5EF}", "\u{1E5EF}\u{1E5EE}"),
    ];
    let mut records = Vec::new();
    for (input, measured_candidate_decode) in pairs {
        let old: String = unicode_normalization_alignments::UnicodeNormalization::nfc(input).map(|(c,_)| c).collect();
        let new: String = unicode_normalization::UnicodeNormalization::nfc(input).collect();
        assert_eq!(old, input, "isolated older NFC differs from earlier tokenizer observation");
        assert_eq!(new, measured_candidate_decode, "isolated newer NFC differs from earlier tokenizer observation");
        assert_ne!(old, new);
        records.push(json!({"input_codepoints":codepoints(input),"older_nfc_codepoints":codepoints(&old),"newer_nfc_codepoints":codepoints(&new),"matches_prior_tokenizer_decodes":true}));
    }
    let stable = "e\u{0301}";
    let old: String = unicode_normalization_alignments::UnicodeNormalization::nfc(stable).map(|(c,_)| c).collect();
    let new: String = unicode_normalization::UnicodeNormalization::nfc(stable).collect();
    assert_eq!(old, "\u{00E9}");
    assert_eq!(new, old);
    println!("{}", serde_json::to_string_pretty(&json!({
        "normalization_form":"NFC",
        "older_package":"unicode-normalization-alignments 0.1.12",
        "older_unicode_version":unicode_normalization_alignments::UNICODE_VERSION,
        "newer_package":"unicode-normalization 0.1.25",
        "newer_unicode_version":unicode_normalization::UNICODE_VERSION,
        "matched_reduced_examples":records.len(),
        "records":records,
        "stable_control":{"input":"e+U+0301","both_outputs":"U+00E9","passed":true},
        "scope":"Isolated exact dependency versions reproduce the seven observed normalized strings, without a tokenizer, vocabulary or BPE engine. This does not decide the intended compatibility contract."})).unwrap());
}
