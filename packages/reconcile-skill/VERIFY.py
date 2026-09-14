"""Read-only verification of this extracted package, not a signature check."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def verify(root):
    info = json.loads((root / 'PACKAGE.json').read_text(encoding='utf-8'))
    if info.get('schema') != 1 or not isinstance(info.get('files'), dict):
        raise ValueError('MANIFEST_FORMAT')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('SYMLINK')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(info['files']) | {'PACKAGE.json'}:
        raise ValueError('FILE_SET_DIFFER')
    for name, expected in info['files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or str(path) != name:
            raise ValueError('UNSAFE_PATH')
        raw = (root / name).read_bytes()
        if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('FILE_BYTES_DIFFER:' + name)
    return {'status': 'verified', 'files_checked': len(info['files']),
            'source_commit': info['source_commit'],
            'scope': 'Local package correspondence; no network, execution, installation or signature claim'}


if __name__ == '__main__':
    try:
        result = verify(Path(__file__).resolve().parent)
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'status': 'rejected', 'reason': 'PACKAGE_DIFFER'}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
