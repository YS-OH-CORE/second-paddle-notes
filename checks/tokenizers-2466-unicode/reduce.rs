//! Diagnostic reduction of the observed #2466 Unicode oracle differences.
//! Zero × Youngseok Oh. No runtime implementation change.
#![cfg(feature = "bench-baseline")]
use std::{fs, path::Path};
use serde_json::json;
use tk_encode::pipeline::{EncodeOptions, Override};
use tokenizers_release::Tokenizer as Released;

fn shrink(mut chars: Vec<char>, differs: &impl Fn(&str) -> bool) -> (String, usize) {
    let mut n = 2;
    let mut checks = 0;
    while chars.len() >= 2 {
        let chunk = chars.len().div_ceil(n);
        let mut reduced = false;
        for from in (0..chars.len()).step_by(chunk) {
            let to = (from + chunk).min(chars.len());
            let candidate: Vec<char> = chars[..from].iter().chain(chars[to..].iter()).copied().collect();
            checks += 1;
            if differs(&candidate.iter().collect::<String>()) {
                chars = candidate;
                n = n.saturating_sub(1).max(2);
                reduced = true;
                break;
            }
        }
        if !reduced {
            if n >= chars.len() { break; }
            n = (n * 2).min(chars.len());
        }
    }
    (chars.iter().collect(), checks)
}

#[test]
fn reduce_observed_unicode_differences() {
    let root = std::env::var("ZERO_RECEIPTS").unwrap();
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../data/fixtures/models/modernbert-base.json");
    let fixture: serde_json::Value = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
    let mut old = Released::from_file(&path).unwrap();
    old.with_padding(None); old.with_truncation(None).unwrap();
    let canonical = tk_convert::canonicalize_file(&path).unwrap();
    let new = tk_serialize::from_json(&canonical).unwrap();
    let options = EncodeOptions { truncation: Override::Off, padding: Override::Off, ..EncodeOptions::no_specials() };
    let ids_new = |text: &str| -> Vec<u32> { new.encode(text, &options).wait().unwrap()[0].ids().iter().map(|i| i.id()).collect() };
    let ids_old = |text: &str| -> Vec<u32> { old.encode_fast(text, false).unwrap().get_ids().to_vec() };
    let differs = |text: &str| ids_old(text) != ids_new(text);
    let mut no_norm = fixture.clone();
    no_norm["normalizer"] = serde_json::Value::Null;
    let no_norm_path = Path::new(&root).join("modernbert-diagnostic-no-normalizer.json");
    fs::write(&no_norm_path, serde_json::to_vec(&no_norm).unwrap()).unwrap();
    let mut control_old = Released::from_file(&no_norm_path).unwrap();
    control_old.with_padding(None); control_old.with_truncation(None).unwrap();
    let control_canonical = tk_convert::canonicalize_file(&no_norm_path).unwrap();
    let control_new = tk_serialize::from_json(&control_canonical).unwrap();
    let ranges = [(0x0, 0xfff), (0x1000, 0x1fff), (0x10800,0x117ff), (0x11800,0x127ff), (0x15800,0x167ff), (0x16800,0x177ff), (0x1d800,0x1e7ff)];
    let mut records = Vec::new();
    for (start,end) in ranges {
        let input: Vec<char> = (start..=end).filter_map(char::from_u32).collect();
        assert!(differs(&input.iter().collect::<String>()));
        let (small, checks) = shrink(input, &differs);
        let expected = ids_old(&small);
        let actual = ids_new(&small);
        assert_ne!(expected, actual);
        let chars: Vec<char> = small.chars().collect();
        let minimal = (0..chars.len()).all(|i| !differs(&chars[..i].iter().chain(chars[i+1..].iter()).collect::<String>()));
        let control_expected = control_old.encode_fast(small.as_str(),false).unwrap().get_ids().to_vec();
        let control_actual: Vec<u32> = control_new.encode(small.as_str(), &options).wait().unwrap()[0].ids().iter().map(|i|i.id()).collect();
        records.push(json!({"original_range":[start,end],"input":small,"codepoints":chars.iter().map(|c|format!("U+{:04X}",*c as u32)).collect::<Vec<_>>(),"scalars":chars.len(),"reduction_checks":checks,"one_deletion_minimal":minimal,"reference_ids":expected,"candidate_ids":actual,"reference_decoded":old.decode(&expected,false).unwrap(),"candidate_decoded":new.decode(&actual,false).unwrap(),"without_normalizer_ids_equal":control_expected==control_actual,"without_normalizer_reference_ids":control_expected,"without_normalizer_candidate_ids":control_actual}));
    }
    let result = json!({"fixture_normalizer":fixture["normalizer"],"comparisons":records,"scope":"Deterministic deletion-minimal examples for seven observed blocks; normalizer removal is diagnostic data alteration, not a proposed workaround"});
    fs::write(Path::new(&root).join("reduction.json"),serde_json::to_vec_pretty(&result).unwrap()).unwrap();
    fs::remove_file(no_norm_path).unwrap();
    println!("REDUCTION {}",result);
}
