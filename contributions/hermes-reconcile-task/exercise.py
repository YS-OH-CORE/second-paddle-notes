"""Check the published reader plus explicit read-only outcome controls via Hermes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import run as bridge


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--skill', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    base = {'version': 1, 'repository': 'YS-OH-CORE/second-paddle-notes',
            'ref': '1f2b59be45c29ac70ebf3e8b5b0879708c93bbb1',
            'path': 'skills/github-write-reconcile/scripts/reconcile.py',
            'expected_sha256': bridge.READER_SHA}
    inputs = [('published_reader', base, 'content_match'),
              ('wrong_digest', dict(base, expected_sha256='0' * 64), 'content_conflict'),
              ('absent_path', dict(base, path='skills/github-write-reconcile/scripts/not-delivered-control.py'), 'absent_at_snapshot'),
              ('invalid_intent', dict(base, version=True), 'unknown')]
    report = {'status': 'incomplete', 'cases': [], 'scope': 'One real published-file check plus three controlled read-only inputs through Hermes; no LLM or remote write'}
    try:
        for name, intent, expected in inputs:
            intent_path = a.out / (name + '-intent.json')
            bridge.save(intent_path, intent)
            out = a.out / name
            proc = subprocess.run([sys.executable, '-B', str(Path(bridge.__file__).resolve()),
                '--upstream', str(a.upstream.resolve()), '--skill', str(a.skill.resolve()),
                '--intent', str(intent_path.resolve()), '--out', str(out.resolve())],
                capture_output=True, text=True, timeout=95)
            (a.out / (name + '.log')).write_text(proc.stdout + proc.stderr)
            bridge.need(proc.returncode == bridge.EXIT[expected], 'BRIDGE_EXIT_' + name)
            result = json.loads((out / 'result.json').read_text())
            bridge.need(result['result']['status'] == expected, 'OUTCOME_' + name)
            bridge.need(result['result']['retry_authorized'] is False, 'RETRY_PERMISSION')
            bridge.need(result['host_calls'] == 4, 'CALL_COUNT')
            report['cases'].append({'case': name, 'exit_code': proc.returncode, 'result': result})
        bridge.need(len({c['result']['host_pid'] for c in report['cases']}) == 4, 'HOST_PID_REUSED')
        report.update(status='verified', get_requests=sum(c['result']['result'].get('get_requests', 0) for c in report['cases']),
                      registry_calls=16, terminal_calls=4, bridge_sha256=hashlib.sha256(Path(bridge.__file__).read_bytes()).hexdigest())
    finally:
        bridge.save(a.out / 'summary.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
