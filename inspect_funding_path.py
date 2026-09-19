"""Bounded read of public blank form's funding-only UI branch.

No personal inputs, consent answers, login, uploads or submission. Non-read
network requests are blocked. Only already observed option labels are selected.
These local UI probes do not establish submission validity or an award.
"""
import json
import shutil
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = 'https://airtable.com/appyVXc5SMPAvIKpP/pagp7takV26cG6JY1/form'
LABEL = """e => ({label:(e.getAttribute('aria-labelledby')||'').split(/\\s+/).map(id=>document.getElementById(id)?.innerText||'').join(' ').trim() || e.getAttribute('aria-label') || (e.labels?Array.from(e.labels).map(x=>x.innerText).join(' | '):''),role:e.getAttribute('role'),required:e.getAttribute('aria-required'),nativeRequired:e.required===true,maxLength:e.getAttribute('maxlength'),tag:e.tagName})"""


def emit(data):
    print('PUBLIC_FUNDING_PATH '+json.dumps(data,ensure_ascii=True),flush=True)


def snapshot(page, stage):
    controls=[]
    for el in page.locator('textarea,input,[role=combobox],[role=textbox],[role=checkbox]').all():
        if el.is_visible():
            controls.append(el.evaluate(LABEL))
    text=page.locator('body').inner_text(timeout=10000)
    emit({'stage':stage,'url':page.url,'text':text[:30000],
          'text_truncated':len(text)>30000,'controls':controls})


def select_observed_option(page, label_contains, desired):
    matches=[]
    for el in page.get_by_role('combobox').all():
        if el.is_visible() and label_contains.casefold() in el.evaluate(LABEL)['label'].casefold():
            matches.append(el)
    if len(matches)!=1:
        raise RuntimeError('Field was not unique: '+label_contains)
    field=matches[0]
    field.click(timeout=8000)
    page.wait_for_timeout(250)
    options=page.get_by_role('option').all()
    texts=[option.inner_text() for option in options]
    emit({'field':label_contains,'observed_options':texts})
    exact=[option for option in options if option.inner_text().strip()==desired]
    if len(exact)!=1 or not exact[0].is_visible():
        page.keyboard.press('Escape')
        raise RuntimeError('Expected visible option absent or ambiguous: '+desired)
    # The previous run's physical click stalled while scrolling. Dispatch the
    # normal DOM click to this verified visible option, not to any submit button.
    exact[0].evaluate('(element)=>element.click()')
    page.wait_for_timeout(700)
    page.keyboard.press('Escape')
    current=[]
    for el in page.get_by_role('combobox').all():
        if el.is_visible() and label_contains.casefold() in el.evaluate(LABEL)['label'].casefold():
            current.append(el.inner_text())
    matched=any(desired in value for value in current)
    emit({'field':label_contains,'requested_local_choice':desired,
          'observed_field_text':current,'display_confirmed':matched})
    if not matched:
        raise RuntimeError('Selection did not appear in field: '+label_contains)


def main():
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise RuntimeError('No preinstalled browser')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=chrome,headless=True)
        context=browser.new_context(accept_downloads=False,viewport={'width':1440,'height':1200})
        blocked=[]
        def guard(route):
            if route.request.method not in ('GET','HEAD','OPTIONS'):
                blocked.append(route.request.method)
                route.abort()
            else:
                route.continue_()
        context.route('**/*',guard)
        page=context.new_page()
        response=page.goto(URL,wait_until='domcontentloaded',timeout=45000)
        page.wait_for_timeout(7000)
        emit({'status':'opened','http_status':response.status,'title':page.title(),
              'observed_at_utc':datetime.now(timezone.utc).isoformat()})
        completed=[]
        for label,desired in [
            ('Applying as an','Individual'),
            ('What are you applying for','Funding (Grant)'),
            ('Are you requesting funding','Yes'),
            ('Are you requesting compute','No')
        ]:
            try:
                select_observed_option(page,label,desired)
                completed.append({'field':label,'choice':desired})
            except Exception as exc:
                emit({'field':label,'status':'probe_incomplete',
                      'error':type(exc).__name__+': '+str(exc)[:600]})
                page.keyboard.press('Escape')
                break
        snapshot(page,'after_verified_local_probes')
        emit({'status':'finished','verified_probes':completed,
              'blocked_nonread_requests':len(blocked),'personal_values_entered':0,
              'consent_answers_selected':0,'submission_actions':0,
              'limitation':'Anonymous local UI selections only; conditional fields and server-side validation are not inferred beyond what is visible.'})
        context.close()
        browser.close()


if __name__=='__main__':
    main()
