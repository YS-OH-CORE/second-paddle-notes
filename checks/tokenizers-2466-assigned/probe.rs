//! Real tokenizers compared only on the Unicode9 assigned repertoire and controls.
//! Zero × Youngseok Oh. Original all-scalar failures remain in the prior record.
#![cfg(feature="bench-baseline")]
use std::{fs,path::Path};
use serde_json::json;
use tk_encode::pipeline::{EncodeOptions,Override};
use tokenizers_release::Tokenizer as Released;
fn compare(name:&str,file:&str) {
    let root=std::env::var("ZERO_INPUTS").unwrap(); let root=Path::new(&root);
    let assigned:Vec<char>=fs::read_to_string(root.join("assigned9.txt")).unwrap().chars().collect();
    assert_eq!(assigned.len(),265705);
    let mut corpus:Vec<(String,String)>=assigned.chunks(4096).enumerate().map(|(i,cs)|(format!("assigned9-block-{i}"),cs.iter().collect())).collect();
    let blocks=corpus.len();
    for n in [0usize,1,2,3,8,16,32,64] {
        corpus.push((format!("spaces-{n}"),format!("a{}b"," ".repeat(n))));
        corpus.push((format!("newlines-{n}"),format!("a{}b","\n".repeat(n))));
    }
    corpus.push(("special-adjacency".into(),"hello[CLS]world[SEP]a  b[MASK]\t\n".into()));
    let path=Path::new(env!("CARGO_MANIFEST_DIR")).join("../data").join(file);
    let mut old=Released::from_file(&path).unwrap();
    old.with_padding(None);old.with_truncation(None).unwrap();
    let canonical=tk_convert::canonicalize_file(&path).unwrap();
    let new=tk_serialize::from_json(&canonical).unwrap();
    let (mut encodes,mut decodes)=(0usize,0usize); let mut mismatches=Vec::new();
    for (label,text) in &corpus {
        for specials in [false,true] {
            let options=EncodeOptions{add_special_tokens:specials,truncation:Override::Off,padding:Override::Off,..EncodeOptions::default()};
            let want=old.encode_fast(text.as_str(),specials).unwrap().get_ids().to_vec();
            let rows=new.encode(text.as_str(),&options).wait().unwrap();assert_eq!(rows.len(),1);
            let got:Vec<u32>=rows[0].ids().iter().map(|id|id.id()).collect();
            encodes+=1;
            if want!=got { mismatches.push(json!({"case":label,"specials":specials,"kind":"encode_ids","reference_count":want.len(),"candidate_count":got.len()})); }
            for skip in [false,true] {
                decodes+=1;
                let expected=old.decode(&want,skip).unwrap();
                match new.decode(&want,skip) {
                    Ok(actual) if actual==expected=>{},
                    Ok(_)=>mismatches.push(json!({"case":label,"specials":specials,"skip":skip,"kind":"decode_text"})),
                    Err(err)=>mismatches.push(json!({"case":label,"specials":specials,"skip":skip,"kind":"decode_error","error":err.to_string()})),
                }
            }
        }
    }
    let output=json!({"fixture":name,"assigned9_scalars":assigned.len(),"blocks":blocks,"extra_inputs":corpus.len()-blocks,"input_strings":corpus.len(),"encode_comparisons":encodes,"decode_comparisons":decodes,"mismatch_count":mismatches.len(),"mismatches":mismatches,"scope":"Assigned Unicode9 scalars in blocks plus 17 controls; not all Unicode9 strings or proof that tokenizer semantics are universally unchanged"});
    fs::write(root.join(format!("{name}.json")),serde_json::to_vec_pretty(&output).unwrap()).unwrap();
    println!("SUMMARY {name} encodes={encodes} decodes={decodes} mismatches={}",mismatches.len());
    assert!(mismatches.is_empty(),"assigned-repertoire comparison failed");
}
#[test] fn modernbert_assigned9(){compare("modernbert","fixtures/models/modernbert-base.json");}
#[test] fn gpt2_assigned9(){compare("gpt2","gpt2.json");}
