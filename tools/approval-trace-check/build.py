#!/usr/bin/env python3
"""Build/check one self-contained HTML file. No network or dependencies."""
from pathlib import Path
import argparse
import base64
import hashlib
import json

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
engine = (root/'audit.js').read_text(encoding='utf-8')
examples = json.dumps(json.loads((root/'examples.json').read_text(encoding='utf-8')), ensure_ascii=True)
app = (root/'app.template.js').read_text(encoding='utf-8').replace('@@EXAMPLES@@', examples)
if '</script' in (engine+app).lower():
    raise SystemExit('Embedded script must not contain an HTML script closing sequence')
result = (root/'page.template.html').read_text(encoding='utf-8')
for label, data in [('ENGINE',engine), ('APP',app)]:
    digest = base64.b64encode(hashlib.sha256(data.encode('utf-8')).digest()).decode()
    result = result.replace('@@'+label+'@@',data).replace('@@'+label+'_HASH@@',digest)
if '@@' in result:
    raise SystemExit('Unresolved template field')
output = root/'index.html'
if args.check:
    if not output.exists() or output.read_bytes() != result.encode('utf-8'):
        raise SystemExit('index.html differs from the source build')
    print('Self-contained HTML matches sources and script hashes.')
else:
    output.write_bytes(result.encode('utf-8'))
    print('Wrote', output.name, len(result.encode('utf-8')), 'bytes')
