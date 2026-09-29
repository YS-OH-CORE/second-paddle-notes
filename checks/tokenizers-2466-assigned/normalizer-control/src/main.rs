//! NFC-only comparisons with independent Unicode Consortium expected outputs.
//! Zero × Youngseok Oh. Does not modify tokenizer dependencies or production code.
use std::{collections::HashSet, fs, path::Path};
use serde_json::json;
fn old_nfc(s: &str) -> String {
    unicode_normalization_alignments::UnicodeNormalization::nfc(s).map(|(c, _)| c).collect()
}
fn new_nfc(s: &str) -> String {
    unicode_normalization::UnicodeNormalization::nfc(s).collect()
}
fn columns(line: &str) -> Option<Vec<String>> {
    let raw = line.split('#').next().unwrap().trim();
    if raw.is_empty() || raw.starts_with('@') { return None; }
    let cells: Vec<String> = raw.split(';').take(5).map(|field| {
        field.split_whitespace().map(|cp| char::from_u32(u32::from_str_radix(cp,16).unwrap()).unwrap()).collect()
    }).collect();
    assert_eq!(cells.len(),5);
    Some(cells)
}
fn check(path: &Path, label: &str, normalize: fn(&str)->String, assigned: Option<&HashSet<char>>) -> serde_json::Value {
    let text=fs::read_to_string(path).unwrap();
    let (mut rows,mut excluded,mut comparisons,mut failed)=(0usize,0usize,0usize,0usize);
    let mut examples=Vec::new();
    for (number,line) in text.lines().enumerate() {
        let Some(c)=columns(line) else { continue; };
        if assigned.is_some_and(|set| c.iter().any(|s| s.chars().any(|ch| !set.contains(&ch)))) {
            excluded+=1; continue;
        }
        rows+=1;
        // UAX #15 NFC column rules: c1,c2,c3 -> c2; c4,c5 -> c4.
        for (from,to) in [(0,1),(1,1),(2,1),(3,3),(4,3)] {
            comparisons+=1;
            if normalize(&c[from])!=c[to] {
                failed+=1;
                if examples.len()<10 { examples.push(json!({"line":number+1,"input_column":from+1,"expected_column":to+1})); }
            }
        }
    }
    assert!(rows>18000, "selected no substantial official corpus");
    json!({"label":label,"rows":rows,"excluded_rows":excluded,"nfc_column_comparisons":comparisons,"mismatches":failed,"first_mismatches":examples})
}
fn main() {
    let root=std::env::var("ZERO_INPUTS").expect("input directory");
    let root=Path::new(&root);
    let assigned:HashSet<char>=fs::read_to_string(root.join("assigned9.txt")).unwrap().chars().collect();
    assert_eq!(assigned.len(),265705);
    let p9=root.join("9.0.0-NormalizationTest.txt");
    let p17=root.join("17.0.0-NormalizationTest.txt");
    let checks=vec![
        check(&p9,"Unicode9 expectations / legacy NFC",old_nfc,None),
        check(&p9,"Unicode9 assigned-in-both expectations / newer NFC",new_nfc,Some(&assigned)),
        check(&p17,"Unicode17 expectations / newer NFC",new_nfc,None),
        check(&p17,"Unicode17 expectations restricted to assigned9 / legacy NFC",old_nfc,Some(&assigned)),
        check(&p17,"Unicode17 expectations restricted to assigned9 / newer NFC",new_nfc,Some(&assigned)),
    ];
    let ok=checks.iter().all(|r|r["mismatches"]==0);
    println!("{}",serde_json::to_string_pretty(&json!({"older_unicode_version":unicode_normalization_alignments::UNICODE_VERSION,"newer_unicode_version":unicode_normalization::UNICODE_VERSION,"assigned9_scalars":assigned.len(),"nfc_checks":checks,"all_selected_nfc_checks_pass":ok,"scope":"Five NFC column identities per included official data row, not NFD/NFKC/NFKD conformance or all strings"})).unwrap());
    assert!(ok,"NFC expectation mismatch; retain result");
}
