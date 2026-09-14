"""Publish one exact preview and read every asset back without authentication.

Creates/reconciles only the named release. Never replaces/deletes an existing asset.
"""
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import build as b

REPO = 'YS-OH-CORE/second-paddle-notes'
BRANCH = 'zero/reconcile-skill-release-20260914'
TAG = 'github-reconcile-v0.1.0a1'
TITLE = 'GitHub Write Reconcile 0.1.0a1: standalone skill and original evidence'
API = 'https://api.github.com/repos/' + REPO
EXPECTED = json.loads((b.HERE / 'expected-assets.json').read_text())
BODY = '''Read-only GitHub file reconciliation, packaged for opt-in use.

This preview packages the unchanged 12-file github-write-reconcile skill from
source commit 24408637d33ef999ba1c03fd34096af7da258913. It is NOT the separately
released second-paddle-evidence MCP wheel and does not update that package.

Download github-write-reconcile-0.1.0a1.zip, compare SHA256SUMS, extract to a new
folder and run `python -B -S VERIFY.py`. START_HERE.ko.md gives the Korean guide.
The reader needs Python 3.10+; public reads need network access, not a provider key.
No installer runs, no Hermes configuration is changed, and no existing file is
silently replaced. Copy the whole skill folder only after choosing to install it.

Match, conflict, absence at a snapshot and unknown remain distinct. Every reader
outcome has retry_authorized=false. This is not general exactly-once, recovery of
the original HTTP response, or permission to repeat a write.

The evidence ZIP preserves five original success/failure archives and matching
source from PR45 (standalone command), PR46 (real skill loading), and PR47
(real Hermes terminal to GitHub). Those were harness-selected tasks, not LLM
choices or a live user installation. Failed attempts remain failed.

This publication adds packaging and acquisition checks, not new fault experiments.
PROVENANCE.json pins source, artifact IDs, hashes and scope. No private profile or
checkpoint is included. Source and artifacts remain subject to owner control and
repository availability; checksums are correspondence checks, not a signature.

Prepared by Youngseok Oh with Zero (ChatGPT). MIT terms in the skill's LICENSE.
Release intent: second-paddle/github-reconcile-preview/0.1.0a1
'''


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def bounded(response):
    raw = response.read(3_000_001)
    b.need(len(raw) <= 3_000_000, 'HTTP_SIZE_LIMIT')
    return raw


def public_download(url):
    # This opener has no cookies, authorization header or inherited request.
    b.need(urllib.parse.urlsplit(url).scheme == 'https', 'NON_HTTPS_DOWNLOAD')
    with urllib.request.build_opener().open(url, timeout=25) as response:
        b.need(urllib.parse.urlsplit(response.url).scheme == 'https', 'NON_HTTPS_REDIRECT')
        return bounded(response)


def request(path, token, method='GET', data=None, upload=False):
    url = path if upload else API + path
    if upload:
        parsed = urllib.parse.urlsplit(url)
        b.need(parsed.scheme == 'https' and parsed.netloc == 'uploads.github.com'
               and parsed.path.startswith('/repos/' + REPO + '/releases/'), 'UPLOAD_DESTINATION')
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'second-paddle-skill-release/1'}
    if isinstance(data, dict):
        raw = json.dumps(data).encode(); headers['Content-Type'] = 'application/json'
    else:
        raw = data
        if raw is not None:
            headers['Content-Type'] = 'application/octet-stream'
    req = urllib.request.Request(url, method=method, data=raw, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=25) as response:
            return response.status, bounded(response), None
    except urllib.error.HTTPError as exc:
        code, location = exc.code, exc.headers.get('Location')
        exc.close()
        return code, b'', location


def api(path, token, method='GET', data=None):
    code, raw, _ = request(path, token, method, data)
    b.need(code in (200, 201), 'GITHUB_HTTP_' + str(code))
    return json.loads(raw)


def releases(token):
    rows = api('/releases?per_page=100', token)
    b.need(isinstance(rows, list) and len(rows) < 100, 'INCOMPLETE_RELEASE_LIST')
    return rows


def existing_snapshot(rows):
    return {str(row['id']): {'tag': row['tag_name'], 'assets': {
        str(a['id']): {'name': a['name'], 'size': a['size'], 'digest': a.get('digest')}
        for a in row['assets']}} for row in rows if row['tag_name'] != TAG}


