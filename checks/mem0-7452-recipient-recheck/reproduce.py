"""Reproduce the bounded review in a new directory, with no third-party packages."""
import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
out = a.out.resolve()
out.mkdir(parents=True, exist_ok=False)
source = 'https://raw.githubusercontent.com/Sai-Sreenath-1819/mem0/'
new = '2bdfb63e5c0b594bcd339b9222f971d416b681fa'
old = 'af93b81bc9573be1b78014b5005a0b0d950605bb'
checksums = {'mem0/memory/storage.py': '0ab9586af1c1d30c9c5fd4668154e146ca1c293fbc98d85ab5e44c389b1d2b2e', 'mem0/memory/main.py': 'e631d57bb9d1a70102e9b0050eac5d535851dccc68b28016962b77ee1a6b200f'}
for path, expected in checksums.items():
    data = urlopen(source + new + '/' + path, timeout=25).read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError('Source identity mismatch: ' + path)
    dest = out / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
old_main = urlopen(source + old + '/mem0/memory/main.py', timeout=25).read()
def selected(text):
    return {n.name: ast.get_source_segment(text, n) for n in ast.parse(text).body
            if isinstance(n, ast.FunctionDef) and n.name in {'_build_session_scope', '_escape_scope_value'}}
assert selected(old_main.decode()) == selected((out / 'mem0/memory/main.py').read_text(encoding='utf-8'))
shutil.copyfile(Path(__file__).with_name('review.py'), out / 'review.py')
started = datetime.now(timezone.utc).isoformat()
proc = subprocess.run([sys.executable, str(out / 'review.py')], capture_output=True, text=True)
(out / 'stdout.txt').write_text(proc.stdout, encoding='utf-8')
(out / 'stderr.txt').write_text(proc.stderr, encoding='utf-8')
record = {'started_at_utc': started, 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
          'exit_code': proc.returncode, 'serializers_identical_to_baseline': True,
          'baseline_main_sha256': hashlib.sha256(old_main).hexdigest(),
          'review_sha256': hashlib.sha256((out / 'review.py').read_bytes()).hexdigest()}
if (out / 'results.json').exists():
    results = json.loads((out / 'results.json').read_text(encoding='utf-8'))
    assert results['source_hashes']['baseline_storage.py']['sha256'] == '611f6f177cf99ef402e8ea3070e0f40720a75f7b013711e35da27c2e45f9bb5d'
(out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(proc.stdout)
print(json.dumps(record))
raise SystemExit(proc.returncode)
