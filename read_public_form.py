"""One-shot public-page inspection. No login, input, clicks, or form submission.

Prepared by Zero for Youngseok Oh. It captures observable content, not proof
that a form is the current application route. Fresh browser context; no secrets.
"""
import json
import shutil
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

RFP = "https://foresight.org/grants/ai-science-safety-nodes-rfp/"
OLD_CANDIDATE = "https://airtable.com/appyVXc5SMPAvIKpP/pagzBRWeiG3HjH6Qn/form"
BLOCKED = {"POST", "PUT", "PATCH", "DELETE"}

def emit(data):
    # Prefix + JSON escapes prevent website strings from becoming log commands.
    print("PUBLIC_OBSERVATION " + json.dumps(data, ensure_ascii=True), flush=True)


def inspect(page, url, provenance):
    result = {"requested_url": url, "provenance": provenance,
              "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "input_actions": 0, "submission_actions": 0}
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(7000)
        result.update({"final_url": page.url, "http_status": response.status if response else None,
                       "title": page.title()})
        result["frames"] = []
        for frame in page.frames[:6]:
            try:
                text = frame.locator("body").inner_text(timeout=8000)
                fields = frame.locator("input,textarea,select,[role=combobox],[role=checkbox],[role=radio]").evaluate_all('''els => els.map(e => ({tag:e.tagName, type:e.getAttribute('type'),role:e.getAttribute('role'),id:e.id,name:e.getAttribute('name'),label:(e.labels?Array.from(e.labels).map(x=>x.innerText).join(' | '):''),ariaLabel:e.getAttribute('aria-label'),ariaLabelledBy:e.getAttribute('aria-labelledby'),required:e.required===true,ariaRequired:e.getAttribute('aria-required'),maxLength:e.getAttribute('maxlength'),minLength:e.getAttribute('minlength'),placeholder:e.getAttribute('placeholder'),options:e.tagName==='SELECT'?Array.from(e.options).map(o=>({text:o.text,value:o.value})):null,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)})).slice(0,100)''')
                result["frames"].append({"url": frame.url, "text": text[:24000],
                                         "text_truncated": len(text)>24000, "fields":fields})
            except Exception as exc:
                result["frames"].append({"url":frame.url,"error":type(exc).__name__+": "+str(exc)[:600]})
        links = page.locator("a[href]").evaluate_all("els=>els.map(e=>({text:e.innerText,href:e.href}))")
        result["application_links"] = [x for x in links if urlparse(x['href']).hostname in {'airtable.com','www.airtable.com','forms.gle','docs.google.com'}][:20]
        result["status"] = "observed"
    except Exception as exc:
        result.update({"status":"read_failed", "error":type(exc).__name__+": "+str(exc)[:800]})
    emit(result)
    return result


def main():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        raise RuntimeError("No preinstalled browser found; not downloading an unplanned browser")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True)
        context = browser.new_context(viewport={"width":1280,"height":960}, accept_downloads=False)
        blocked = []
        def guard(route):
            req = route.request
            if req.method.upper() in BLOCKED:
                blocked.append({"method":req.method,"host":urlparse(req.url).hostname})
                route.abort()
            else:
                route.continue_()
        context.route("**/*", guard)
        page = context.new_page()
        first = inspect(page, RFP, "current_official_call_requested")
        forms = [x['href'] for x in first.get('application_links',[]) if urlparse(x['href']).hostname in {'airtable.com','www.airtable.com'}]
        urls = list(dict.fromkeys(forms))[:2]
        if not urls:
            urls = [OLD_CANDIDATE]
        for url in urls:
            inspect(page, url, "linked_from_current_observed_call" if url in forms else "historical_candidate_currentness_unverified")
        emit({"status":"finished", "browser_version":browser.version,
              "blocked_nonread_request_count":len(blocked),"blocked_hosts":sorted({x['host'] for x in blocked if x['host']}),
              "policy":"No input, click, login, submission, credentials, uploads or downloads. Non-GET/HEAD/OPTIONS requests blocked.",
              "limitation":"Blocking non-read requests may prevent dynamic read APIs. Hidden conditional fields are not established."})
        context.close()
        browser.close()

if __name__ == '__main__':
    main()
