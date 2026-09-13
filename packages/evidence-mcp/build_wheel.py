"""Build a reproducible, data-only wheel from eight pinned public source files.

No build dependency, remote fetch, source rewrite, or credential is needed.
Uses the PyPA wheel/entry-point specification; pip acceptance is checked separately.
"""
from __future__ import annotations
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

NAME = 'second_paddle_evidence'
VERSION = '0.1.0a2'
FILENAME = f'{NAME}-{VERSION}-py3-none-any.whl'


def build(out: Path) -> Path:
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    pins = json.loads((here/'pins.json').read_text(encoding='utf-8'))
    files: dict[str, bytes] = {}
    digests = {}
    for path, expected in pins['files'].items():
        data = (root/'tools'/path).read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual != expected:
            raise RuntimeError('Pinned source differs: '+path)
        files[f'{NAME}/_bundle/{path}'] = data
        digests[path] = hashlib.sha256(data).hexdigest()
    files[f'{NAME}/bundle.json'] = (json.dumps({'source_commit': pins['source_commit'], 'sha256': digests}, sort_keys=True, indent=2)+'\n').encode()
    files[f'{NAME}/__init__.py'] = b'"""Packaged read-only MCP utilities. Nothing starts at import."""\n'
    files[f'{NAME}/__main__.py'] = (here/'launcher.py').read_bytes()
    info = f'{NAME}-{VERSION}.dist-info'
    files[f'{info}/METADATA'] = (
        'Metadata-Version: 2.4\nName: second-paddle-evidence\nVersion: '+VERSION+'\n'
        'Summary: Two opt-in read-only MCP tools, packaged with their existing implementations\n'
        'Author: Youngseok Oh\nLicense-Expression: MIT\nLicense-File: LICENSE\n'
        'Requires-Python: >=3.10\nRequires-Dist: mcp==2.2.0\n'
        'Project-URL: Source, https://github.com/YS-OH-CORE/second-paddle-notes\n'
        'Description-Content-Type: text/plain\n\n'
        'Requires separately installed Node.js 22 or newer. No provider key, scheduler, or HTTP endpoint. '
        'Bundled source is pinned to '+pins['source_commit']+'. '
        'Run second-paddle-evidence --check for local prerequisites and connection arguments. '
        'The host must explicitly configure the stdio tool. This preview is not published to PyPI.\n'
    ).encode()
    files[f'{info}/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: second-paddle-stdlib-wheel 1\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    files[f'{info}/entry_points.txt'] = b'[console_scripts]\nsecond-paddle-evidence = second_paddle_evidence.__main__:main\n'
    files[f'{info}/licenses/LICENSE'] = files[f'{NAME}/_bundle/evidence-mcp/LICENSE']
    rows = []
    for path, data in sorted(files.items()):
        value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        rows.append((path, 'sha256='+value, str(len(data))))
    rows.append((f'{info}/RECORD', '', ''))
    csv_text = io.StringIO(newline=''); csv.writer(csv_text, lineterminator='\n').writerows(rows)
    files[f'{info}/RECORD'] = csv_text.getvalue().encode()
    out.mkdir(parents=True, exist_ok=True)
    destination = out/FILENAME
    # Exclusive create avoids replacing an existing release file.
    with destination.open('xb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(files, key=lambda x: ('.dist-info/' in x, x)):
            entry = zipfile.ZipInfo(path, (1980,1,1,0,0,0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, files[path])
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    print(build(parser.parse_args().out).resolve())
