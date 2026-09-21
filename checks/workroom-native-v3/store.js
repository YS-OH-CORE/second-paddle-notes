/* Cooperative multi-tab persistence. Native Web Locks are required for writes.
   Never writes or deletes the legacy v1 key. Not a hostile-origin sandbox. */
(function(root){
'use strict';
const KEY='zero.workroom.offline.v3', LEGACY_KEY='zero.workroom.offline.v1';
const FORMAT='zero.workroom.storage.v3', LOCK='zero.workroom.storage.v3.exclusive';
function fail(code,message){const e=new Error(message);e.code=code;throw e;}
function client(env,E){
 const supported=()=>!!env.secure&&typeof env.locks?.request==='function';
 function validateCatalog(c){
  if(!c||typeof c!=='object'||Object.keys(c).sort().join('|')!=='currentId|schema|spaces'||c.schema!=='zero.workroom.catalog.v1'||!Array.isArray(c.spaces)||!c.spaces.length||c.spaces.length>30)fail('FORMAT','작업실 목록 형식이 맞지 않습니다.');
  c.spaces.forEach(E.validate);
  if(new Set(c.spaces.map(x=>x.id)).size!==c.spaces.length||!c.spaces.some(x=>x.id===c.currentId))fail('FORMAT','작업실 식별자가 중복되거나 없습니다.');
  return c;
 }
 function raw(){try{return env.storage.getItem(KEY);}catch(e){fail('READ','브라우저 보관값을 읽지 못했습니다. 이 창의 입력과 파일 백업을 사용하세요.');}}
 function decode(value){
  if(value===null)return {catalog:null,generation:null};
  const x=E.parse(value);
  if(!x||Object.keys(x).sort().join('|')!=='catalog|generation|schema'||x.schema!==FORMAT||typeof x.generation!=='string'||!/^z[A-Za-z0-9_-]{1,99}$/.test(x.generation))fail('FORMAT','v3 브라우저 보관 형식이 맞지 않습니다. 기존 값은 변경하지 않았습니다.');
  if(x.catalog!==null)validateCatalog(x.catalog);
  return x;
 }
 function read(){const value=raw();return {raw:value,...decode(value)};}
 async function save(c,expected){
  if(!supported())fail('NO_LOCK','이 환경은 안전한 여러 창 저장을 지원하지 않습니다. 현재 탭과 파일 백업을 사용하세요.');
  if(c!==null)validateCatalog(c);
  // Freeze the outgoing value before waiting for a lock. The compare and write
  // below contain no asynchronous gap while the cooperative lock is held.
  const frozen=c===null?null:E.clone(c);
  return env.locks.request(LOCK,{mode:'exclusive',ifAvailable:true},lock=>{
   if(!lock)fail('BUSY','다른 창이 저장 중입니다. 이 창의 입력은 그대로입니다. 잠시 후 다시 저장하세요.');
   const before=raw();
   if(before!==expected)fail('STALE','다른 창이 보관 기록을 바꿨습니다. 덮어쓰지 않았습니다. 이 창의 입력을 보존한 뒤 최신 기록을 확인하세요.');
   decode(before); // A corrupt existing value must never be silently replaced.
   const after=JSON.stringify({schema:FORMAT,generation:E.id(),catalog:frozen});
   try{env.storage.setItem(KEY,after);}catch(e){fail('WRITE','브라우저 저장에 실패했습니다. 이 창의 입력과 기존 보관본은 그대로입니다. 파일 백업을 저장하세요.');}
   if(raw()!==after)fail('READBACK','저장 뒤 값이 다시 바뀌었습니다. 완료로 표시하지 않았습니다. 이 창과 브라우저 보관본을 각각 확인하세요.');
   return after;
  });
 }
 // Read old storage only on initial migration; never edit either old key.
 function legacy(){
  const old=env.storage.getItem('zero.workroom.offline.v2');
  if(old!==null){
   const x=E.parse(old);
   if(!x||Object.keys(x).sort().join('|')!=='catalog|generation|schema'||x.schema!=='zero.workroom.storage.v2'||typeof x.generation!=='string'||!/^z[A-Za-z0-9_-]{1,99}$/.test(x.generation))fail('FORMAT','기존 v2 보관본 형식이 맞지 않습니다. 변경하지 않았습니다.');
   if(x.catalog!==null)validateCatalog(x.catalog);
   return {catalog:x.catalog,from:'v2',tombstone:x.catalog===null};
  }
  const first=env.storage.getItem(LEGACY_KEY);
  return {catalog:first===null?null:validateCatalog(E.parse(first)),from:first===null?null:'v1',tombstone:false};
 }
 return {KEY,LEGACY_KEY,LOCK,supported,raw,read,decode,validateCatalog,save,legacy};
}
root.ZeroStore={create:client,KEY,LEGACY_KEY,LOCK};
if(typeof module!=='undefined'&&module.exports)module.exports=root.ZeroStore;
})(typeof globalThis!=='undefined'?globalThis:this);
