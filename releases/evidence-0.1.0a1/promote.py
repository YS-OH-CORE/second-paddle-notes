"""Promote one already-tested wheel; preserve original execution evidence.

No rebuild, package installation or model call. The publisher only creates this
fixed prerelease in the owner's existing repository. Conflicts stop, never clobber.
"""
from __future__ import annotations
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
from urllib.request import urlopen
import zipfile

REPO = 'YS-OH-CORE/second-paddle-notes'
TAG = 'evidence-v0.1.0a1'
TARGET = 'e0399c96bf2bdcbcd841eafa5f257070751a624e'
WHEEL = 'second_paddle_evidence-0.1.0a1-py3-none-any.whl'
WHEEL_SHA = '0e509a17ee164189abea151996cb084de6fc55990ee0ce4d8a9a70bed5b984bd'
ORIGINALS = {
    'linux': (10303401390, 20308, '184c277574ffaf68ba06920ed7f5eedf4aa9a1b610837a7c92cf3fc863b18811'),
    'windows': (10303122004, 20415, '3e5c930519edc3a5dc28bf55df30167c352fe3e282d07ca062b6126f34920a65'),
}
NAMES = [WHEEL, 'ORIGINAL-linux.zip', 'ORIGINAL-windows.zip', 'PROVENANCE.json', 'SHA256SUMS']


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def gh(*args: str) -> bytes:
    return subprocess.check_output(['gh', *args], timeout=90)


def inspect_original(data: bytes, mode: str) -> bytes:
    artifact_id, size, expected = ORIGINALS[mode]
    require(len(data) == size and sha(data) == expected, f'Original {artifact_id} mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(z.testzip() is None, 'Bad original CRC')
        summary = json.loads(z.read('wheel-evidence/summary.json'))
        calls = json.loads(z.read('wheel-evidence/calls.json'))
        require(summary['status'] == 'verified-installed-wheel' and summary['calls'] == calls, 'Incomplete run')
        require(calls['status'] == 'passed' and not calls['network_attempts'], 'Unexpected original call status')
        require([c['label'] for c in calls['cases']] ==
                ['matching', 'mismatch', 'ambiguous', 'valid_after_error', 'error_preserved'], 'Wrong original cases')
        for c in calls['cases']:
            r = c['response']
            require(json.loads(r['content'][0]['text']) == r['structuredContent'], 'Original response mismatch')
            require(r.get('isError', False) == (c['label'] in ('ambiguous', 'error_preserved')), 'Error flag mismatch')
        return z.read('wheel-dist/' + WHEEL)


def inspect_wheel(data: bytes) -> None:
    require(len(data) == 32918 and sha(data) == WHEEL_SHA, 'Wrong wheel')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(z.testzip() is None and len(z.namelist()) == len(set(z.namelist())) == 16, 'Wheel structure mismatch')
        record = next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
        rows = list(csv.reader(io.StringIO(z.read(record).decode())))
        require({r[0] for r in rows} == set(z.namelist()), 'Incomplete wheel RECORD')
        for name, h, size in rows:
            if name == record:
                require(h == size == '', 'Invalid RECORD self-entry')
            else:
                b = z.read(name)
                actual = base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b'=').decode()
                require(h == 'sha256=' + actual and int(size) == len(b), 'Wheel RECORD mismatch')
        bundle = json.loads(z.read('second_paddle_evidence/bundle.json'))
        require(len(bundle['sha256']) == 8, 'Wrong bundled-source count')
        for name, expected in bundle['sha256'].items():
            require(sha(z.read('second_paddle_evidence/_bundle/' + name)) == expected, 'Bundled source mismatch')


