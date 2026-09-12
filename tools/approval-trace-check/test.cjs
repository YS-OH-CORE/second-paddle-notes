'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {spawnSync} = require('node:child_process');
const os = require('node:os');
const path = require('node:path');
const {audit, parseAndAudit, LIMIT} = require('./audit.js');
const examples = require('./examples.json');
const E = (type,id='A',scope='s',payload='text')=>Object.assign({type,request_id:id,scope},['propose','execute'].includes(type)?{payload}:{});
const D = (...events)=>({schema:'approval-trace-v1',events});
const C = doc=>audit(doc).issues.map(x=>x.code);

test('valid complete trace and exact Korean whitespace',()=>{
 const r = audit(examples.valid);assert.equal(r.status,'no_violation_observed');assert.equal(r.valid_execution_attempts,1);
});
test('old payload with a new approval',()=>assert.deepEqual(C(examples.stale),['PAYLOAD_CHANGED']));
test('execution after cancellation',()=>assert.ok(C(examples.cancel).includes('NOT_APPROVED')));
test('execution after expiry',()=>assert.ok(C(D(E('propose'),E('approve'),E('expire'),E('execute'))).includes('NOT_APPROVED')));
test('repeated execution consumes rather than renews the approval',()=>{
 const r=audit(examples.repeat);assert.equal(r.execution_attempts,2);assert.equal(r.valid_execution_attempts,1);assert.ok(C(examples.repeat).includes('REPEATED_EXECUTION'));
});
test('two scopes do not supersede one another',()=>assert.equal(audit(examples.scopes).valid_execution_attempts,2));
test('request replaced after approval',()=>assert.ok(C(D(E('propose'),E('approve'),E('propose','B'),E('execute'))).includes('NOT_CURRENT')));
test('late approval cannot revive an old request',()=>assert.ok(C(D(E('propose'),E('propose','B'),E('approve'),E('execute'))).includes('NOT_APPROVED')));
test('approval on the wrong scope has no authority',()=>{
 const r=audit(D(E('propose'),E('approve','A','other'),E('execute')));assert.equal(r.valid_execution_attempts,0);assert.ok(r.issues.some(x=>x.code==='SCOPE_MISMATCH'));
});
test('wrong-scope execution still counts as an attempt',()=>{
 const r=audit(D(E('propose'),E('approve'),E('execute','A','other'),E('execute')));assert.equal(r.valid_execution_attempts,0);assert.ok(r.issues.some(x=>x.code==='REPEATED_EXECUTION'));
});
test('duplicate proposal IDs cannot replace the original text',()=>{
 const r=audit(D(E('propose'),E('propose','A','s','changed'),E('approve'),E('execute','A','s','changed')));assert.ok(r.issues.some(x=>x.code==='DUPLICATE_ID'));assert.ok(r.issues.some(x=>x.code==='PAYLOAD_CHANGED'));
});
test('execution without proposal or approval is visible',()=>{
 assert.deepEqual(C(D(E('execute'))),['UNKNOWN_REQUEST']);assert.ok(C(D(E('propose'),E('execute'))).includes('NOT_APPROVED'));
});
test('failed execution cannot become authorized retroactively',()=>{
 const r=audit(D(E('propose'),E('execute'),E('approve'),E('execute')));assert.equal(r.valid_execution_attempts,0);
});
test('whitespace, normalization and empty strings are not silently changed',()=>{
 for(const [a,b] of [['x\n','x'],['  x','x'],['é','e\u0301'],['😀','😃']]) assert.ok(C(D(E('propose','A','s',a),E('approve'),E('execute','A','s',b))).includes('PAYLOAD_CHANGED'));
 assert.equal(audit(D(E('propose','A','s',''),E('approve'),E('execute','A','s',''))).valid_execution_attempts,1);
});
test('missing execution is not a successful job',()=>{
 assert.equal(audit(D()).status,'no_execution_observed');assert.equal(audit(D(E('propose'),E('approve'))).status,'no_execution_observed');
});
test('dangerous property names are ordinary request IDs',()=>{
 const r=audit(D(E('propose','__proto__'),E('approve','__proto__'),E('execute','__proto__')));assert.equal(r.valid_execution_attempts,1);assert.equal({}.state,undefined);
});
test('HTML and command strings are never executed or copied to report',()=>{
 const payload='<img src=x onerror="globalThis.INJECTED=1">; throw new Error("x")';
 const r=audit(D(E('propose','A','s',payload),E('approve'),E('execute','A','s',payload)));
 assert.equal(r.status,'no_violation_observed');assert.equal(globalThis.INJECTED,undefined);assert.ok(!JSON.stringify(r).includes(payload));
});
test('input structure rejects unknown fields and event types',()=>{
 for(const d of [null,[],{},D({type:'grant',request_id:'A',scope:'s'}),D({...E('propose'),hidden:true}),{...D(),extra:true},D({...E('execute'),payload:3}),D({...E('approve'),payload:'text'}),D({...E('approve'),request_id:''})]) assert.throws(()=>audit(d));
});
test('UTF-8 text size, event limit and malformed JSON fail before assessment',()=>{
 assert.throws(()=>parseAndAudit('x'.repeat(LIMIT+1)));assert.throws(()=>parseAndAudit('{'));assert.throws(()=>audit({schema:'approval-trace-v1',events:Array(3001).fill(E('approve'))}));
});
test('auditing does not mutate the supplied trace',()=>{
 const before=JSON.stringify(examples.stale);audit(examples.stale);assert.equal(JSON.stringify(examples.stale),before);
});
test('all 6 orderings of one request require propose, approve, execute order',()=>{
 const events=[E('propose'),E('approve'),E('execute')];let clean=0;
 for(let a=0;a<3;a++)for(let b=0;b<3;b++)for(let c=0;c<3;c++)if(new Set([a,b,c]).size===3)clean+=audit(D(events[a],events[b],events[c])).status==='no_violation_observed';
 assert.equal(clean,1);
});
test('all 20 merges of two ordered three-event scopes preserve both requests',()=>{
 const a=[E('propose','A','x'),E('approve','A','x'),E('execute','A','x')];const b=[E('propose','B','y'),E('approve','B','y'),E('execute','B','y')];let n=0;
 function walk(i,j,out){if(i===3&&j===3){assert.equal(audit(D(...out)).valid_execution_attempts,2);n++;return;}if(i<3)walk(i+1,j,[...out,a[i]]);if(j<3)walk(i,j+1,[...out,b[j]]);}
 walk(0,0,[]);assert.equal(n,20);
});
test('single-file browser build matches source and CSP script hashes',()=>{
 const r=spawnSync('python3',[path.join(__dirname,'build.py'),'--check'],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);
 const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
 const {createHash}=require('node:crypto');for(const id of ['audit-engine','audit-app']){const script=html.split('<script id="'+id+'">')[1].split('</script>')[0];const hash=createHash('sha256').update(script).digest('base64');assert.ok(html.includes("'sha256-"+hash+"'"));}
 assert.ok(html.includes("connect-src 'none'"));assert.ok(!html.includes('localStorage'));assert.ok(!html.includes('innerHTML'));
});
test('CLI returns data, behavior-failure and input-error separately',()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'approval-trace-test-'));
 try {for(const [name,value,code] of [['good',JSON.stringify(examples.valid),0],['bad',JSON.stringify(examples.stale),1],['syntax','{',2]]){
  const input=path.join(tmp,name+'.json');fs.writeFileSync(input,value);const r=spawnSync(process.execPath,[path.join(__dirname,'cli.cjs'),input],{encoding:'utf8'});assert.equal(r.status,code);if(code!==2)assert.ok(JSON.parse(r.stdout).status);else assert.equal(r.stdout,'');assert.equal(fs.readFileSync(input,'utf8'),value);
 }
 const p=path.join(tmp,'utf8.json');fs.writeFileSync(p,Buffer.from([0xff]));assert.equal(spawnSync(process.execPath,[path.join(__dirname,'cli.cjs'),p]).status,2);
 } finally {fs.rmSync(tmp,{recursive:true,force:true});}
});
