#!/usr/bin/env python3
"""Promote one tested alpha wheel without rebuilding or replacing existing assets.

Only --publish writes to the owner's GitHub release, using a workflow-scoped token.
--prepare only reads the fixed artifact. --check-archive has no network operations.
"""
from __future__ import annotations
import argparse
import configparser
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

REPO = 'YS-OH-CORE/second-paddle-notes'
TAG = 'process-receipt-v0.2.0a1'
SOURCE = '753933c1ea85711df4928695cba6374c79487518'
BUILD_HEAD = '5c07e65a4ebeb6c9323aab8c1cd9237bdbab2c0b'
BUILD_CHECKOUT = '70e8f6a5c667be9fbb1f8bb47b3b5b520bf2473c'
RUN = 34569094695
ARTIFACT = 10187093500
ARCHIVE_SHA = 'bae34f9282b0e791f0b321c3d79b11fcb1fdc8d2feda489d942c32766efeda5f'
WHEEL = 'second_paddle_process_receipt-0.2.0a1-py3-none-any.whl'
WHEEL_SHA = '13b47b0416b519e42596fd0ea7a0c2c929edbdd17488ae53adfa7031745c7032'
DIST = 'second_paddle_process_receipt-0.2.0a1.dist-info/'
MODULES = {
    'process_receipt.py': 'ecadd494ec2ac59877b35d713481ce27c820635d5915b54e9b56046f3b86fed0',
    'process_receipt_cli.py': 'e47b96b628e44f014fdf8ebe5b2dc954009d06251ede41c62762e9c46ddcbb6b',
    'process_receipt_windows.py': 'd2057044d6b4ceb372ad9c92238ee8bfe95cb9df7993c14c03480829f2dfc91f',
}
NAMES = {WHEEL, 'BUILD_PROVENANCE.json', 'SHA256SUMS'}
PREFIX = f'repos/{REPO}/'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def wheel_modules(raw: bytes) -> dict[str, bytes]:
    require(len(raw) == 12476 and sha(raw) == WHEEL_SHA, 'Not the tested Windows alpha wheel')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(z.testzip() is None, 'Wheel CRC failed')
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate wheel member')
        require(sum(n.file_size for n in z.infolist()) < 200000, 'Oversized wheel')
        require({n for n in z.namelist() if not n.startswith(DIST)} == set(MODULES), 'Unexpected runtime member')
        meta = BytesParser().parsebytes(z.read(DIST+'METADATA'))
        require(meta['Name'] == 'second-paddle-process-receipt' and meta['Version'] == '0.2.0a1', 'Wrong package/version')
        require(not meta.get_all('Requires-Dist'), 'Unexpected runtime dependency')
        ep = configparser.ConfigParser()
        ep.read_string(z.read(DIST+'entry_points.txt').decode())
        require(ep['console_scripts']['process-receipt'] == 'process_receipt_cli:main', 'Wrong installed command')
        result = {name: z.read(name) for name in MODULES}
        require({n: sha(b) for n, b in result.items()} == MODULES, 'Runtime identity mismatch')
        return result


def prepare(archive: Path, out: Path) -> dict:
    raw = archive.read_bytes()
    require(len(raw) == 19256 and sha(raw) == ARCHIVE_SHA, 'Not the inspected source artifact')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(z.testzip() is None and len(z.namelist()) == len(set(z.namelist())), 'Invalid artifact ZIP')
        data = z.read('process-native-build/dist/'+WHEEL)
        summary = json.loads(z.read('process-native-build/installation/results/summary.json'))
    wheel_modules(data)
    require(summary['status'] == 'verified' and summary['os_name'] == 'nt'
            and summary['case_count'] == 10 and summary['wheel_sha256'] == WHEEL_SHA, 'Missing native build evidence')
    out.mkdir(parents=True, exist_ok=False)
    (out/WHEEL).write_bytes(data)
    provenance = dict(schema='process-receipt-fixed-alpha-origin-v1', repository=REPO,
        release_tag=TAG, source_commit=SOURCE, build_head=BUILD_HEAD,
        build_checkout=BUILD_CHECKOUT, build_run=RUN, build_artifact=ARTIFACT,
        artifact_sha256=ARCHIVE_SHA, wheel=WHEEL, wheel_sha256=WHEEL_SHA,
        wheel_bytes=len(data), runtime_sha256=MODULES,
        operation='Promote the exact native-Windows-tested wheel bytes. No rebuild.',
        historical_native_windows_cases=10,
        historical_linux_evidence='Same runtime bytes, separately built wheel; not whole-wheel identity.',
        evidence=f'https://github.com/{REPO}/actions/runs/{RUN}',
        limits='Author-run direct-child engineering checks; not independent certification or model evaluation.')
    dump(out/'BUILD_PROVENANCE.json', provenance)
    (out/'SHA256SUMS').write_text(''.join(f'{sha((out/n).read_bytes())}  {n}\n'
                                        for n in (WHEEL, 'BUILD_PROVENANCE.json')), encoding='utf-8')
    return provenance


def gh(*args: str, payload: dict | None = None) -> bytes:
    command = ['gh', 'api', *args]
    if payload is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(payload).encode() if payload is not None else None,
                            capture_output=True, timeout=45, check=False)
    require(result.returncode == 0, 'GitHub request failed; no automatic write retry or credential fallback')
    return result.stdout


def api(path: str, *, payload: dict | None = None, method: str = 'GET'):
    return json.loads(gh('--method', method, PREFIX+path, payload=payload))


