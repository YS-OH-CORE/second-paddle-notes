"""Inspect one anonymous public-form Yes choice; no applicant or consent input."""
import json
import shutil
from playwright.sync_api import sync_playwright

URL='https://airtable.com/appyVXc5SMPAvIKpP/pagp7takV26cG6JY1/form'
LABEL="""e => ({label:(e.getAttribute('aria-labelledby')||'').split(/\\s+/).map(id=>document.getElementById(id)?.innerText||'').join(' ').trim() || e.getAttribute('aria-label') || (e.labels?Array.from(e.labels).map(x=>x.innerText).join(' | '):''),role:e.getAttribute('role'),required:e.getAttribute('aria-required'),maxLength:e.getAttribute('maxlength'),tag:e.tagName})"""

def emit(data):
    print('PUBLIC_FUNDING_DETAIL '+json.dumps(data,ensure_ascii=True),flush=True)

with sync_playwright() as p:
    exe=shutil.which('google-chrome') or shutil.which('chromium')
    if not exe: raise RuntimeError('Preinstalled browser missing')
    browser=p.chromium.launch(executable_path=exe,headless=True)
    context=browser.new_context(accept_downloads=False)
    blocked=[]
    def guard(route):
        if route.request.method not in ('GET','HEAD','OPTIONS'):
            blocked.append(route.request.method)
            route.abort()
        else: route.continue_()
    context.route('**/*',guard)
    page=context.new_page()
    page.goto(URL,wait_until='domcontentloaded',timeout=45000)
    page.wait_for_timeout(7000)
    boxes=[x for x in page.get_by_role('combobox').all() if x.is_visible() and x.evaluate(LABEL)['label']=='Are you requesting funding?']
    if len(boxes)!=1: raise RuntimeError('Funding choice not unique')
    boxes[0].click(timeout=8000)
    page.wait_for_timeout(250)
    opts=[x for x in page.get_by_role('option').all() if x.is_visible() and x.inner_text().strip()=='Yes']
    if len(opts)!=1: raise RuntimeError('Yes option not unique')
    opts[0].evaluate('(element)=>element.click()')
    page.wait_for_timeout(1000)
    page.keyboard.press('Escape')
    observed=[]
    for x in page.get_by_role('combobox').all():
        if 'Are you requesting funding?' in x.evaluate(LABEL)['label']:
            observed.append(x.inner_text())
    emit({'local_funding_choice_text':observed,'selection_confirmed':any('Yes' in v for v in observed)})
    controls=[]
    for el in page.locator('textarea,input,[role=combobox],[role=textbox],[role=checkbox]').all():
        if el.is_visible(): controls.append(el.evaluate(LABEL))
    text=page.locator('body').inner_text()
    emit({'url':page.url,'title':page.title(),'text':text[:30000],'text_truncated':len(text)>30000,'controls':controls})
    emit({'blocked_nonread_requests':len(blocked),'personal_inputs':0,'consent_choices':0,'submissions':0,'note':'Single local Yes choice on a fresh blank form. No other application answers, no validation or submission.'})
    context.close()
    browser.close()
