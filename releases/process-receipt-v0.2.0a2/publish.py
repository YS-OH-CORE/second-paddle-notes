#!/usr/bin/env python3
"""Publish one fixed corrective alpha; add dated notices without replacing assets.

Publication and notices require this repository's explicit main push. No rebuild,
model call, credential creation, implicit retry, or recurring operation.
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
TAG = 'process-receipt-v0.2.0a2'
SOURCE = 'b17f5f8cfa107a917ab87011a08487d05b90a1dd'
BUILD_HEAD = 'f0b98590bf1dfd138563b93229a24a74602127f7'
RUN = 34575924199
ARTIFACT = 10189621151
ARCHIVE_SHA = 'ada8685d34562426dbd8603a5f7dfea056612a6c7d19654b6c8b364f90e8b606'
WHEEL = 'second_paddle_process_receipt-0.2.0a2-py3-none-any.whl'
WHEEL_SHA = '69c96c6d1be62b4031e6e0f7d5ebf874bf551f15433f75b296c685b9ce2c907d'
DIST = 'second_paddle_process_receipt-0.2.0a2.dist-info/'
MODULES = {
    'process_receipt.py': '4bb444f5e6607c0a44e0a1f1a070e79e2dc3012d6b64ede1591a45c9180f92db',
    'process_receipt_cli.py': 'df3e3a1e66a2687041e6c55b3f44fb2de2605778bc5dad9c18e1a79821d0cd19',
    'process_receipt_windows.py': 'be3246ec70f5d48f3babf1bedacda36ee6394a8ee87284a821e48a0a005a9f2b',
}
NAMES = {WHEEL, 'BUILD_PROVENANCE.json', 'SHA256SUMS'}
PREFIX = f'repos/{REPO}/'
OLD_RELEASES = {386679814: 'process-receipt-v0.1.0', 386843459: 'process-receipt-v0.2.0a1'}
MARK = '<!-- process-receipt-persistence-correction-20260911 -->'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def wheel_modules(raw: bytes) -> dict[str, bytes]:
    require(len(raw) == 13000 and sha(raw) == WHEEL_SHA, 'Not the tested corrective wheel')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(len(z.namelist()) == len(set(z.namelist())) and sum(n.file_size for n in z.infolist()) < 200000, 'Invalid wheel bounds')
        require(z.testzip() is None, 'Wheel CRC failure')
        require({n for n in z.namelist() if not n.startswith(DIST)} == set(MODULES), 'Unexpected runtime member')
        meta = BytesParser().parsebytes(z.read(DIST+'METADATA'))
        require(meta['Name'] == 'second-paddle-process-receipt' and meta['Version'] == '0.2.0a2' and not meta.get_all('Requires-Dist'), 'Wrong metadata')
        ep = configparser.ConfigParser()
        ep.read_string(z.read(DIST+'entry_points.txt').decode())
        require(ep['console_scripts']['process-receipt'] == 'process_receipt_cli:main', 'Wrong entry point')
        result = {n: z.read(n) for n in MODULES}
        require({n: sha(b) for n, b in result.items()} == MODULES, 'Runtime identity mismatch')
        return result


def prepare(archive: Path, out: Path) -> dict:
    raw = archive.read_bytes()
    require(len(raw) == 24898 and sha(raw) == ARCHIVE_SHA, 'Source artifact mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(z.testzip() is None and len(z.namelist()) == len(set(z.namelist())), 'Invalid artifact ZIP')
        data = z.read('process-native-build/dist/'+WHEEL)
        installation = json.loads(z.read('process-native-build/installation/results/summary.json'))
        faults = json.loads(z.read('receipt-io-evidence/candidate-counts.json'))
    wheel_modules(data)
    require(installation['status'] == 'verified' and installation['version'] == '0.2.0a2'
            and installation['os_name'] == 'nt' and installation['wheel_sha256'] == WHEEL_SHA, 'Native installation evidence absent')
    require(faults == dict(tests=9, failures=0, errors=0, skipped=1, success=True), 'Native fault regression evidence absent')
    out.mkdir(parents=True, exist_ok=False)
    (out/WHEEL).write_bytes(data)
    provenance = dict(schema='process-receipt-corrective-release-v1', repository=REPO,
        release_tag=TAG, source_commit=SOURCE, build_head=BUILD_HEAD, build_run=RUN,
        build_artifact=ARTIFACT, artifact_sha256=ARCHIVE_SHA, wheel=WHEEL,
        wheel_bytes=len(data), wheel_sha256=WHEEL_SHA, runtime_sha256=MODULES,
        operation='Promote the existing Windows-tested wheel; no rebuild.',
        fix='Separate final receipt I/O failure from observed execution; restore handlers even after close failure.',
        evidence=f'https://github.com/{REPO}/pull/12',
        limits='Author-run engineering evidence. No exactly-once, durable fallback, rollback or independent certification.')
    dump(out/'BUILD_PROVENANCE.json', provenance)
    (out/'SHA256SUMS').write_text(''.join(f'{sha((out/n).read_bytes())}  {n}\n' for n in (WHEEL, 'BUILD_PROVENANCE.json')), encoding='utf-8')
    return provenance


def gh(*args: str, payload: dict | None = None) -> bytes:
    command = ['gh', 'api', *args]
    if payload is not None:
        command += ['--input', '-']
    p = subprocess.run(command, input=json.dumps(payload).encode() if payload is not None else None,
                       capture_output=True, timeout=45, check=False)
    require(p.returncode == 0, 'GitHub request failed; inspect state before retrying')
    return p.stdout


def api(path: str, *, payload: dict | None = None, method: str = 'GET'):
    return json.loads(gh('--method', method, PREFIX+path, payload=payload))


def main_write_gate() -> str:
    require(os.environ.get('GITHUB_REPOSITORY') == REPO and os.environ.get('GITHUB_EVENT_NAME') == 'push'
            and os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Explicit owner main push required')
    commit = os.environ['GITHUB_SHA']
    require(api('git/ref/heads/main')['object']['sha'] == commit, 'Main changed')
    return commit


def prepare_remote(out: Path) -> Path:
    run = api(f'actions/runs/{RUN}')
    require(run['head_sha'] == BUILD_HEAD and run['conclusion'] == 'success', 'Build not confirmed')
    a = api(f'actions/artifacts/{ARTIFACT}')
    require(not a['expired'] and a['digest'] == 'sha256:'+ARCHIVE_SHA and a['workflow_run']['id'] == RUN, 'Artifact changed or expired')
    out.mkdir(parents=True, exist_ok=False)
    archive = out/'original.zip'
    archive.write_bytes(gh(PREFIX+f'actions/artifacts/{ARTIFACT}/zip'))
    assets = out/'assets'
    prepare(archive, assets)
    for n, data in wheel_modules((assets/WHEEL).read_bytes()).items():
        require((Path(__file__).resolve().parents[2]/'tools/process-receipt'/n).read_bytes() == data, 'Checkout runtime differs')
    dump(out/'preflight.json', dict(status='fixed_artifact_verified', wheel_sha256=WHEEL_SHA, release_written=False))
    return assets


def release_identity(r: dict) -> dict:
    keys = ('id', 'tag_name', 'target_commitish', 'body', 'draft', 'prerelease')
    return {**{k: r[k] for k in keys}, 'assets': sorted([
        {k: a.get(k) for k in ('id', 'name', 'size', 'digest', 'state')} for a in r['assets']
    ], key=lambda a: a['id'])}


def assert_assets(r: dict, folder: Path, *, complete: bool = True) -> None:
    assets = r['assets']
    require(len(assets) == len({a['name'] for a in assets}) and {a['name'] for a in assets} <= NAMES, 'Unexpected assets')
    if complete:
        require({a['name'] for a in assets} == NAMES, 'Missing assets')
    for a in assets:
        data = (folder/a['name']).read_bytes()
        require(a['state'] == 'uploaded' and a['size'] == len(data) and a.get('digest') == 'sha256:'+sha(data), 'Conflicting asset')
        require(gh('-H', 'Accept: application/octet-stream', PREFIX+f"releases/assets/{a['id']}") == data, 'Remote bytes differ')


def publish(out: Path) -> None:
    commit = main_write_gate()
    assets = prepare_remote(out)
    releases = api('releases?per_page=100')
    require(len(releases) < 100, 'Incomplete release listing')
    old = {r['id']: release_identity(r) for r in releases if r['tag_name'] != TAG}
    matches = [r for r in releases if r['tag_name'] == TAG]
    require(len(matches) <= 1, 'Duplicate release')
    notes = Path(__file__).with_name('NOTES.md').read_text(encoding='utf-8')
    r = matches[0] if matches else api('releases', method='POST', payload=dict(tag_name=TAG,
        target_commitish=SOURCE, name='Process Receipt 0.2.0a2: receipt failure reporting fix (alpha)',
        body=notes, draft=True, prerelease=True, make_latest='false'))
    dump(out/'draft-checkpoint.json', dict(release_id=r['id'], tag=TAG, draft=r['draft']))
    require(r['target_commitish'] == SOURCE and r['body'] == notes and r['prerelease'], 'Existing release differs')
    assert_assets(r, assets, complete=not r['draft'])
    if r['draft']:
        url = r['upload_url'].split('{', 1)[0]
        require(url == f"https://uploads.github.com/repos/{REPO}/releases/{r['id']}/assets", 'Unexpected upload destination')
        for name in sorted(NAMES-{a['name'] for a in r['assets']}):
            gh('--method', 'POST', url+'?name='+name, '-H', 'Content-Type: application/octet-stream', '--input', str(assets/name))
        r = api(f"releases/{r['id']}")
        assert_assets(r, assets)
        require(main_write_gate() == commit, 'Main moved')
        api(f"releases/{r['id']}", method='PATCH', payload=dict(draft=False, prerelease=True, make_latest='false'))
    r = api(f"releases/{r['id']}")
    require(not r['draft'] and r['prerelease'], 'Not a published alpha')
    assert_assets(r, assets)
    for rid, prior in old.items():
        require(release_identity(api(f'releases/{rid}')) == prior, 'Older release changed during publication')
    dump(out/'publication.json', dict(status='published_and_assets_read_back', release_id=r['id'],
        url=r['html_url'], tag=TAG, wheel_sha256=WHEEL_SHA, rebuilt=False, overwritten_assets=0,
        prior_releases_unchanged=True, public_consumer_verified=False))


def notice_suffix() -> str:
    return '\n\n---\n\n'+MARK+'\n'+Path(__file__).with_name('NOTICE.md').read_text(encoding='utf-8')


def notified_body(body: str) -> str:
    suffix = notice_suffix()
    if MARK in body:
        require(body.endswith(suffix) and body.count(MARK) == 1, 'Existing notice differs; leave untouched')
        return body
    return body+suffix


def notices(out: Path) -> None:
    main_write_gate()
    new = api('releases/tags/'+TAG)
    require(new['tag_name'] == TAG and new['target_commitish'] == SOURCE and not new['draft'], 'Correction release not public')
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for rid, tag in OLD_RELEASES.items():
        path = f'releases/{rid}'
        before = api(path)
        require(before['tag_name'] == tag and not before['draft'], 'Unexpected older release')
        snapshot = release_identity(before)
        body = notified_body(before['body'])
        dump(out/f'{rid}-before.json', snapshot)
        if body != before['body']:
            require(release_identity(api(path)) == snapshot, 'Release changed before notice')
            api(path, method='PATCH', payload={'body': body})
        after = api(path)
        expected = {**snapshot, 'body': body}
        require(release_identity(after) == expected, 'Notice readback differs')
        rows.append(dict(release_id=rid, tag=tag, body_only_notice_added=body != before['body'],
                         original_body_retained=True, assets_and_target_unchanged=True, url=after['html_url']))
    dump(out/'notices.json', dict(status='older_release_notices_read_back', records=rows,
        concurrency_limit='Read-before-write comparison is not an atomic cross-client edit lock.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--publish', action='store_true')
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--notices', action='store_true')
    modes.add_argument('--check-archive', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    out = a.out.resolve()
    if a.publish:
        publish(out)
    elif a.prepare:
        prepare_remote(out)
    elif a.notices:
        notices(out)
    else:
        prepare(a.check_archive, out)
