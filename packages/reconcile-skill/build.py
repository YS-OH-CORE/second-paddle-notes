"""Deterministic, offline release assembly from pinned source and original ZIPs."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'source.json').read_text())
RUNTIME = 'github-write-reconcile-0.1.0a1.zip'
EVIDENCE = 'github-write-reconcile-0.1.0a1-evidence.zip'


def need(value, code):
    if not value:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def info(raw):
    return {'bytes': len(raw), 'sha256': digest(raw)}


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')


def safe(name):
    path = PurePosixPath(name)
    need(bool(name) and not path.is_absolute() and str(path) == name and '..' not in path.parts
         and '\\' not in name and ':' not in name, 'UNSAFE_MEMBER')


def pack(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, raw in sorted(files.items()):
            safe(name)
            entry = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            z.writestr(entry, raw)
    return buffer.getvalue()


def checked_source(repo):
    output = {}
    for name, pin in CONFIG['files'].items():
        safe(name)
        path = repo / name
        need(not path.is_symlink(), 'SOURCE_SYMLINK')
        raw = path.read_bytes()
        need(info(raw) == {k: pin[k] for k in ('bytes', 'sha256')}, 'SOURCE_HASH:' + name)
        need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == pin['blob'], 'SOURCE_BLOB')
        output[name] = raw
    skill = repo / 'skills/github-write-reconcile'
    actual = {p.relative_to(repo).as_posix() for p in skill.rglob('*') if p.is_file()}
    need(actual == {n for n in output if n.startswith('skills/')}, 'SKILL_FILE_SET')
    return output


def checked_archives(originals):
    files = {}
    for pin in CONFIG['artifacts']:
        raw = originals[pin['filename']]
        need(info(raw) == {k: pin[k] for k in ('bytes', 'sha256')}, 'ORIGINAL_HASH')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = z.namelist()
            need(len(names) == len(set(names)) == pin['members'], 'ORIGINAL_MEMBERS')
            for name in names:
                safe(name)
            need(sum(i.file_size for i in z.infolist()) < 4_000_000, 'EXPANSION_LIMIT')
            need(z.testzip() is None, 'ORIGINAL_CRC')
        files['originals/' + pin['filename']] = raw
    return files


def build(repo, originals):
    sources = checked_source(repo)
    runtime = {name.removeprefix('skills/'): raw for name, raw in sources.items() if name.startswith('skills/')}
    runtime['START_HERE.ko.md'] = (HERE / 'START_HERE.ko.md').read_bytes()
    runtime['VERIFY.py'] = (HERE / 'VERIFY.py').read_bytes()
    runtime['PACKAGE.json'] = encode({'schema': 1, 'source_commit': CONFIG['source_commit'],
        'version': CONFIG['version'], 'files': {n: info(b) for n, b in sorted(runtime.items())}})
    evidence = checked_archives(originals)
    evidence.update({'source/' + name: raw for name, raw in sources.items()})
    evidence['PROVENANCE.json'] = encode(CONFIG)
    assets = {RUNTIME: pack(runtime), EVIDENCE: pack(evidence), 'PROVENANCE.json': encode(CONFIG)}
    assets['SHA256SUMS'] = ''.join(digest(raw) + '  ' + name + '\n' for name, raw in sorted(assets.items())).encode()
    return assets


def verify_extracted(runtime_bytes):
    """The new distribution must work without a repository checkout or Hermes."""
    with tempfile.TemporaryDirectory(prefix='reconcile-package-') as temp:
        root = Path(temp)
        with zipfile.ZipFile(io.BytesIO(runtime_bytes)) as z:
            for entry in z.infolist():
                safe(entry.filename)
                target = root / entry.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(entry))
        check = subprocess.run([sys.executable, '-B', '-S', str(root / 'VERIFY.py')],
                               cwd=root, capture_output=True, text=True, timeout=15)
        need(check.returncode == 0 and json.loads(check.stdout)['status'] == 'verified', 'PACKAGE_VERIFY')
        tests = subprocess.run([sys.executable, '-B', '-S', '-m', 'unittest', 'discover',
                                '-s', 'github-write-reconcile/tests', '-p', 'test_*.py', '-v'],
                               cwd=root, capture_output=True, text=True, timeout=20)
        need(tests.returncode == 0 and 'Ran 26 tests' in tests.stderr, 'EXTRACTED_TESTS')
        help_run = subprocess.run([sys.executable, '-B', '-S', 'github-write-reconcile/scripts/reconcile.py', '--help'],
                                  cwd=root, capture_output=True, text=True, timeout=10)
        need(help_run.returncode == 0 and '--intent' in help_run.stdout, 'EXTRACTED_COMMAND')
        # A missing support file must fail package verification, not pass on SKILL.md alone.
        reader = root / 'github-write-reconcile/scripts/reconcile.py'
        reader.rename(reader.with_suffix('.missing-control'))
        bad = subprocess.run([sys.executable, '-B', '-S', str(root / 'VERIFY.py')],
                             cwd=root, capture_output=True, text=True, timeout=10)
        need(bad.returncode == 1, 'MISSING_SCRIPT_NOT_REJECTED')
        return {'package': json.loads(check.stdout), 'unit_tests': 26, 'unit_log': tests.stderr,
                'help_exit': help_run.returncode, 'missing_script_exit': bad.returncode}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--originals', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    originals = {r['filename']: (a.originals / r['filename']).read_bytes() for r in CONFIG['artifacts']}
    assets = build(a.repo, originals)
    need(assets == build(a.repo, originals), 'NONDETERMINISTIC_BUILD')
    checked = verify_extracted(assets[RUNTIME])
    for name, raw in assets.items():
        (a.out / name).write_bytes(raw)
    (a.out / 'local-check.json').write_bytes(encode({'status': 'verified', 'assets': {n: info(b) for n,b in assets.items()}, 'checks': checked}))
    print(json.dumps({'status': 'verified', 'assets': {n: info(b) for n,b in assets.items()}}, indent=2))