def prepare_remote(out: Path) -> Path:
    run = api(f'actions/runs/{RUN}')
    require(run['head_sha'] == BUILD_HEAD and run['conclusion'] == 'success', 'Pinned run is not successful')
    metadata = api(f'actions/artifacts/{ARTIFACT}')
    require(not metadata['expired'] and metadata['digest'] == 'sha256:'+ARCHIVE_SHA
            and metadata['workflow_run']['id'] == RUN, 'Pinned artifact changed or expired')
    out.mkdir(parents=True, exist_ok=False)
    archive = out/'source-artifact.zip'
    archive.write_bytes(gh(PREFIX+f'actions/artifacts/{ARTIFACT}/zip'))
    assets = out/'assets'
    prepare(archive, assets)
    checkout = Path(__file__).resolve().parents[2]
    for name, raw in wheel_modules((assets/WHEEL).read_bytes()).items():
        require((checkout/'tools/process-receipt'/name).read_bytes() == raw, 'Current source differs from tested wheel')
    dump(out/'preflight.json', {'status': 'fixed_artifact_verified', 'wheel_sha256': WHEEL_SHA,
                                'runtime_matches_checkout': True, 'release_written': False})
    return assets


def release_identity(release: dict) -> dict:
    # Exclude mutable download counters while preserving content, IDs and digests.
    keys = ('id', 'tag_name', 'target_commitish', 'body', 'draft', 'prerelease')
    return {**{k: release[k] for k in keys}, 'assets': sorted([
        {k: a.get(k) for k in ('id', 'name', 'size', 'digest', 'state')} for a in release['assets']
    ], key=lambda x: x['id'])}


def assert_assets(release: dict, folder: Path, *, complete: bool = True) -> None:
    assets = release['assets']
    require(len(assets) == len({a['name'] for a in assets}), 'Duplicate remote assets')
    require({a['name'] for a in assets} <= NAMES, 'Unexpected existing release asset')
    if complete:
        require({a['name'] for a in assets} == NAMES, 'Missing release asset')
    for a in assets:
        data = (folder/a['name']).read_bytes()
        require(a['state'] == 'uploaded' and a['size'] == len(data)
                and a.get('digest') == 'sha256:'+sha(data), 'Incomplete or conflicting release asset')
        returned = gh('-H', 'Accept: application/octet-stream', PREFIX+f"releases/assets/{a['id']}")
        require(returned == data, 'Remote asset bytes do not match prepared bytes')


def publish(out: Path) -> None:
    require(os.environ.get('GITHUB_REPOSITORY') == REPO
            and os.environ.get('GITHUB_EVENT_NAME') == 'push'
            and os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Only this repository main publication commit')
    commit = os.environ['GITHUB_SHA']
    require(api('git/ref/heads/main')['object']['sha'] == commit, 'Main changed before publication')
    assets = prepare_remote(out)
    releases = api('releases?per_page=100')
    require(len(releases) < 100, 'Release listing may be incomplete')
    old = {r['id']: release_identity(r) for r in releases if r['tag_name'] != TAG}
    matches = [r for r in releases if r['tag_name'] == TAG]
    require(len(matches) <= 1, 'Duplicate tag release')
    notes = Path(__file__).with_name('NOTES.md').read_text(encoding='utf-8')
    if matches:
        release = matches[0]
    else:
        release = api('releases', method='POST', payload=dict(tag_name=TAG,
            target_commitish=SOURCE, name='Process Receipt 0.2.0a1: Windows + Linux (experimental)',
            body=notes, draft=True, prerelease=True, make_latest='false'))
    dump(out/'draft-checkpoint.json', {'release_id': release['id'], 'tag': TAG, 'draft': release['draft']})
    require(release['tag_name'] == TAG and release['target_commitish'] == SOURCE
            and release['body'] == notes and release['prerelease'], 'Existing release differs; leave untouched')
    assert_assets(release, assets, complete=not release['draft'])
    uploaded = []
    if release['draft']:
        url = release['upload_url'].split('{', 1)[0]
        require(url == f"https://uploads.github.com/repos/{REPO}/releases/{release['id']}/assets", 'Unexpected upload destination')
        existing = {a['name'] for a in release['assets']}
        for name in sorted(NAMES-existing):
            gh('--method', 'POST', url+'?name='+name, '-H', 'Content-Type: application/octet-stream',
               '--input', str(assets/name))
            uploaded.append(name)
        release = api(f"releases/{release['id']}")
        assert_assets(release, assets)
        require(api('git/ref/heads/main')['object']['sha'] == commit, 'Main changed; leave verified draft unpublished')
        release = api(f"releases/{release['id']}", method='PATCH',
                      payload={'draft': False, 'prerelease': True, 'make_latest': 'false'})
    final = api(f"releases/{release['id']}")
    require(not final['draft'] and final['prerelease'], 'Alpha publication not confirmed')
    assert_assets(final, assets)
    for release_id, snapshot in old.items():
        require(release_identity(api(f'releases/{release_id}')) == snapshot, 'Prior release metadata changed')
    dump(out/'publication.json', dict(status='published_assets_read_back', release_id=final['id'],
        url=final['html_url'], tag=TAG, wheel_sha256=WHEEL_SHA, source_commit=SOURCE,
        publication_commit=commit, uploaded=uploaded, overwritten_assets=0, rebuilt=False,
        prior_release_identities_preserved=True, public_consumer_verified=False))
    print(final['html_url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--publish', action='store_true')
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--check-archive', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.publish:
        publish(out)
    elif args.prepare:
        prepare_remote(out)
    else:
        prepare(args.check_archive, out)
        print('Exact source archive and wheel verified offline; no publication performed.')
