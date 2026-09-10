#!/usr/bin/env python3
"""One fixed, source-pinned release. Never rebuild or overwrite a release asset.

This is project publication code, not an autonomous agent or general executor.
Only --publish uses the existing workflow token. --verify-public uses no token.
"""
from __future__ import annotations
import argparse
import configparser
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

REPO = 'YS-OH-CORE/second-paddle-notes'
TAG = 'process-receipt-v0.1.0'
SOURCE = '388efef41ae8f0a754ba5508fc7fcccc819a97c0'
RUN = 34539459938
ARTIFACT = 10176690471
ARCHIVE_SHA = '22f51dbf1193e95edfbdf683df2bd094c3b3984073ccd3a58cab4ab4dae67424'
WHEEL = 'second_paddle_process_receipt-0.1.0-py3-none-any.whl'
WHEEL_SHA = '6c4242fcf26685e9b0740ac634aca0bdc4c5c4a1e3532da224d102f74c1a73e8'
MODULE_BLOB = '1243c33f07a974bc3f2f9a0d03865534224c33e4'
DIST = 'second_paddle_process_receipt-0.1.0.dist-info/'
API = f'https://api.github.com/repos/{REPO}'
URL = f'https://github.com/{REPO}/releases/download/{TAG}/'
NAMES = {WHEEL, 'SHA256SUMS', 'BUILD_PROVENANCE.json'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def wheel_module(data: bytes) -> bytes:
    require(len(data) == 10088 and sha(data) == WHEEL_SHA, 'Not the already verified wheel')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate wheel member')
        require(sum(x.file_size for x in z.infolist()) < 200000, 'Oversized wheel')
        require(z.testzip() is None, 'Wheel CRC failure')
        meta = BytesParser().parsebytes(z.read(DIST + 'METADATA'))
        require(meta['Name'] == 'second-paddle-process-receipt' and meta['Version'] == '0.1.0', 'Wrong metadata')
        require(not meta.get_all('Requires-Dist'), 'Unexpected runtime dependency')
        ep = configparser.ConfigParser()
        ep.read_string(z.read(DIST + 'entry_points.txt').decode())
        require(ep['console_scripts']['process-receipt'] == 'process_receipt:main', 'Wrong entry point')
        module = z.read('process_receipt.py')
        blob = hashlib.sha1(b'blob ' + str(len(module)).encode() + b'\0' + module).hexdigest()
        require(blob == MODULE_BLOB, 'Runtime module changed')
        return module


def prepare(archive: Path, out: Path) -> dict:
    raw = archive.read_bytes()
    require(len(raw) == 16362 and sha(raw) == ARCHIVE_SHA, 'Unexpected CI artifact bytes')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate artifact member')
        require(sum(x.file_size for x in z.infolist()) < 500000, 'Oversized artifact')
        require(z.testzip() is None, 'Artifact CRC failure')
        data = z.read('process-package-dist/' + WHEEL)
    wheel_module(data)
    out.mkdir(parents=True, exist_ok=False)
    (out / WHEEL).write_bytes(data)
    provenance = dict(schema='process-receipt-build-origin-v1', repository=REPO,
        source_commit=SOURCE, build_run=RUN, build_artifact=ARTIFACT,
        artifact_sha256=ARCHIVE_SHA, wheel=WHEEL, wheel_sha256=WHEEL_SHA,
        runtime_git_blob=MODULE_BLOB, release_tag=TAG,
        operation='Promote the existing tested wheel bytes; no rebuild.',
        evidence=f'https://github.com/{REPO}/actions/runs/{RUN}',
        limits='Author-run packaging and process checks, not independent adoption, a model evaluation or a signature.')
    dump(out / 'BUILD_PROVENANCE.json', provenance)
    sums = ''.join(f'{sha((out / n).read_bytes())}  {n}\n' for n in (WHEEL, 'BUILD_PROVENANCE.json'))
    (out / 'SHA256SUMS').write_text(sums, encoding='utf-8')
    return provenance


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['gh', *args], check=True, capture_output=True, timeout=45)


