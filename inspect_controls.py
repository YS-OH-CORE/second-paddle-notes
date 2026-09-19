"""Inspect public blank-form choices and funding-only conditional questions.
No applicant details, consent selections, upload, login or submission. All
non-GET/HEAD/OPTIONS requests are blocked. Selections are local UI probes.
"""
import json
import re
import shutil
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = 'https://airtable.com/appyVXc5SMPAvIKpP/pagp7takV26cG6JY1/form'

def emit(data):
    print('PUBLIC_CONTROLS '+json.dumps(data,ensure_ascii=True),flush=True)

LABEL = """e => ({label:(e.getAttribute('aria-labelledby')||'').split(/\\s+/).map(id=>document.getElementById(id)?.innerText||'').join(' ').trim() || e.getAttribute('aria-label') || (e.labels?Array.from(e.labels).map(x=>x.innerText).join(' | '):''),role:e.getAttribute('role'),required:e.getAttribute('aria-required'),maxLength:e.getAttribute('maxlength'),tag:e.tagName})"""

def snapshot(page, stage):
    controls=[]
    for el in page.locator('textarea,input,[role=combobox],[role=textbox],[role=checkbox]').all():
        if el.is_visible(): controls.append(el.evaluate(LABEL))
    text=page.locator('body').inner_text()
    emit({'stage':stage,'url':page.url,'text':text[:26000], 'text_truncated':len(text)>26000,'controls':controls})

def choose_or_inspect(page, label_contains, desired=None):
    matches=[]
    for el in page.get_by_role('combobox').all():
        if label_contains.casefold() in el.evaluate(LABEL)['label'].casefold(): matches.append(el)
    if len(matches)!=1:
        emit({'field':label_contains,'status':'not_unique','count':len(matches)})
        return
    el=matches[0]
    el.click(timeout=5000)
    page.wait_for_timeout(300)
    options=page.get_by_role('option').all_text_contents()
    emit({'field':label_contains,'options':options,'expanded_text':page.locator('body').inner_text()[-4500:] if not options else None})
    if desired:
        exact=[text.strip() for text in options if text.strip().casefold()==desired.casefold()]
        if len(exact)==1:
            page.get_by_role('option',name=exact[0],exact=True).click(timeout=5000)
            page.wait_for_timeout(600)
            emit({'field':label_contains,'selected_local_probe':exact[0]})
        else:
            emit({'field':label_contains,'selection_not_performed':desired})
    page.keyboard.press('Escape')


def main():
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome: raise RuntimeError('No preinstalled browser')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=chrome,headless=True)
        context=browser.new_context(accept_downloads=False)
        blocked=[]
        def guard(route):
            if route.request.method not in ('GET','HEAD','OPTIONS'):
                blocked.append(route.request.method)
                route.abort()
            else: route.continue_()
        context.route('**/*',guard)
        page=context.new_page()
        r=page.goto(URL,wait_until='domcontentloaded',timeout=45000)
        page.wait_for_timeout(7000)
        emit({'status':'opened','http_status':r.status,'title':page.title(),'observed_at_utc':datetime.now(timezone.utc).isoformat()})
        snapshot(page,'blank_form')
        for label,desired in [
            ('Applying as an',None),
            ('Primary region',None),
            ('What are you applying for','Funding'),
            ('Which node are you interested in',None),
            ('Are you requesting funding','Yes'),
            ('Are you requesting compute',None),
            ('Do you consent to us sharing your application with our grant advisors',None)
        ]:
            try: choose_or_inspect(page,label,desired)
            except Exception as exc:
                emit({'field':label,'status':'interaction_failed','error':type(exc).__name__+': '+str(exc)[:500]})
                page.keyboard.press('Escape')
        snapshot(page,'after_nonpersonal_funding_probes')
        emit({'status':'finished','blocked_nonread_requests':len(blocked),'consents_selected':0,'personal_values_entered':0,'submit_actions':0,'limitation':'Only currently exposed fields/options; no validation by submitting.'})
        context.close()
        browser.close()

if __name__=='__main__': main()
