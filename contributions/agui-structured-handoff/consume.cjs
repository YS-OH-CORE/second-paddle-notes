'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');
function version(name) {
  let dir = path.dirname(require.resolve(name));
  while (true) {
    const file = path.join(dir, 'package.json');
    if (fs.existsSync(file)) { const meta=JSON.parse(fs.readFileSync(file,'utf8')); if(meta.name===name)return meta.version; }
    const parent=path.dirname(dir); if(parent===dir)throw new Error('Package metadata not found'); dir=parent;
  }
}
const { HttpAgent } = require('@ag-ui/client');
const KEY = 'example.mcp.result.v1';
const report = {status:'incomplete',versions:{client:version('@ag-ui/client'),core:version('@ag-ui/core'),node:process.version},cases:[],requests:[]};
const [base,out] = process.argv.slice(2);
const fetchOriginal = globalThis.fetch;
globalThis.fetch = async function(input,options) {
  const url=typeof input==='string'?input:input.url;
  assert.equal(new URL(url).origin,base);
  report.requests.push({url,method:options?.method||'GET'});
  return fetchOriginal(input,options);
};
(async()=>{
  try {
    assert.equal(report.versions.client,'0.0.59');assert.equal(report.versions.core,'0.0.59');
    for (const mode of ['top_level','metadata']) {
      for (const name of ['ui','empty_object','error','absent']) {
        const events=[];
        const agent=new HttpAgent({url:`${base}/${mode}/${name}`,threadId:`thread-${mode}-${name}`});
        await agent.runAgent({runId:`run-${mode}-${name}`,tools:[],context:[]},{
          onToolCallResultEvent:({event})=>{events.push(JSON.parse(JSON.stringify(event)));}
        });
        assert.equal(events.length,1);
        const messages=JSON.parse(JSON.stringify(agent.messages));
        const message=messages.find(m=>m.id===`result-${mode}-${name}`);
        assert.ok(message);assert.equal(message.role,'tool');
        assert.equal(message.content,events[0].content);
        assert.equal(message.toolCallId,`call-${mode}-${name}`);
        if (mode==='metadata' && name!=='absent') {
          assert.ok(Object.hasOwn(message.metadata||{},KEY));
          assert.deepEqual(message.metadata[KEY],events[0].metadata[KEY]);
        }
        assert.ok(!JSON.stringify(messages).includes('HOST_ONLY_CANARY_DO_NOT_FORWARD'));
        report.cases.push({mode,case:name,event:events[0],message,
          undeclared_field_at_event:Object.hasOwn(events[0],'structuredContent'),
          undeclared_field_at_message:Object.hasOwn(message,'structuredContent')});
      }
    }
    assert.equal(report.requests.length,8);
    report.status='passed';
  } catch(e) {report.error=e.stack;throw e;}
  finally {fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');}
})().catch(e=>{console.error(e);process.exitCode=1;});
