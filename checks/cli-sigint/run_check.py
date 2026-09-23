"""Bounded, text-mode CLI SIGINT comparison using Halldrix's published mock.

Run in a disposable Linux checkout after installing its frozen environment:
  python run_check.py --worktree /checkout --python /checkout/.venv/bin/python
No real model, credentials, user files, persistent process or automatic patching
of an installed application. The candidate exists only in the supplied checkout.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

TARGET = 'e99497e5101358b496ca860a3e42c1b623375287'
MOCK_URL = 'https://gist.githubusercontent.com/Halldrix/1eaaef203821dae5c8abfb94c24a2ccd/raw/de7803c3197ab090785d2fdc7d7616f6ec12f5be/e2e_sigint_sanitized.py'
MOCK_SHA = '0c24f281e5702b7f6b8dca1530b50175426d5df2e95bbae54eb18ffae25387be'
NOTICE = 'Turn interrupted by user.'


def digest(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--python', type=Path, required=True)
    args = ap.parse_args()
    repo, interpreter = args.worktree.resolve(), args.python.resolve()
    root = Path(tempfile.mkdtemp(prefix='zero-cli-e2e-'))
    report = {'target': TARGET, 'scope': 'real quiet text-mode CLI with a local mock; not live model/tool/TUI/Windows',
              'mock_author': 'Halldrix', 'mock_url': MOCK_URL,
              'runner_author': 'Zero (ChatGPT), for Youngseok Oh / YS-OH-CORE',
              'runs': [], 'checks': [], 'source_restored': False}
    source = repo / 'hermes_cli/cli_single_query.py'
    before = None

    def check(name, good):
        report['checks'].append({'name': name, 'passed': bool(good)})
        if not good:
            raise AssertionError(name)

    try:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        check('head_pin', head == TARGET)
        check('checkout_clean', not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip())
        with urllib.request.urlopen(MOCK_URL, timeout=20) as response:
            raw = response.read(20001)
        check('mock_hash_pin', digest(raw) == MOCK_SHA)
        report['mock_sha256'] = digest(raw)
        ast.parse(raw)
        mock_path = root / 'halldrix_mock.py'
        mock_path.write_bytes(raw)
        spec = importlib.util.spec_from_file_location('halldrix_mock', mock_path)
        mock = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mock)
        guard = root / 'guard'
        guard.mkdir()
        (guard / 'sitecustomize.py').write_text('''import socket
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
def _check(address):
    if isinstance(address, tuple) and str(address[0]) not in {'127.0.0.1','::1','localhost'}:
        raise OSError('ZERO_FIXTURE: non-loopback network denied')
def _connect(self, address):
    _check(address)
    return _real_connect(self, address)
def _connect_ex(self, address):
    _check(address)
    return _real_connect_ex(self, address)
socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
''', encoding='utf-8')

        def run(label, interrupt):
            out = root / label
            home = out / 'home'
            (home / 'logs').mkdir(parents=True)
            marker = out / 'sentinel.arrived'
            srv, port, state = mock.make_mock(15.0 if interrupt else 0.0, marker, mode='text')
            (home / 'config.yaml').write_text(f'''model:
  default: "mock/mock"
  provider: "custom"
  base_url: "http://127.0.0.1:{port}/v1"
  api_key: "sk-mock-e2e"
  streaming: false
display:
  streaming: false
''', encoding='utf-8')
            env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'HERMES_HOME': str(home),
                   'PYTHONPATH': str(guard) + os.pathsep + str(repo),
                   'HERMES_ACCEPT_HOOKS': '1', 'PYTHONUNBUFFERED': '1',
                   'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8', 'TZ': 'UTC'}
            command = [str(interpreter), '-B', '-m', 'hermes_cli.main', 'chat', '-Q', '-q', mock.SENTINEL]
            sent, p = False, None
            start = time.monotonic()
            try:
                with (out / 'stdout.txt').open('wb') as stdout, (out / 'stderr.txt').open('wb') as stderr:
                    p = subprocess.Popen(command, cwd=repo, env=env, stdin=subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, start_new_session=True)
                    deadline = start + 30
                    while p.poll() is None and time.monotonic() < deadline:
                        if interrupt and marker.exists():
                            time.sleep(0.3)
                            if p.poll() is None:
                                p.send_signal(signal.SIGINT)
                                sent = True
                            break
                        time.sleep(0.05)
                    try:
                        code = p.wait(timeout=35)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait(timeout=5)
                        raise RuntimeError('bounded CLI run timed out: ' + label)
                stdout = (out / 'stdout.txt').read_text(errors='replace')
                stderr = (out / 'stderr.txt').read_text(errors='replace')
                log = home / 'logs/agent.log'
                lines = [s for s in log.read_text(errors='replace').splitlines() if 'Turn ended' in s] if log.exists() else []
                row = {'label': label, 'returncode': code, 'sentinel_seen': bool(state['sentinel_seen']),
                       'sigint_sent': sent, 'stdout': stdout, 'stderr_tail': stderr[-1400:],
                       'notice_count_stderr': stderr.count(NOTICE), 'notice_in_stdout': NOTICE in stdout,
                       'turn_ended_lines': len(lines), 'seconds': round(time.monotonic()-start, 2),
                       'stdout_sha256': digest(stdout.encode()), 'stderr_sha256': digest(stderr.encode())}
                report['runs'].append(row)
                print('CASE ' + json.dumps(row), flush=True)
                check(label + ':request_reached_mock', state['sentinel_seen'])
                check(label + ':intended_signal_sent', sent == interrupt)
                return row
            finally:
                if p is not None and p.poll() is None:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(timeout=5)
                srv.shutdown()
                srv.server_close()

        original_control = run('original_control', False)
        original_interrupt = run('original_sigint', True)
        check('baseline_control', original_control['returncode'] == 0 and 'MOCK_REPLY_OK' in original_control['stdout'] and original_control['turn_ended_lines'] > 0)
        check('original_reproduces_silence', original_interrupt['returncode'] == 130 and not original_interrupt['stdout'].strip() and original_interrupt['notice_count_stderr'] == 0 and original_interrupt['turn_ended_lines'] == 0)
        before = source.read_bytes()
        text = before.decode('utf-8')
        needle = '            print(f"\\nsession_id: {cli.session_id}", file=sys.stderr)\n            exit_single_query(130)'
        check('one_exception_exit_site', text.count(needle) == 1)
        replacement = '            if emitter is None:\n                print("Turn interrupted by user.", file=sys.stderr, flush=True)\n' + needle
        candidate = text.replace(needle, replacement)
        ast.parse(candidate)
        source.write_bytes(candidate.encode('utf-8'))
        report['original_source_sha256'] = digest(before)
        report['candidate_source_sha256'] = digest(source.read_bytes())
        report['candidate_diff'] = subprocess.check_output(['git','diff','--','hermes_cli/cli_single_query.py'], cwd=repo, text=True)
        fixed_control = run('candidate_control', False)
        fixed_interrupt = run('candidate_sigint', True)
        check('normal_stdout_unchanged', fixed_control['returncode'] == 0 and fixed_control['stdout'] == original_control['stdout'] and fixed_control['notice_count_stderr'] == 0)
        check('interruption_diagnostic_once_stderr_only', fixed_interrupt['returncode'] == 130 and not fixed_interrupt['stdout'].strip() and fixed_interrupt['notice_count_stderr'] == 1 and not fixed_interrupt['notice_in_stdout'])
        check('not_claiming_worker_finalization', fixed_interrupt['turn_ended_lines'] == 0)
        report['success'] = True
    except Exception as exc:
        report['success'] = False
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if before is not None:
            source.write_bytes(before)
            report['source_restored'] = source.read_bytes() == before
        print('ZERO_CLI_E2E_RESULT ' + json.dumps(report, ensure_ascii=False), flush=True)
        (root / 'result.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0 if report.get('success') and report['source_restored'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
