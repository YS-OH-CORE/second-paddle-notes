'use strict';
// Read-only, five synthetic raw-text comparisons. No agent, account or task execution.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
if(process.argv.length!==3)throw new Error('Usage: node compare-unique-json.cjs /path/to/previous/audit.js');
const baseFile=path.resolve(process.argv[2]);
const oldBytes=fs.readFileSync(baseFile);
const blob=bytes=>createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
assert.equal(blob(oldBytes),'6a34a92f10a5bdfe022740838e93076e5149367c','Wrong baseline source');
const base=require(baseFile), candidate=require('./audit.js');
const p='{"type":"propose","request_id":"A","scope":"s","payload":"draft only"}';
const x='{"type":"execute","request_id":"A","scope":"s","payload":"draft only"}';
const a='{"type":"approve","request_id":"A","scope":"s"}';
const doc=e=>' {"schema":"approval-trace-v1","events":['+e.join(',')+']}';
const cases=[
 ['cancel_then_approve_same_field',doc([p,'{"type":"cancel","type":"approve","request_id":"A","scope":"s"}',x])],
 ['execution_text_overwritten',doc([p,a,x.replace('"payload":"draft only"','"payload":"send now","payload":"draft only"')])],
 ['events_array_overwritten','{"schema":"approval-trace-v1","events":['+x+'],"events":['+[p,a,x].join(',')+']}'],
 ['escaped_field_name_collision',doc([p,'{"type":"cancel","t\\u0079pe":"approve","request_id":"A","scope":"s"}',x])],
 ['identical_duplicate_still_ambiguous',doc([p,a.replace('"type":"approve"','"type":"approve","type":"approve"'),x])]
];
const rows=cases.map(([name,text])=>{
 const before=base.parseAndAudit(text);assert.equal(before.status,'no_violation_observed');
 let error;
 assert.throws(()=>candidate.parseAndAudit(text),e=>{error=e;return e.code==='DUPLICATE_JSON_MEMBER';});
 return {case:name,synthetic_source:text,before:{status:before.status,valid_execution_attempts:before.valid_execution_attempts},
   after:{status:'input_not_assessed',code:error.code,line:error.line,column:error.column,offset:error.offset}};
});
console.log(JSON.stringify({baseline_git_blob:blob(oldBytes),candidate_git_blob:blob(fs.readFileSync(path.join(__dirname,'audit.js'))),
 scope:'Five synthetic duplicate-member examples, not production incidents. Existing valid-input behavior is checked separately.',rows},null,2));
