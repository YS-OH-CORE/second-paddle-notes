"""GitHub Actions adapter for the exact published Process Receipt 0.2.0a2.

Trusted commands only. No shell expansion, credential lookup, retry or package
installation. A verified pure-Python wheel is imported from a temporary folder.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import secrets
import sys
import tempfile
import urllib.request
import zipfile

WHEEL = 'second_paddle_process_receipt-0.2.0a2-py3-none-any.whl'
WHEEL_SHA = '69c96c6d1be62b4031e6e0f7d5ebf874bf551f15433f75b296c685b9ce2c907d'
WHEEL_URL = ('https://github.com/YS-OH-CORE/second-paddle-notes/releases/download/'
             'process-receipt-v0.2.0a2/' + WHEEL)
EXECUTION_KEYS = ('status', 'task_started', 'direct_child_exit_observed',
                  'child_exit_code', 'stop_reason')
FILE_COMMANDS = ('GITHUB_OUTPUT', 'GITHUB_ENV', 'GITHUB_PATH', 'GITHUB_STEP_SUMMARY')


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def parse_inputs(env: dict) -> tuple[list[str], dict]:
    raw = env.get('PR_COMMAND_JSON', '')
    require(len(raw) <= 65536, 'Command input exceeds 64 KiB characters')
    command = json.loads(raw)
    require(isinstance(command, list) and 0 < len(command) <= 512
            and all(isinstance(a, str) and '\0' not in a for a in command)
            and bool(command[0]), 'command-json must be a nonempty argument array')
    options = {}
    for field, key, default in (('timeout', 'PR_TIMEOUT', '60'), ('grace', 'PR_GRACE', '1')):
        value = float(env.get(key, default))
        require(math.isfinite(value) and value > 0, 'Limits must be finite and positive')
        options[field] = value
    for key in ('PR_RECEIPT_PATH', 'PR_STOP_FILE'):
        value = env.get(key, '')
        require(not any(c in value for c in ('\0', '\r', '\n')), 'Control character in path')
    return command, options


def load_runtime(folder: Path):
    # A fixed public GET, not ambient gh authentication or a user-supplied URL.
    request = urllib.request.Request(WHEEL_URL, headers={'User-Agent': 'second-paddle-receipt-action/0.1'})
    with urllib.request.urlopen(request, timeout=30) as response:
        require(response.status == 200 and response.url.startswith('https://'), 'Unexpected response')
        raw = response.read(13001)
    return load_verified_wheel(raw, folder)


def load_verified_wheel(raw: bytes, folder: Path):
    require(len(raw) == 13000 and hashlib.sha256(raw).hexdigest() == WHEEL_SHA,
            'Published wheel identity mismatch')
    path = folder / WHEEL
    with path.open('xb') as output:
        output.write(raw)
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, 'Wheel CRC failed')
    names = ('process_receipt', 'process_receipt_windows')
    require(not any(n in sys.modules for n in names), 'Runtime already imported; refuse ambiguous source')
    sys.path.insert(0, str(path))
    core = importlib.import_module('process_receipt')
    windows = importlib.import_module('process_receipt_windows')
    require(all(str(path) in mod.__file__ for mod in (core, windows)), 'Runtime import is not pinned wheel')
    return core, windows


def unknown_execution() -> dict:
    return dict(status='unknown', task_started=None, direct_child_exit_observed=None,
                child_exit_code=None, stop_reason=None)


def execute(core, windows, command: list[str], receipt: Path, stop: Path | None,
            options: dict) -> dict:
    """Map the API, never child stdout or a stale receipt, into action outputs."""
    # Validate paths before invoking the runtime. Runtime exclusive open still
    # handles a competing creator. No old receipt is ever read as this run's result.
    try:
        require(not os.path.lexists(receipt), 'Receipt already exists')
        require(receipt.parent.is_dir(), 'Receipt parent does not exist')
        if stop is not None:
            require(os.path.normcase(str(stop.resolve())) != os.path.normcase(str(receipt.resolve())),
                    'Receipt and stop paths must differ')
    except (OSError, ValueError) as exc:
        return dict(action_status='rejected', receipt_state='not_created',
                    execution={**unknown_execution(), 'status': 'not_started', 'task_started': False,
                               'direct_child_exit_observed': False}, error_type=type(exc).__name__)
    try:
        run = windows.run_windows_with_receipt if os.name == 'nt' else core.run_with_receipt
        record = run(command, receipt, stop_file=stop, **options)
        require(record.get('finished_at') is not None, 'No final runtime observation')
        return dict(action_status='completed' if record['status'] == 'completed' else 'failed',
                    receipt_state='finalized', execution={k: record[k] for k in EXECUTION_KEYS})
    except core.ReceiptPersistenceError as exc:
        return dict(action_status='receipt_persistence_failed', receipt_state='unconfirmed',
                    execution=exc.summary['execution'], receipt_errors=exc.summary['receipt_errors'])
    except Exception as exc:
        # An exception after invoking the runtime cannot certify non-execution.
        return dict(action_status='adapter_error', receipt_state='unconfirmed',
                    execution=unknown_execution(), error_type=type(exc).__name__)


def outputs(result: dict) -> dict[str, str]:
    def scalar(value):
        if value is None:
            return 'unknown'
        if isinstance(value, bool):
            return 'true' if value else 'false'
        return str(value)
    ex = result['execution']
    return {'action-status': result['action_status'], 'execution-status': ex['status'],
            'task-started': scalar(ex['task_started']),
            'exit-observed': scalar(ex['direct_child_exit_observed']),
            'child-exit-code': scalar(ex['child_exit_code']), 'receipt-state': result['receipt_state'],
            'receipt-path': result['receipt_path'], 'summary-path': result['summary_path']}


def main() -> int:
    root = os.environ.get('RUNNER_TEMP')
    output_file = os.environ.get('GITHUB_OUTPUT')
    require(root and output_file, 'This entry point requires a GitHub Actions runner')
    folder = Path(tempfile.mkdtemp(prefix='process-receipt-action-', dir=root)).resolve()
    require('\n' not in str(folder) and '\r' not in str(folder), 'Invalid runner path')
    summary_path = folder/'action-summary.json'
    receipt = folder/'receipt.json'
    result = dict(action_status='rejected', receipt_state='not_created',
                  execution={**unknown_execution(), 'status': 'not_started', 'task_started': False,
                             'direct_child_exit_observed': False})
    try:
        require(os.name in ('posix', 'nt') and sys.version_info >= (3, 10), 'Unsupported Python/platform')
        command, options = parse_inputs(os.environ)
        receipt = Path(os.environ['PR_RECEIPT_PATH']).absolute() if os.environ.get('PR_RECEIPT_PATH') else receipt
        stop = Path(os.environ['PR_STOP_FILE']).absolute() if os.environ.get('PR_STOP_FILE') else None
        core, windows = load_runtime(folder)
        # Keep child log text from being interpreted as workflow commands. This
        # is accidental-spoofing protection, NOT hostile-code isolation.
        token = secrets.token_hex(24)
        print('::stop-commands::'+token, flush=True)
        saved = {k: os.environ.pop(k) for k in FILE_COMMANDS if k in os.environ}
        try:
            result = execute(core, windows, command, receipt, stop, options)
        finally:
            os.environ.update(saved)
            print('::'+token+'::', flush=True)
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    result.update(schema='process-receipt-action-v1', wheel_sha256=WHEEL_SHA,
                  receipt_path=str(receipt), summary_path=str(summary_path),
                  retry_warning='No automatic retry. Missing outputs do not establish non-execution.')
    # Output transport can fail independently too. Neither channel is a durable
    # transaction or evidence that an already-started child never acted.
    delivered = True
    try:
        with summary_path.open('x', encoding='utf-8', newline='\n') as file:
            json.dump(result, file, ensure_ascii=True, indent=2)
            file.write('\n')
    except OSError:
        delivered = False
    try:
        values = outputs(result)
        require(all('\r' not in v and '\n' not in v for v in values.values()), 'Unsafe output field')
        with open(output_file, 'a', encoding='utf-8', newline='\n') as file:
            file.write(''.join(k+'='+v+'\n' for k, v in values.items()))
    except (OSError, ValueError):
        delivered = False
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if delivered and result['action_status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
