import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--checkout', required=True)
parser.add_argument('--label', required=True)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
root = Path(args.checkout).resolve()
out = Path(__file__).resolve().parent
env = os.environ.copy()
env.update(TZ='UTC', CI='true', GIT_NO_LAZY_FETCH='1')
files = ['src/runner/server.ts', 'src/runner/server.session-lifetime.test.ts',
         'src/runner/server.test.ts', 'package.json', 'package-lock.json']
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = {
    'label': args.label, 'cwd': str(root), 'command': args.command,
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, env=env, text=True).strip(),
    'environment_overrides': {k: env[k] for k in ('TZ', 'CI', 'GIT_NO_LAZY_FETCH')},
    'input_sha256': {f: digest(root / f) for f in files},
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
start = time.monotonic()
log = out / (args.label + '.log')
with log.open('w') as stream:
    result = subprocess.run(args.command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode, elapsed_seconds=round(time.monotonic()-start, 3),
              ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), log_sha256=digest(log))
(out / (args.label + '.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
print('\n'.join(log.read_text().splitlines()[-42:]))
raise SystemExit(result.returncode)
