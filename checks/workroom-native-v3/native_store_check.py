"""Native browser check of the unmodified v3 persistence MODULE, not the whole app.

Real localStorage and navigator.locks; no API mocks or browser-policy changes.
The engine parameter is a deliberately small test fixture: full engine validation,
choice semantics, UI, iOS and file:// behavior are NOT tested here. No private data.
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import zlib
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
STORE_SHA = 'a76ab457f4a83a1109235b8f92afc4458f3f99ec15de3b3350bde3a7dfb518e3'
HTML_SHA = 'd77842b2c229c75d3a47bc6c90a6a23e17b35733c26dc7f9ac4a433b48c2a7bd'
KEY = 'zero.workroom.offline.v3'
FIXTURE = r'''<!doctype html><meta charset="utf-8"><title>Synthetic storage module test</title>
<script src="/store.js"></script><script>
// The real application engine is NOT replaced in a shipped app. This page is an
// isolated contract fixture for the unchanged persistence module only.
const E = {
 parse: JSON.parse,
 clone: x => JSON.parse(JSON.stringify(x)),
 id: () => 'z'+crypto.randomUUID().replaceAll('-',''),
 validate: s => {if(!s || typeof s.id!=='string' || typeof s.note!=='string') throw Error('fixture shape'); return s;}
};
window.store = ZeroStore.create({storage:localStorage,locks:navigator.locks,secure:isSecureContext},E);
window.events=[];
addEventListener('storage',e=>events.push({key:e.key,newValue:e.newValue}));
window.attempt=async(c,expected)=>{try{return {ok:true,raw:await store.save(c,expected)}}catch(e){return {ok:false,code:e.code||e.name}}};
</script>'''


def staging_audit():
    """Do not use an unchecked encoded whole-app fixture as runnable software."""
    row = {'used_for_execution': False, 'full_app_test_executed': False}
    try:
        pieces = [(ROOT / f'neutral.part{i}.b64').read_bytes() for i in range(1,4)]
        row['part_sha256'] = [hashlib.sha256(x).hexdigest() for x in pieces]
        data = zlib.decompress(base64.b64decode(b''.join(pieces),validate=True))
        row['decoded_sha256'] = hashlib.sha256(data).hexdigest()
        row['matches_expected_neutral_html'] = row['decoded_sha256'] == HTML_SHA
    except Exception as e:
        row['matches_expected_neutral_html'] = False
        row['error'] = type(e).__name__ + ': ' + str(e)[:200]
    return row


async def run():
    raw_module = (ROOT/'store.js').read_bytes()
    report = {
        'scope':'unaltered v3 persistence module, native browser APIs, synthetic engine fixture',
        'source_sha256':hashlib.sha256(raw_module).hexdigest(),
        'full_app_staging':staging_audit(),
        'checks':[], 'page_errors':[], 'unexpected_requests':[],
        'full_app_ui_tested':False, 'full_engine_validation_tested':False,
        'ios_tested':False, 'os_reboot_tested':False, 'file_url_tested':False,
    }
    def check(name, ok, detail=None):
        report['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
        if not ok:
            raise AssertionError(name)
    check('unaltered_store_source',report['source_sha256']==STORE_SHA)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/test.html':
                body,typ=FIXTURE.encode(),'text/html; charset=utf-8'
            elif self.path=='/store.js':
                body,typ=raw_module,'text/javascript; charset=utf-8'
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type',typ)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    origin=f'http://127.0.0.1:{server.server_port}'
    url=origin+'/test.html'
    chrome=os.environ.get('CHROME_BIN') or shutil.which('google-chrome') or shutil.which('chromium')
    check('browser_available',bool(chrome))
    def catalog(note):
        return {'schema':'zero.workroom.catalog.v1','currentId':'zsynthetic',
                'spaces':[{'id':'zsynthetic','note':note,'waitingFor':'synthetic user choice'}]}
    literal='\ufeff가상 원문\r\n  빈 줄 보존\r\n\r\n<script>window.BAD=1</script>\r\n'
    original=catalog(literal)
    async def attach(context):
        async def route(r):
            if not r.request.url.startswith(origin+'/'):
                report['unexpected_requests'].append(r.request.url)
                await r.abort()
            else: await r.continue_()
        await context.route('**/*',route)
        context.on('page',lambda pg: pg.on('pageerror',lambda e: report['page_errors'].append(str(e))))
    async def page(context):
        pg=await context.new_page()
        await pg.goto(url,wait_until='load')
        await pg.wait_for_function('typeof window.store !== "undefined"')
        return pg
    try:
        async with async_playwright() as p:
            with tempfile.TemporaryDirectory(prefix='zero-native-store-') as d:
                context=await p.chromium.launch_persistent_context(d,executable_path=chrome,headless=True)
                await attach(context)
                a=await page(context)
                report['browser_version']=context.browser.version if context.browser else await a.evaluate('navigator.userAgent')
                native=await a.evaluate('''()=>({secure:isSecureContext, supported:store.supported(),
                  storageNative:Function.prototype.toString.call(Storage.prototype.setItem).includes('[native code]'),
                  locksNative:Function.prototype.toString.call(navigator.locks.request).includes('[native code]')})''')
                check('native_apis_on_loopback_secure_context',all(native.values()),native)
                first=await a.evaluate('c=>attempt(c,null)',original)
                check('initial_native_write_readback',first.get('ok') and json.loads(first['raw'])['catalog']==original)
                b=await page(context)
                check('second_page_reads_same_origin_value',await b.evaluate('store.raw()')==first['raw'])
                next_catalog=catalog('A updated the question; B still has the older value')
                newer=await a.evaluate('([c,e])=>attempt(c,e)',[next_catalog,first['raw']])
                check('new_revision_written',newer.get('ok'))
                await b.wait_for_function('(v)=>events.some(e=>e.key===store.KEY&&e.newValue===v)',arg=newer['raw'])
                check('native_storage_event_seen',True)
                stale=await b.evaluate('([c,e])=>attempt(c,e)',[catalog('stale B answer'),first['raw']])
                check('stale_writer_rejected',stale=={'ok':False,'code':'STALE'})
                check('stale_writer_did_not_change_latest',await a.evaluate('store.raw()')==newer['raw'])
                await a.evaluate('''()=>{window.lockReady=false; window.held=navigator.locks.request(store.LOCK,async()=>{
                  window.lockReady=true; await new Promise(r=>window.releaseLock=r);
                });}''')
                await a.wait_for_function('window.lockReady===true')
                busy=await b.evaluate('([c,e])=>attempt(c,e)',[catalog('locked write'),newer['raw']])
                check('real_lock_contention_rejected',busy=={'ok':False,'code':'BUSY'})
                await a.evaluate('async()=>{releaseLock();await held}')
                retry=await b.evaluate('([c,e])=>attempt(c,e)',[original,newer['raw']])
                check('retry_after_native_lock_release',retry.get('ok'))
                left,right=await asyncio.gather(
                    a.evaluate('([c,e])=>attempt(c,e)',[catalog('parallel A'),retry['raw']]),
                    b.evaluate('([c,e])=>attempt(c,e)',[catalog('parallel B'),retry['raw']]))
                check('parallel_writers_one_commit',sum(bool(x.get('ok')) for x in [left,right])==1,[left.get('code'),right.get('code')])
                loser=left if not left.get('ok') else right
                check('parallel_loser_reports_busy_or_stale',loser.get('code') in ['BUSY','STALE'])
                saved_raw=await a.evaluate('store.raw()')
                literal_saved=await a.evaluate('([c,e])=>attempt(c,e)',[original,saved_raw])
                check('literal_source_preserved',literal_saved.get('ok') and json.loads(literal_saved['raw'])['catalog']==original)
                before_restart=literal_saved['raw']
                await context.close()
                context=await p.chromium.launch_persistent_context(d,executable_path=chrome,headless=True)
                await attach(context)
                a=await page(context)
                after_restart=await a.evaluate('store.raw()')
                check('browser_process_restart_same_profile',after_restart==before_restart)
                check('restart_literal_text_exact',await a.evaluate('store.read().catalog.spaces[0].note')==literal)
                isolated=await p.chromium.launch(executable_path=chrome,headless=True)
                fresh=await isolated.new_context(); await attach(fresh)
                f=await page(fresh)
                check('different_profile_has_no_saved_value',await f.evaluate('store.raw()') is None)
                await isolated.close()
                deleted=await a.evaluate('e=>attempt(null,e)',after_restart)
                check('tombstone_saved',deleted.get('ok') and json.loads(deleted['raw'])['catalog'] is None)
                blocked=await a.evaluate('([c,e])=>attempt(c,e)',[original,after_restart])
                check('old_writer_cannot_resurrect_after_delete',blocked=={'ok':False,'code':'STALE'})
                await a.evaluate('([key,value])=>localStorage.setItem(key,value)',['zero.workroom.offline.v1',json.dumps(original,ensure_ascii=False)])
                v1=await a.evaluate('localStorage.getItem("zero.workroom.offline.v1")')
                legacy=await a.evaluate('store.legacy()')
                check('legacy_v1_read_only',legacy['catalog']==original and await a.evaluate('localStorage.getItem("zero.workroom.offline.v1")')==v1)
                v2=json.dumps({'schema':'zero.workroom.storage.v2','generation':'zold','catalog':None})
                await a.evaluate('v=>localStorage.setItem("zero.workroom.offline.v2",v)',v2)
                migration=await a.evaluate('store.legacy()')
                check('legacy_v2_tombstone_precedes_v1',migration=={'catalog':None,'from':'v2','tombstone':True})
                await a.evaluate('localStorage.setItem(store.KEY,"not JSON")')
                invalid=await a.evaluate('c=>attempt(c,"not JSON")',original)
                check('corrupt_existing_value_not_overwritten',not invalid['ok'] and await a.evaluate('store.raw()')=='not JSON')
                check('no_page_errors',not report['page_errors'])
                check('no_unexpected_page_requests',not report['unexpected_requests'])
                await context.close()
        report['success']=True
    except Exception as e:
        report['success']=False
        report['failure']=type(e).__name__+': '+str(e)[:1000]
        raise
    finally:
        server.shutdown();server.server_close()
        print('ZERO_NATIVE_STORE_RESULT '+json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    asyncio.run(run())
