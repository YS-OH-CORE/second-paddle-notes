"""Build from pinned original bytes; optionally repair only this PR's known bad copy."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
import verify as v

REPO = 'YS-OH-CORE/second-paddle-notes'
BRANCH = 'zero/retain-stdio-evidence-20260914'
TARGET = 'contributions/stdio-evidence-capsule/records.capsule.json'
KNOWN_BAD_BLOB = '146aa2503dbfd837278caf956ad86f8ee8ab2225'
CORRECT_BLOB = '1b11c7cd2faced0bc11a1355074de23a04bd05e2'
ORIGINALS = {
    'successful': (10327972446, 34791675942, 'stdio-restart-verified-10327972446.zip',
                   'cd9aec329504cd5168ba9793382e137877263d64cf17e171fe786d6b014a2151'),
    'first_failed': (10327682835, 34791471652, 'stdio-restart-first-run-10327682835.zip',
                     '03afcabf31c2cf9051f13778dd0e712014a5a3309971623c754d02c327328107'),
}
SOURCE_PATHS = ('.github/workflows/stdio-round-restart.yml',
                'contributions/preserved-mcp-rounds/requirements.txt',
                'contributions/preserved-mcp-rounds/round_graph.py',
                'contributions/stdio-round-restart/stdio_restart_probe.py',
                'contributions/stdio-round-restart/test_store.py')
NOTICE = ('Lossless UTF-8 member bytes from the successful and first failed PR35 ZIPs. '
          'Source files are referenced by content hashes; no embedded code is executed. '
          'This is not a byte-identical reconstruction of the ZIP container.')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def bounded_read(response, limit=500_000):
    raw = response.read(limit + 1)
    v.need(len(raw) <= limit, 'HTTP_BODY_LIMIT')
    return raw


def api(path, token, data=None):
    url = 'https://api.github.com/repos/' + REPO + '/' + path
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'second-paddle-retention'}
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method='PUT' if body is not None else 'GET')
    with urllib.request.build_opener(NoRedirect).open(request, timeout=25) as response:
        return bounded_read(response)


def download_original(artifact_id, token):
    # Never forward the API bearer token to the signed storage redirect.
    try:
        return api(f'actions/artifacts/{artifact_id}/zip', token)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise
        location = exc.headers['Location']
    parsed = urllib.parse.urlsplit(location)
    v.need(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
           'ARTIFACT_REDIRECT')
    with urllib.request.urlopen(location, timeout=25) as response:
        return bounded_read(response, v.MAX_INPUT)


def build(repo, originals):
    archives = {}
    for label, (artifact_id, run_id, filename, sha) in ORIGINALS.items():
        raw = originals[label]
        v.need(v.digest(raw) == sha, 'ORIGINAL_ARCHIVE_IDENTITY')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            v.need(len(names) == len(set(names)), 'DUPLICATE_ZIP_MEMBER')
            v.need(sum(x.file_size for x in archive.infolist()) < v.MAX_EXPANDED, 'ZIP_EXPANSION_LIMIT')
            v.need(archive.testzip() is None, 'ZIP_CRC')
            members = {}
            for name in sorted(names):
                v.safe_name(name)
                value = archive.read(name)
                text = value.decode('utf-8')
                v.need(text.encode('utf-8') == value, 'UTF8_ROUNDTRIP')
                members[name] = text
        archives[label] = {'artifact_id': artifact_id, 'run_id': run_id, 'original_zip_bytes': len(raw),
                           'original_zip_sha256': sha, 'members': members,
                           'member_sha256': {name: v.digest(text.encode()) for name, text in members.items()}}
    source_files = {}
    for name in SOURCE_PATHS:
        raw = (repo / name).read_bytes()
        source_files[name] = {'bytes': len(raw), 'sha256': v.digest(raw),
                             'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}
    packet = {'schema': 1, 'source_ref': 'f795eeaad68895d4aacd1955ac137335e7898eac',
              'archives': archives, 'source_files': source_files}
    raw = v.canonical(packet).encode('utf-8')
    v.need(len(raw) == v.PAYLOAD_BYTES and v.digest(raw) == v.PAYLOAD_SHA256, 'ASSEMBLED_PACKET_PIN')
    outer = {'format': 'second-paddle-record-members/v1', 'encoding': 'zlib+base64',
             'payload_bytes': len(raw), 'payload_sha256': v.digest(raw), 'notice': NOTICE,
             'payload': base64.b64encode(zlib.compress(raw, 9)).decode('ascii')}
    result = (json.dumps(outer, indent=2) + '\n').encode('utf-8')
    blob = hashlib.sha1(b'blob ' + str(len(result)).encode() + b'\0' + result).hexdigest()
    v.need(blob == CORRECT_BLOB, 'ASSEMBLED_FILE_PIN')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-archives', type=Path)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    token = os.environ.get('GH_RETENTION_TOKEN', '')
    if args.publish:
        v.need(os.environ.get('GITHUB_REPOSITORY') == REPO and
               os.environ.get('RETENTION_HEAD_BRANCH') == BRANCH and
               os.environ.get('RETENTION_HEAD_REPO') == REPO and token and not args.local_archives,
               'PUBLICATION_CONTEXT')
    if args.local_archives:
        originals = {label: (args.local_archives / spec[2]).read_bytes() for label, spec in ORIGINALS.items()}
    else:
        v.need(bool(token), 'TOKEN_REQUIRED_FOR_ARTIFACT_READ')
        originals = {label: download_original(spec[0], token) for label, spec in ORIGINALS.items()}
    candidate = build(repo, originals)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'candidate.json'
        path.write_bytes(candidate)
        packet = v.load_capsule(path)
        result = v.verify_packet(packet, repo)
        for label, raw in originals.items():
            original = Path(temp) / (label + '.zip')
            original.write_bytes(raw)
            v.compare_original_zip(packet, original)
    if not args.publish:
        print(json.dumps({'status': 'verified_no_remote_write', 'correct_blob': CORRECT_BLOB,
                          'retained_members': result['retained_members']}))
        return
    # Replace only this disposable runner checkout before running the local tests.
    (repo / TARGET).write_bytes(candidate)
    subprocess.run([sys.executable, '-S', '-m', 'unittest', 'discover', '-s',
                    str(Path(__file__).parent), '-p', 'test_verify.py', '-v'], check=True, timeout=30)
    endpoint = 'contents/' + TARGET
    query = '?ref=' + urllib.parse.quote(BRANCH, safe='')
    current = v.strict_json(api(endpoint + query, token))
    if current['sha'] == CORRECT_BLOB:
        status = 'already_correct_no_write'
    else:
        v.need(current['sha'] == KNOWN_BAD_BLOB, 'UNREVIEWED_REMOTE_CHANGE')
        response = v.strict_json(api(endpoint, token, {
            'message': 'Repair retained evidence from verified original artifact bytes [skip ci]',
            'content': base64.b64encode(candidate).decode('ascii'), 'sha': KNOWN_BAD_BLOB, 'branch': BRANCH}))
        v.need(response['content']['sha'] == CORRECT_BLOB, 'PUBLISHED_BLOB_DIFFER')
        status = 'repaired_known_copy'
    readback = v.strict_json(api(endpoint + query, token))
    v.need(readback['sha'] == CORRECT_BLOB and base64.b64decode(readback['content']) == candidate,
           'REMOTE_READBACK_DIFFER')
    print(json.dumps({'status': status, 'correct_blob': CORRECT_BLOB,
                      'retained_members': result['retained_members'], 'source_files_checked': 5}))


if __name__ == '__main__':
    main()
