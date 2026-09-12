'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawnSync} = require('node:child_process');
const {parseUniqueJSON, parseAndAudit, audit, LIMIT} = require('./audit.js');
const E=(type,payload)=>Object.assign({type,request_id:'A',scope:'s'},payload===undefined?{}:{payload});
const D=(payload='  한국어\n    draft only\n')=>({schema:'approval-trace-v1',events:[E('propose',payload),E('approve'),E('execute',payload)]});
function duplicate(text) {
 let found;
 assert.throws(()=>parseUniqueJSON(text), e=>{found=e; return e.code==='DUPLICATE_JSON_MEMBER';});
 assert.equal(found.unit,'UTF-16 code unit');
 assert.ok(found.first_offset < found.offset);
 assert.equal(text[found.offset],'"');
 return found;
}

test('raw cancel/approve duplicate never reaches a passing assessment',()=>{
 const text=JSON.stringify(D()).replace('"type":"approve"','"type":"cancel","type":"approve"');
 // Native parsing is deliberately not enough: its last-member behavior hides cancel.
 assert.equal(audit(JSON.parse(text)).status,'no_violation_observed');
 assert.throws(()=>parseAndAudit(text),e=>e.code==='DUPLICATE_JSON_MEMBER');
});
test('overwritten payload and top-level events are rejected',()=>{
 const valid=JSON.stringify(D('draft only'));
 duplicate(valid.replace('"payload":"draft only"','"payload":"different task","payload":"draft only"'));
 duplicate(valid.replace('"events":','"events":[],"events":'));
});
test('identical duplicates do not receive a special pass',()=>{
 duplicate('{"events":[],"events":[]}');
 duplicate('{"x":null,"x":null}');
});
test('escape-equivalent keys collide after decoding',()=>{
 for(const s of ['{"type":1,"t\\u0079pe":2}','{"\\u0074ype":1,"type":2}',
  '{"한글":1,"\\ud55c\\uae00":2}','{"😀":1,"\\ud83d\\ude00":2}',
  '{"a/b":1,"a\\/b":2}','{"a\\nb":1,"a\\u000ab":2}']) duplicate(s);
});
test('member ownership is per object including nested arrays',()=>{
 const text='{"x":[{"name":1},{"name":2}],"name":{"name":3}}';
 assert.deepEqual(parseUniqueJSON(text),JSON.parse(text));
 duplicate('{"x":[{"name":1},{"name":1,"name":2}]}');
});
test('punctuation and apparent duplicate keys inside payloads stay ordinary data',()=>{
 for(const p of ['{"type":"cancel","type":"approve"}', '"x": {}, ["q"], \\',
  '\\" : "type" : { } [ ] , \n 한글', '</script><img src=x onerror=1>']){
  const raw=JSON.stringify(D(p));assert.deepEqual(parseUniqueJSON(raw),JSON.parse(raw));
  assert.equal(parseAndAudit(raw).valid_execution_attempts,1);
 }
});
test('empty, numeric-looking and prototype-like names are safe to inspect',()=>{
 for(const key of ['', '__proto__', 'constructor', 'toString', '0']){
  const k=JSON.stringify(key);duplicate('{'+k+':1,'+k+':2}');
  assert.deepEqual(parseUniqueJSON('{'+k+':1}'),JSON.parse('{'+k+':1}'));
 }
 assert.equal({}.polluted,undefined);
});
test('canonical Unicode forms remain distinct instead of being normalized',()=>{
 const s='{"é":1,"e\\u0301":2}';assert.deepEqual(parseUniqueJSON(s),JSON.parse(s));
 const d=D('é');d.events[2].payload='e\u0301';
 assert.ok(parseAndAudit(JSON.stringify(d)).issues.some(e=>e.code==='PAYLOAD_CHANGED'));
});
test('positions identify the second name with CRLF, CR, LF and UTF-16 units',()=>{
 const raw='{\r\n  "😀":1,\r\n  "😀":2\r\n}';const e=duplicate(raw);
 assert.equal(e.line,3);assert.equal(e.column,3);
 assert.equal(e.first_offset,5);assert.equal(e.offset,raw.lastIndexOf('"😀"'));
 for(const sep of ['\n','\r','\r\n']){
  const x=duplicate('{'+sep+'"x":1,'+sep+' "x":2}');assert.equal(x.line,3);assert.equal(x.column,2);
 }
 const one=duplicate('{"😀":1,"😀":2}');assert.equal(one.column,9);
});
test('diagnostic contains positions, never the sensitive key or value',()=>{
 const key='synthetic-secret-key-91832', value='synthetic-private-value-38291';
 const raw='{'+JSON.stringify(key)+':'+JSON.stringify(value)+','+JSON.stringify(key)+':2}';
 const e=duplicate(raw), details=e.message+JSON.stringify(e);
 assert.ok(!details.includes(key));assert.ok(!details.includes(value));
});
test('native syntax errors and non-text or oversized input are still rejected',()=>{
 for(const s of ['{','{"a":1,}', '["x":1]', '{"x":undefined}', '"bad\nstring"', '{"x":1,"x":2,}'])
  assert.throws(()=>parseUniqueJSON(s),e=>e instanceof SyntaxError && !e.code);
 for(const s of [null,{},42, 'x'.repeat(LIMIT+1)])assert.throws(()=>parseUniqueJSON(s));
});
test('deep nesting uses an explicit stack, not recursive JavaScript descent',()=>{
 const n=20000; const s='['.repeat(n)+'{"x":1}' + ']'.repeat(n);
 assert.ok(Array.isArray(parseUniqueJSON(s)));
 duplicate('['.repeat(n)+'{"x":1,"x":2}' + ']'.repeat(n));
});
test('a full-size allowed text and each ordinary JSON value keep native semantics',()=>{
 const cases=['null','true','false','0','-12.25e+3','""','[]','{}','{"x":[null,true,false,1e-10]}', '"'+ 'x'.repeat(LIMIT-2)+'"'];
 for(const s of cases)assert.deepEqual(parseUniqueJSON(s),JSON.parse(s));
});
test('all existing examples agree via raw-text and object APIs apart from their shared version',()=>{
 for(const d of Object.values(require('./examples.json'))){
  const text=JSON.stringify(d);assert.deepEqual(parseAndAudit(text),audit(d));
  assert.equal(parseAndAudit(text).auditor_version,'0.1.1');assert.equal(JSON.stringify(d),text);
 }
});
test('CLI rejects ambiguity with exit2, no success JSON, and unchanged source file',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'unique-trace-'));
 try{
  const file=path.join(dir,'ambiguous.json');
  const raw=JSON.stringify(D()).replace('"type":"approve"','"type":"cancel","type":"approve"');
  fs.writeFileSync(file,raw);
  const r=spawnSync(process.execPath,[path.join(__dirname,'cli.cjs'),file],{encoding:'utf8'});
  assert.equal(r.status,2);assert.equal(r.stdout,'');assert.match(r.stderr,/Duplicate JSON object member/);
  assert.equal(fs.readFileSync(file,'utf8'),raw);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('256 deterministic mixed documents agree with Python object_pairs_hook on duplicates',()=>{
 const samples=[];
 const keys=['x','t\\u0079pe','한글','a\\/b','😀','__proto__','q\\"r',''];
 for(let i=0;i<256;i++){
  const key=JSON.stringify(keys[i%keys.length]);
  const fields=key+':'+JSON.stringify({nested:[': { " }',i]})+(i%2?','+key+':'+i:',"other":true');
  let raw='{'+fields+'}';
  for(let d=0;d<(i%7);d++)raw=d%2?'['+raw+',{"name":0}]':'{"nested":'+raw+'}';
  samples.push(raw);
 }
 const code='import json,sys\nclass Duplicate(Exception): pass\ndef pairs(items):\n d={}\n for k,v in items:\n  if k in d: raise Duplicate()\n  d[k]=v\n return d\nout=[]\nfor raw in json.load(sys.stdin):\n try: json.loads(raw,object_pairs_hook=pairs); out.append(False)\n except Duplicate: out.append(True)\nprint(json.dumps(out))';
 const ref=spawnSync('python3',['-c',code],{input:JSON.stringify(samples),encoding:'utf8'});
 assert.equal(ref.status,0,ref.stderr);const expected=JSON.parse(ref.stdout);
 const actual=samples.map(s=>{try{parseUniqueJSON(s);return false;}catch(e){assert.equal(e.code,'DUPLICATE_JSON_MEMBER');return true;}});
 assert.deepEqual(actual,expected);assert.equal(actual.filter(Boolean).length,128);
});
