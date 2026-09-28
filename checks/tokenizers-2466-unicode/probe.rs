//! Independent differential check for Tokenizers #2466.
//! Zero × Youngseok Oh. Uses the repository's pinned 0.23.2 oracle.
#![cfg(feature = "bench-baseline")]
use std::{fs, path::Path};
use serde_json::json;
use tk_encode::pipeline::{EncodeOptions, Override};
use tokenizers_release::Tokenizer as Released;

fn compare_fixture(name: &str, file: &str) {
    let root = std::env::var("ZERO_RECEIPTS").expect("receipt directory");
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../data").join(file);
    let mut old = Released::from_file(&path).expect("0.23.2 loads exact fixture");
    old.with_padding(None);
    old.with_truncation(None).unwrap();
    let canonical = tk_convert::canonicalize_file(&path).expect("convert exact fixture");
    let pipeline = match tk_serialize::from_json(&canonical) {
        Ok(p) => p,
        Err(error) => {
            let result = json!({"fixture": name, "stage": "candidate_load", "error": error.to_string(), "sweep_executed": false});
            fs::write(Path::new(&root).join(format!("{name}.json")), serde_json::to_vec_pretty(&result).unwrap()).unwrap();
            panic!("candidate load failed: {error}");
        }
    };
    let mut inputs = Vec::new();
    let mut block = String::new();
    let mut start = 0u32;
    let mut scalar_count = 0u64;
    let mut bytes_seen = [false; 256];
    for value in 0..=0x10ffff {
        if let Some(ch) = char::from_u32(value) {
            if block.is_empty() { start = value; }
            block.push(ch);
            scalar_count += 1;
            let mut buf = [0u8; 4];
            for &byte in ch.encode_utf8(&mut buf).as_bytes() { bytes_seen[byte as usize] = true; }
            if scalar_count % 4096 == 0 {
                inputs.push((format!("U+{start:06X}..U+{value:06X}"), std::mem::take(&mut block)));
            }
        }
    }
    if !block.is_empty() { inputs.push((format!("U+{start:06X}..U+10FFFF"), block)); }
    let scalar_blocks = inputs.len();
    for n in [0usize, 1, 2, 3, 8, 16, 32, 64] {
        inputs.push((format!("spaces-{n}"), format!("a{}b", " ".repeat(n))));
        inputs.push((format!("newlines-{n}"), format!("a{}b", "\n".repeat(n))));
    }
    inputs.push(("special-adjacency".into(), "hello[CLS]world[SEP]a  b[MASK]\t\n".into()));
    let mut mismatches = Vec::new();
    let mut checked = 0;
    let mut compared_ids = 0u64;
    for (label, text) in &inputs {
        for specials in [false, true] {
            let options = EncodeOptions { add_special_tokens: specials, truncation: Override::Off, padding: Override::Off, ..EncodeOptions::default() };
            let expected = old.encode_fast(text.as_str(), specials).unwrap();
            let encodings = pipeline.encode(text.as_str(), &options).wait().unwrap();
            assert_eq!(encodings.len(), 1);
            let got: Vec<u32> = encodings[0].ids().iter().map(|id| id.id()).collect();
            let want = expected.get_ids();
            checked += 1;
            compared_ids += want.len() as u64;
            if got != want {
                let index = got.iter().zip(want).position(|(a,b)| a != b).unwrap_or(got.len().min(want.len()));
                let lo = index.saturating_sub(3);
                mismatches.push(json!({"case":label,"specials":specials,"kind":"encode_ids","first_index":index,"expected_length":want.len(),"actual_length":got.len(),"expected_context":&want[lo.min(want.len())..(index+5).min(want.len())],"actual_context":&got[lo.min(got.len())..(index+5).min(got.len())]}));
            }
            for skip in [false, true] {
                let expected_decoded = old.decode(want, skip).unwrap();
                match pipeline.decode(want, skip) {
                    Ok(actual) if actual == expected_decoded => {},
                    Ok(actual) => mismatches.push(json!({"case":label,"specials":specials,"skip_specials":skip,"kind":"decode_text","expected_bytes":expected_decoded.len(),"actual_bytes":actual.len()})),
                    Err(error) => mismatches.push(json!({"case":label,"specials":specials,"skip_specials":skip,"kind":"decode_error","error":error.to_string()})),
                }
            }
        }
    }
    assert_eq!(scalar_count, 0x110000 - 0x800);
    assert_eq!(bytes_seen.iter().filter(|&&b| b).count(), 243);
    let result = json!({"fixture":name,"stage":"completed","sweep_executed":true,"unicode_scalars":scalar_count,"scalar_blocks":scalar_blocks,"extra_inputs":inputs.len()-scalar_blocks,"input_cases":inputs.len(),"encode_comparisons":checked,"decode_comparisons":checked*2,"oracle_id_positions":compared_ids,"observed_utf8_bytes":bytes_seen.iter().filter(|&&b|b).count(),"mismatch_count":mismatches.len(),"mismatches":mismatches});
    fs::write(Path::new(&root).join(format!("{name}.json")), serde_json::to_vec_pretty(&result).unwrap()).unwrap();
    println!("SUMMARY {name} scalars={scalar_count} inputs={} encodes={checked} mismatches={}", inputs.len(), mismatches.len());
    assert!(mismatches.is_empty(), "{} mismatches; see {name}.json", mismatches.len());
}

#[test]
fn modernbert_valid_unicode() { compare_fixture("modernbert", "fixtures/models/modernbert-base.json"); }

#[test]
fn gpt2_valid_unicode_control() { compare_fixture("gpt2", "gpt2.json"); }