def api(path: str) -> object:
    return json.loads(gh('api', f'repos/{REPO}/{path}').stdout)


def asset_metadata(release: dict, folder: Path) -> None:
    assets = release['assets']
    require(len(assets) == 3 and {a['name'] for a in assets} == NAMES, 'Unexpected release assets')
    for asset in assets:
        data = (folder / asset['name']).read_bytes()
        require(asset['state'] == 'uploaded' and asset['size'] == len(data), 'Incomplete asset')
        digest = asset.get('digest')
        require(digest is None or digest == 'sha256:' + sha(data), 'Remote asset digest mismatch')


def publish(out: Path) -> None:
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'Wrong repository')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'push' and os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Only explicit main publication commits')
    commit = os.environ['GITHUB_SHA']
    require(api('git/ref/heads/main')['object']['sha'] == commit, 'Publication commit is not current main')
    run = api(f'actions/runs/{RUN}')
    require(run['head_sha'] == SOURCE and run['conclusion'] == 'success', 'Source build not verified')
    items = api(f'actions/runs/{RUN}/artifacts')['artifacts']
    a = [a for a in items if a['id'] == ARTIFACT]
    require(len(a) == 1 and not a[0]['expired'] and a[0]['digest'] == 'sha256:' + ARCHIVE_SHA, 'Source artifact missing/expired/changed')
    out.mkdir(parents=True, exist_ok=False)
    archive = out / 'original-ci.zip'
    archive.write_bytes(gh('api', f'repos/{REPO}/actions/artifacts/{ARTIFACT}/zip').stdout)
    assets = out / 'assets'
    prepare(archive, assets)
    module = wheel_module((assets / WHEEL).read_bytes())
    checkout = Path(__file__).resolve().parents[2]
    require((checkout / 'tools/process-receipt/process_receipt.py').read_bytes() == module, 'Publication checkout has a different runtime')
    # The first publication attempt created this exact draft, then used a
    # published-tag-only endpoint to read it. Finish that inspected draft only.
    # No further release/tag creation, asset overwrite, or deletion is allowed.
    releases = api('releases?per_page=100')
    require(len(releases) < 100, 'Incomplete release listing')
    matches = [r for r in releases if r['tag_name'] == TAG]
    require(len(matches) == 1, 'Expected exactly the inspected release')
    draft = matches[0]
    require(draft['id'] == 386679814, 'Not the inspected draft ID')
    require(draft['target_commitish'] == '3e2d64f896fe6f9f11e3180914c1b5bc8cb2e15c', 'Draft target changed')
    require(draft['author']['login'] == 'github-actions[bot]', 'Unexpected draft author')
    require(draft['body'] == Path(__file__).with_name('NOTES.md').read_text(encoding='utf-8'), 'Draft notes changed')
    asset_metadata(draft, assets)
    returned = out / 'draft-readback'
    returned.mkdir()
    for item in draft['assets']:
        data = gh('api', '-H', 'Accept: application/octet-stream',
                  f"repos/{REPO}/releases/assets/{item['id']}").stdout
        require(data == (assets / item['name']).read_bytes(), 'Remote asset bytes differ')
        (returned / item['name']).write_bytes(data)
    if not draft['draft']:
        dump(out / 'publication.json', dict(status='existing_release_left_unchanged',
            release_id=draft['id'], url=draft['html_url'], asset_bytes_verified=True))
        return
    require(api('git/ref/heads/main')['object']['sha'] == commit, 'Main changed before publication')
    # PATCH the known ID, never infer that a tag endpoint's 404 means no draft.
    gh('api', '--method', 'PATCH', f"repos/{REPO}/releases/{draft['id']}",
       '-F', 'draft=false', '-F', 'prerelease=true', '-f', 'make_latest=false')
    final = api(f"releases/{draft['id']}")
    require(not final['draft'] and final['prerelease'], 'Release not published as alpha')
    asset_metadata(final, assets)
    dump(out / 'publication.json', dict(status='published_and_authenticated_readback_verified',
        release_id=final['id'], tag=TAG, url=final['html_url'], source_commit=SOURCE,
        publication_commit=final['target_commitish'], finalizer_commit=commit, wheel_sha256=WHEEL_SHA,
        recovered_same_draft=True, assets_reuploaded=False,
        anonymous_download_verified=False, prior_release_not_modified=True))
    print(final['html_url'])