def prepare(out: Path, originals: Path | None) -> None:
    out.mkdir(parents=True, exist_ok=False)
    wheels = []
    for mode, (artifact, _, _) in ORIGINALS.items():
        data = ((originals / f'evidence_wheel_{mode}_34710660702.zip').read_bytes()
                if originals else gh('api', f'repos/{REPO}/actions/artifacts/{artifact}/zip'))
        wheels.append(inspect_original(data, mode))
        (out / f'ORIGINAL-{mode}.zip').write_bytes(data)
    require(wheels[0] == wheels[1], 'Platform wheels differ')
    inspect_wheel(wheels[0])
    (out / WHEEL).write_bytes(wheels[0])
    provenance = {
        'distribution': 'second-paddle-evidence', 'version': '0.1.0a1',
        'release_tag': TAG, 'source_commit': TARGET,
        'tested_executable_commit': 'f2a1fc8346558ab2c3576808aff987a8c67cc4ae',
        'original_run': 34710660702, 'wheel': {'name': WHEEL, 'bytes': 32918, 'sha256': WHEEL_SHA},
        'original_artifacts': {k: {'id': v[0], 'bytes': v[1], 'sha256': v[2]} for k, v in ORIGINALS.items()},
        'operation': 'copy exact wheel and original artifact ZIP bytes, without rebuilding',
        'scope': 'Original Windows/Linux install observations with five synthetic calls each. Distribution verification is not a new model experiment or independent certification.',
    }
    (out / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    sums = ''.join(f'{sha((out/name).read_bytes())}  {name}\n' for name in NAMES if name != 'SHA256SUMS')
    (out / 'SHA256SUMS').write_text(sums, encoding='utf-8')
    validate(out)
    print('Prepared exact tested wheel and two original evidence archives.')


def validate(out: Path) -> dict[str, str]:
    require({p.name for p in out.iterdir()} == set(NAMES), 'Unexpected release asset set')
    data = (out / WHEEL).read_bytes()
    inspect_wheel(data)
    for mode in ORIGINALS:
        require(inspect_original((out / f'ORIGINAL-{mode}.zip').read_bytes(), mode) == data, 'Evidence-wheel mismatch')
    p = json.loads((out / 'PROVENANCE.json').read_text())
    require(p['source_commit'] == TARGET and p['wheel']['sha256'] == WHEEL_SHA and p['original_run'] == 34710660702, 'Provenance mismatch')
    expected = ''.join(f'{sha((out/name).read_bytes())}  {name}\n' for name in NAMES if name != 'SHA256SUMS')
    require((out / 'SHA256SUMS').read_text() == expected, 'Checksum-file mismatch')
    return {name: sha((out/name).read_bytes()) for name in NAMES}


def publish(out: Path, notes: Path) -> None:
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'Wrong repository')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Publication requires main')
    hashes = validate(out)
    pages = json.loads(gh('api', '--paginate', '--slurp', f'repos/{REPO}/releases?per_page=100'))
    existing = [r for page in pages for r in page if r['tag_name'] == TAG]
    require(len(existing) <= 1, 'Ambiguous release')
    if existing:
        release = existing[0]
        require(not release['draft'], 'Existing draft requires explicit reconciliation; nothing overwritten')
    else:
        gh('release', 'create', TAG, '--repo', REPO, '--target', TARGET, '--draft', '--prerelease',
           '--latest=false', '--title', 'Evidence Tools 0.1.0a1: installable preview', '--notes-file', str(notes))
        gh('release', 'upload', TAG, *[str(out / n) for n in NAMES], '--repo', REPO)
        draft = json.loads(gh('api', f'repos/{REPO}/releases/tags/{TAG}'))
        require({a['name']: a.get('digest') for a in draft['assets']} ==
                {n: 'sha256:' + h for n, h in hashes.items()}, 'Draft asset digest mismatch; left unpublished')
        gh('release', 'edit', TAG, '--repo', REPO, '--draft=false', '--prerelease', '--latest=false')
        release = json.loads(gh('api', f'repos/{REPO}/releases/tags/{TAG}'))
    require(not release['draft'] and release['prerelease'] and release['target_commitish'] == TARGET, 'Release state mismatch')
    require({a['name']: a.get('digest') for a in release['assets']} ==
            {n: 'sha256:' + h for n, h in hashes.items()}, 'Public metadata mismatch')
    print(release['html_url'])


def public_readback(out: Path) -> None:
    # urllib adds no token/cookie/authentication, even when the runner has a GH token.
    out.mkdir(parents=True, exist_ok=False)
    url = f'https://api.github.com/repos/{REPO}/releases/tags/{TAG}'
    with urlopen(url, timeout=30) as r:
        require(r.status == 200, 'Public release unavailable')
        release = json.load(r)
    require(not release['draft'] and release['prerelease'] and release['target_commitish'] == TARGET, 'Unexpected public release')
    require({a['name'] for a in release['assets']} == set(NAMES), 'Unexpected public asset set')
    requests = []
    for asset in release['assets']:
        with urlopen(asset['browser_download_url'], timeout=40) as r:
            data = r.read(200000)
            require(r.status == 200, 'Public download failed')
        require(len(data) == asset['size'] and asset['digest'] == 'sha256:' + sha(data), 'Public download identity mismatch')
        (out / asset['name']).write_bytes(data)
        requests.append({'asset': asset['name'], 'status': 200, 'bytes': len(data), 'sha256': sha(data)})
    validate(out)
    report = {'status': 'public_assets_verified', 'authenticated': False, 'release': release['html_url'],
              'release_id': release['id'], 'tag': TAG, 'assets': requests,
              'scope': 'Five actual unauthenticated asset downloads; no uptime or adoption claim.'}
    (out.parent / 'public-readback.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'validate', 'publish', 'public-readback'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--originals', type=Path)
    parser.add_argument('--notes', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare': prepare(args.out, args.originals)
    elif args.mode == 'validate': print(json.dumps(validate(args.out)))
    elif args.mode == 'publish':
        if args.notes is None: parser.error('--notes required for publish')
        publish(args.out, args.notes)
    else: public_readback(args.out)
