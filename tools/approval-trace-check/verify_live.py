"""Read-only public-entry check. Uses live navigation, never supplied HTML.

All input data is synthetic. A third-party hosting notice is followed through
its ordinary visible button, not cookie/header injection. This exercises hosted
Chromium and mobile-size WebKit, not a physical phone or native Safari.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = 'https://rawcdn.githack.com/YS-OH-CORE/second-paddle-notes/b0fc912f4e8d957623c3df087cdadcaacba95c53/tools/approval-trace-check/index.html'
EXPECTED = 'd27f2b213ff2e4b32ceb930bf361b6adef8d28c3d3ed61a10c346bdfca6877ae'
PAYLOAD = 'SYNTHETIC_ONLY_CANARY_60912  한글\n    keep indentation\n'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)
    summary = {'status':'incomplete', 'url':URL, 'expected_sha256':EXPECTED, 'browsers':[],
               'scope':'Live public URL, synthetic input, Linux browsers; not native iPhone Safari.',
               'hosting':'Third-party rawgit.hack; host sees ordinary page requests. No GitHub Pages configuration or uptime guarantee.'}
    try:
        # The first machine GET returned 403 before any browser was launched.
        # Test the intended, normal browser route once; keep that failure recorded.
        # The independently pinned repository bytes remain the acceptance target.
        data = Path(__file__).with_name('index.html').read_bytes()
        assert len(data) == 26813 and digest(data) == EXPECTED
        summary['prior_attempt'] = {
            'run_id':34698109087, 'method':'urllib GET', 'status':403,
            'browser_started':False, 'reason_beyond_http_status':'unconfirmed'}
        with sync_playwright() as p:
            for name, mobile in [('chromium',False), ('webkit',True)]:
                result = {'engine':name, 'mobile_size':mobile, 'checks':[], 'requests':[], 'page_errors':[]}
                summary['browsers'].append(result)
                browser = getattr(p,name).launch(headless=True)
                context = browser.new_context(locale='en-US', accept_downloads=True,
                    viewport={'width':390 if mobile else 1280,'height':844 if mobile else 960},
                    is_mobile=mobile, has_touch=mobile)
                page = context.new_page()
                page.set_default_timeout(12000)
                phase = ['entry']
                page.on('request',lambda req:result['requests'].append({
                    'phase':phase[0], 'method':req.method, 'url':req.url,
                    'resource_type':req.resource_type, 'synthetic_payload_in_request':PAYLOAD in (req.post_data or '') or 'SYNTHETIC_ONLY_CANARY' in req.url}))
                page.on('pageerror',lambda error:result['page_errors'].append(str(error)))
                try:
                    doc = page.goto(URL, wait_until='domcontentloaded', timeout=45000)
                    result['entry_http_status'] = doc.status if doc else None
                    result['entry_title'] = page.title()
                    if doc:
                        result['entry_response_headers'] = {k:v for k,v in doc.headers.items() if k in ('content-type','server','x-githack-cache-status')}
                    assert doc and doc.ok, 'Public browser entry denied; no bypass or retry'
                    button = page.get_by_role('button', name='Open the page', exact=True)
                    result['host_notice_shown'] = button.count() > 0
                    if result['host_notice_shown']:
                        assert page.locator('#phish-dest').input_value() == URL
                        with page.expect_navigation(wait_until='domcontentloaded', timeout=45000) as nav:
                            button.click()
                        doc = nav.value
                    assert doc and doc.ok and page.url == URL
                    actual = doc.body()
                    result['document_sha256'] = digest(actual)
                    assert actual == data, 'Served document differs from the exact published source'
                    (out/(name+'-served.html')).write_bytes(actual)
                    page.wait_for_selector('#trace')
                    assert page.title() == 'Approval Trace Check'
                    page.wait_for_load_state('networkidle')
                    assert page.locator('#status').inner_text() == 'Mismatch found'
                    assert 'PAYLOAD_CHANGED' in page.locator('#timeline').inner_text()
                    result['checks'].append('actual served bytes match the fixed public source and initial result runs')
                    phase[0] = 'interaction'
                    page.select_option('#sample','valid'); page.click('#load')
                    assert page.locator('#status').inner_text() == 'No violation observed'
                    result['checks'].append('live controls change the example result')
                    trace = {'schema':'approval-trace-v1','events':[
                        {'type':'propose','request_id':'synthetic-live','scope':'demo','payload':PAYLOAD},
                        {'type':'approve','request_id':'synthetic-live','scope':'demo'},
                        {'type':'execute','request_id':'synthetic-live','scope':'demo','payload':PAYLOAD}]}
                    encoded = json.dumps(trace,ensure_ascii=False).encode('utf-8')
                    page.set_input_files('#file',{'name':'synthetic.json','mimeType':'application/json','buffer':encoded})
                    page.wait_for_function("document.getElementById('trace').value.includes('SYNTHETIC_ONLY_CANARY')")
                    page.wait_for_function("document.getElementById('status').textContent === 'No violation observed'")
                    assert json.loads(page.locator('#trace').input_value()) == trace
                    result['checks'].append('real file import preserves exact synthetic Korean payload')
                    with page.expect_download() as pending:
                        page.click('#export')
                    pending.value.save_as(out/(name+'-report.json'))
                    report = json.loads((out/(name+'-report.json')).read_text())
                    assert report['valid_execution_attempts'] == report['execution_attempts'] == 1
                    assert report['issues'] == [] and PAYLOAD not in json.dumps(report,ensure_ascii=False)
                    result['checks'].append('browser-generated download is valid and omits payload text')
                    trace['events'][2]['payload'] = 'Different synthetic task'
                    page.fill('#trace',json.dumps(trace,ensure_ascii=False))
                    assert page.locator('#export').is_disabled()
                    page.click('#check')
                    assert 'PAYLOAD_CHANGED' in page.locator('#timeline').inner_text()
                    result['checks'].append('editing disables old export and a changed execution is detected')
                    page.click('#lang')
                    assert page.locator('html').get_attribute('lang') == 'ko'
                    assert page.locator('#status').inner_text() == '어긋남을 찾았어'
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    page.screenshot(path=str(out/(name+'.png')),full_page=True)
                    result['checks'].append('Korean rendering fits the tested viewport')
                    context.set_offline(True)
                    page.select_option('#sample','valid');page.click('#load')
                    assert page.locator('#status').inner_text() == '위반 관측 없음'
                    result['checks'].append('already-loaded checker still operates with network disconnected')
                    context.set_offline(False)
                    page.wait_for_timeout(300)
                    interaction_http = [r for r in result['requests'] if r['phase']=='interaction' and r['url'].startswith(('https:','http:'))]
                    result['interaction_http_count'] = len(interaction_http)
                    assert not interaction_http and not result['page_errors']
                    assert not any(r['synthetic_payload_in_request'] for r in result['requests'])
                    storage = page.evaluate('JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])')
                    assert 'SYNTHETIC_ONLY_CANARY' not in storage
                    result['checks'].append('no HTTP requests during data interactions and no canary in browser storage')
                    phase[0] = 'reload'
                    page.reload(wait_until='domcontentloaded')
                    page.wait_for_selector('#trace')
                    assert 'SYNTHETIC_ONLY_CANARY' not in page.locator('#trace').input_value()
                    result['checks'].append('reloading does not restore the supplied trace')
                    result.update(status='passed', version=browser.version)
                except Exception as exc:
                    result.update(status='failed', error=type(exc).__name__+': '+str(exc))
                    page.screenshot(path=str(out/(name+'-failure.png')),full_page=True)
                    raise
                finally:
                    context.close();browser.close()
        summary['status'] = 'verified'
    except Exception as exc:
        summary['error'] = type(exc).__name__+': '+str(exc)
        raise
    finally:
        (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    verify(parser.parse_args().out)