def public_get(url: str) -> bytes:
    # Deliberately no GitHub credentials or authenticated browser session.
    request = urllib.request.Request(url, headers={'User-Agent': 'process-receipt-public-download-check/0.1', 'Accept': 'application/octet-stream' if '/download/' in url else 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        require(response.status == 200 and response.url.startswith('https://'), 'Unexpected public response')
        data = response.read(1_000_001)
    require(len(data) <= 1_000_000, 'Oversized public response')
    return data


def verify_public(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)
    release = json.loads(public_get(API + '/releases/tags/' + TAG))
    require(not release['draft'] and release['tag_name'] == TAG, 'Not a public release')
    require(len(release['assets']) == 3 and {a['name'] for a in release['assets']} == NAMES, 'Public assets differ')
    data = public_get(URL + WHEEL)
    module = wheel_module(data)
    (out / WHEEL).write_bytes(data)
    expected_provenance = json.loads(public_get(URL + 'BUILD_PROVENANCE.json'))
    require(expected_provenance['source_commit'] == SOURCE and expected_provenance['wheel_sha256'] == WHEEL_SHA, 'Public provenance differs')
    sums = public_get(URL + 'SHA256SUMS').decode('utf-8')
    require(f'{WHEEL_SHA}  {WHEEL}\n' in sums, 'Public checksum absent')
    # Verify consumer installation without a package index, source checkout, or token.
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(out / 'home'),
           'LANG': 'C.UTF-8', 'PIP_CONFIG_FILE': os.devnull,
           'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_INPUT': '1'}
    Path(env['HOME']).mkdir()
    venv = out / 'consumer'
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=out, env=env, check=True, capture_output=True, text=True, timeout=40).stdout
    run([sys.executable, '-I', '-m', 'venv', str(venv)])
    python = str(venv / 'bin/python')
    install = run([python, '-I', '-m', 'pip', 'install', '--no-index', '--no-deps', str(out / WHEEL)])
    identity = json.loads(run([python, '-I', '-c', 'import process_receipt,json; print(json.dumps({"file":process_receipt.__file__}))']))
    installed = Path(identity['file'])
    require(installed.is_relative_to(venv) and installed.read_bytes() == module, 'Source fallback rather than installed package')
    help_text = run([str(venv / 'bin/process-receipt'), '--help'])
    require('--receipt' in help_text and '--stop-file' in help_text, 'Console command not functional')
    (out / 'install.txt').write_text(install, encoding='utf-8')
    (out / 'help.txt').write_text(help_text, encoding='utf-8')
    dump(out / 'anonymous-verification.json', dict(status='anonymous_download_and_clean_install_verified',
         observed_at=datetime.now(timezone.utc).isoformat(), release_id=release['id'],
         release_url=release['html_url'], wheel_url=URL + WHEEL, wheel_bytes=len(data), wheel_sha256=sha(data),
         source_commit=SOURCE, used_authorization_header=False, installation='no-index, no-deps, new venv',
         installed_module_matches=True, console_help_succeeded=True,
         third_party_adoption_observed=False, scope='Author-run consumer-path test; Linux only, no new model trial.'))
    print('Anonymous public download, exact wheel bytes, clean install and installed CLI verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--publish', action='store_true')
    mode.add_argument('--verify-public', action='store_true')
    mode.add_argument('--check-archive', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.publish:
        publish(out)
    elif args.verify_public:
        verify_public(out)
    else:
        prepare(args.check_archive, out)
        print('Existing archive, wheel metadata and runtime identity verified; no network call.')
