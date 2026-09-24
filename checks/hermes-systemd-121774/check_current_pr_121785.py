"""Bounded check of Hermes PR #121785 using exact source and real duration parser.
Only subprocess.run is replaced. No systemctl/service/model is invoked.
The source is AST-selected, not a full package import. Eight synthetic cases
are author-side supplemental checks, not a live systemd reproduction.
Zero, an AI assistant, for Youngseok Oh / YS-OH-CORE.
"""
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Dict, Optional

SPECS = [
    ('base', 'NousResearch/hermes-agent', 'd350422b15863fc4c0b7962b122b625a0271516c', 'c7d337d47f233b599028488c78603a32c1aa964a'),
    ('candidate', '686f6c61/hermes-agent', '2c6f77434a6a0e54bea6861901cb3adc98478936', '9944cc1b88356bdb10c9273f45c9c7795193bb42'),
]
NAMES = {'_systemd_unit_is_loaded', '_systemd_timeout_stop_us', 'parse_systemd_duration_to_us'}

def sample(load='loaded', value='3min 30s', fragment='/run/systemd/system/example.service'):
    return {'LoadState': load, 'FragmentPath': fragment, 'TimeoutStopUSec': value}

CASES = [
    ('missing_user_loaded_system', sample('not-found', '1min 30s', ''), sample(), 210000000, ['user', 'system']),
    ('both_not_found', sample('not-found', '1min 30s', ''), sample('not-found', '1min 30s', ''), None, ['user', 'system']),
    ('loaded_user_precedence', sample(value='4min'), sample(), 240000000, ['user']),
    ('genuine_short_user', sample(value='1min 30s'), sample(), 90000000, ['user']),
    ('failed_user_query', 'exit1', sample(), 210000000, ['user', 'system']),
    ('timed_out_user_query', 'timeout', sample(), 210000000, ['user', 'system']),
    ('loaded_without_fragment_fractional_duration', sample(value='1min 30.5s', fragment=''), sample(), 90500000, ['user']),
    ('invalid_user_duration', sample(value='not-a-duration'), sample(), 210000000, ['user', 'system']),
]

def extract(raw, label):
    tree = ast.parse(raw)
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in NAMES]
    expected = NAMES if label == 'candidate' else NAMES - {'_systemd_unit_is_loaded'}
    assert {n.name for n in selected} == expected
    assert all(not n.decorator_list for n in selected)
    return compile(ast.Module(body=selected, type_ignores=[]), label + '_pinned_functions', 'exec')

root = Path(tempfile.mkdtemp(prefix='zero-hermes-121785-'))
report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version.split()[0],
          'scope': 'source-selected original probe and duration parser; subprocess.run mocked; no full module or live systemd',
          'cases': [], 'sources': {}, 'new_model_calls': 0, 'service_changes': 0, 'success': False}
try:
    compiled = {}
    for label, repo, ref, expected_blob in SPECS:
        endpoint = f'repos/{repo}/contents/gateway/shutdown_forensics.py?ref={ref}'
        proc = subprocess.run(['gh', 'api', endpoint], capture_output=True, timeout=25,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if proc.returncode:
            raise RuntimeError('Public source GET failed; exit=' + str(proc.returncode))
        item = json.loads(proc.stdout)
        raw = base64.b64decode(item['content'])
        assert len(raw) < 120000
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert item['sha'] == blob == expected_blob, 'Pinned source identity mismatch'
        (root / (label + '_shutdown_forensics.py')).write_bytes(raw)
        report['sources'][label] = {'repository': repo, 'commit': ref, 'git_blob': blob, 'sha256': hashlib.sha256(raw).hexdigest()}
        compiled[label] = extract(raw, label)
    for case_id, user, system, expected, expected_calls in CASES:
        record = {'id': case_id, 'expected_us': expected, 'expected_candidate_calls': expected_calls, 'observed': {}}
        for label in ('base', 'candidate'):
            calls = []
            def fake_run(cmd, **kwargs):
                assert cmd[:1] == ['systemctl'] and 'show' in cmd
                assert kwargs.get('timeout') == 2.0
                scope = 'user' if '--user' in cmd else 'system'
                calls.append(scope)
                response = user if scope == 'user' else system
                if response == 'timeout':
                    raise subprocess.TimeoutExpired(cmd, 2.0)
                if response == 'exit1':
                    return subprocess.CompletedProcess(cmd, 1, stdout='', stderr='synthetic unavailable manager')
                requested = []
                for arg in cmd:
                    if arg.startswith('--property='):
                        requested.extend(arg.split('=', 1)[1].split(','))
                text = '\n'.join(k + '=' + response[k] for k in requested if k in response) + '\n'
                return subprocess.CompletedProcess(cmd, 0, stdout=text, stderr='')
            namespace = {'Dict': Dict, 'Optional': Optional,
                         'subprocess': SimpleNamespace(run=fake_run, TimeoutExpired=subprocess.TimeoutExpired)}
            exec(compiled[label], namespace)
            observed = namespace['_systemd_timeout_stop_us']('example.service')
            record['observed'][label] = {'microseconds': observed, 'calls': list(calls)}
            if label == 'candidate':
                assert observed == expected, (case_id, observed, expected)
                assert calls == expected_calls, (case_id, calls, expected_calls)
        report['cases'].append(record)
    differing = [r['id'] for r in report['cases'] if r['observed']['base'] != r['observed']['candidate']]
    assert differing == ['missing_user_loaded_system', 'both_not_found']
    report['changed_cases'] = differing
    report['passed_cases'] = len(report['cases'])
    report['success'] = True
except Exception as exc:
    report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:300]}
finally:
    payload = json.dumps(report, indent=2, sort_keys=True)
    (root / 'report.json').write_text(payload + '\n', encoding='utf-8')
    print('REVIEW_RESULT=' + json.dumps(report, sort_keys=True), flush=True)
    print('SCRATCH=' + str(root), flush=True)
