"""Four fresh read-only CLI invocations against existing PR44 provider records."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    skill = Path(__file__).resolve().parents[1]
    wanted = [('committed-despite-failed-check', 'content_match', 0),
              ('completed-retry', 'content_match', 0),
              ('conflict-control', 'content_conflict', 2),
              ('absent-control', 'absent_at_snapshot', 3)]
    records = []
    for name, expected, code in wanted:
        process = subprocess.run([sys.executable, '-B', '-S', str(skill / 'scripts/reconcile.py'),
            '--intent', str(skill / 'examples' / (name + '.json')), '--use-github-token'],
            capture_output=True, text=True, timeout=50)
        (args.out / (name + '.json')).write_text(process.stdout, encoding='utf-8')
        observed = json.loads(process.stdout)
        if process.returncode != code or observed['status'] != expected or observed['retry_authorized'] is not False:
            raise RuntimeError('UNEXPECTED_READBACK_' + name)
        if process.stderr:
            raise RuntimeError('UNEXPECTED_STDERR_' + name)
        records.append({'case': name, 'exit_code': process.returncode, 'result': observed})
    report = {'status': 'verified', 'scope': 'New read-only CLI checks of existing provider records; zero provider writes or new loss injections',
              'cases': records, 'get_requests': sum(x['result']['get_requests'] for x in records),
              'source_sha256': hashlib.sha256((skill / 'scripts/reconcile.py').read_bytes()).hexdigest()}
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