def main():
    b.need(os.environ.get('GITHUB_REPOSITORY') == REPO and
           os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and
           os.environ.get('RELEASE_HEAD_REPO') == REPO and
           os.environ.get('RELEASE_HEAD_BRANCH') == BRANCH, 'PUBLICATION_CONTEXT')
    head = os.environ['RELEASE_HEAD_SHA']
    b.need(re.fullmatch('[0-9a-f]{40}', head) is not None, 'HEAD_SHA')
    token = os.environ['RELEASE_TOKEN']
    out = Path(os.environ['RELEASE_OUT'])
    out.mkdir(parents=True, exist_ok=False)
    journal = {'status': 'incomplete', 'tag': TAG, 'build_head': head, 'events': []}
    def event(kind, **fields):
        journal['events'].append({'event': kind, **fields})
        (out / 'publication.json').write_bytes(b.encode(journal))
    try:
        repo = api('', token)
        b.need(repo['private'] is False, 'PUBLIC_REPOSITORY_REQUIRED')
        # Binary originals go directly from GitHub to the runner, not through text.
        originals = {}
        for pin in b.CONFIG['artifacts']:
            code, raw, location = request('/actions/artifacts/' + str(pin['id']) + '/zip', token)
            if code in (301, 302, 303, 307, 308):
                b.need(bool(location), 'MISSING_ORIGINAL_LOCATION')
                raw = public_download(location)
            else:
                b.need(code == 200, 'ARTIFACT_HTTP_' + str(code))
            b.need(b.info(raw) == {k: pin[k] for k in ('bytes', 'sha256')}, 'ORIGINAL_IDENTITY')
            originals[pin['filename']] = raw
        assets = b.build(Path.cwd(), originals)
        b.need(assets == b.build(Path.cwd(), originals), 'BUILD_CHANGED')
        b.need({n: b.info(raw) for n, raw in assets.items()} == EXPECTED, 'ASSET_PIN')
        checks = b.verify_extracted(assets[b.RUNTIME])
        (out / 'before-publication-checks.json').write_bytes(b.encode(checks))
        for name, raw in assets.items():
            (out / name).write_bytes(raw)
        event('prepared_exact_assets', assets=EXPECTED, historical_archives=len(originals))
        before = releases(token)
        untouched = existing_snapshot(before)
        matches = [row for row in before if row['tag_name'] == TAG]
        b.need(len(matches) <= 1, 'AMBIGUOUS_RELEASE')
        if matches:
            release = matches[0]
            b.need(release['name'] == TITLE and release['body'] == BODY
                   and release['target_commitish'] == head and release['prerelease'] is True, 'UNEXPECTED_EXISTING_RELEASE')
        else:
            release = api('/releases', token, 'POST', {'tag_name': TAG, 'target_commitish': head,
                'name': TITLE, 'body': BODY, 'draft': True, 'prerelease': True, 'make_latest': 'false'})
            event('draft_created', release_id=release['id'])
        rid = release['id']
        journal['release_id'] = rid
        release = api('/releases/' + str(rid), token)
        found = {a['name']: a for a in release['assets']}
        b.need(len(found) == len(release['assets']) and set(found) <= set(assets), 'UNEXPECTED_ASSETS')
        upload = release['upload_url'].split('{', 1)[0]
        b.need(urllib.parse.urlsplit(upload).path == '/repos/' + REPO + '/releases/' + str(rid) + '/assets', 'UPLOAD_PATH')
        for name, raw in assets.items():
            if name not in found:
                b.need(release['draft'] is True, 'WILL_NOT_MODIFY_PUBLISHED_RELEASE')
                code, body, _ = request(upload + '?name=' + urllib.parse.quote(name, safe=''), token,
                                        'POST', raw, upload=True)
                b.need(code == 201, 'UPLOAD_HTTP_' + str(code))
                asset = json.loads(body)
            else:
                asset = found[name]
            b.need(asset['state'] == 'uploaded' and asset['size'] == len(raw)
                   and asset.get('digest') == 'sha256:' + b.digest(raw), 'REMOTE_ASSET_IDENTITY')
            event('asset_verified', name=name, id=asset['id'], **b.info(raw))
        if release['draft']:
            release = api('/releases/' + str(rid), token, 'PATCH', {'draft': False, 'make_latest': 'false'})
        event('public_release', release_id=rid)
        # Read the public metadata and every asset without authorization/cookies.
        public = json.loads(public_download(API + '/releases/tags/' + TAG))
        b.need(public['id'] == rid and public['draft'] is False and public['prerelease'] is True, 'PUBLIC_RELEASE_IDENTITY')
        downloads = {}
        for asset in public['assets']:
            name = asset['name']
            b.need(name in assets, 'UNEXPECTED_PUBLIC_ASSET')
            expected_url = 'https://github.com/' + REPO + '/releases/download/' + TAG + '/' + name
            b.need(asset['browser_download_url'] == expected_url, 'PUBLIC_ASSET_URL')
            raw = public_download(expected_url)
            b.need(raw == assets[name], 'PUBLIC_BYTES_DIFFER')
            downloads[name] = b.info(raw)
            if name == b.RUNTIME:
                checked = b.verify_extracted(raw)
                (out / 'public-package-checks.json').write_bytes(b.encode(checked))
        b.need(downloads == EXPECTED, 'PUBLIC_ASSET_SET')
        after = existing_snapshot(releases(token))
        b.need(all(after.get(k) == v for k,v in untouched.items()), 'OLD_RELEASE_CHANGED')
        journal.update(status='verified', public_url=public['html_url'], public_downloads=downloads,
                       old_releases_unchanged=len(untouched), public_download_authentication=False,
                       new_fault_experiments=0, user_profile_installations=0)
        event('public_acquisition_checked')
        print(json.dumps(journal, indent=2))
    except Exception as exc:
        journal.update(status='failed', failure_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            journal['failure_code'] = str(exc)
        event('failure')
        raise


if __name__ == '__main__':
    main()
