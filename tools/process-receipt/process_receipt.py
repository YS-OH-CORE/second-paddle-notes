#!/usr/bin/env python3
"""Run one trusted POSIX command with a stop-file and an observed-exit receipt.

Standard library only. This is process supervision, not an agent, sandbox,
credential boundary, rollback facility, or proof that a user goal was met.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Sequence


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def positive(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be finite and positive')
    return value


def stop_exists(path: Path | None) -> bool:
    # A dangling symlink still counts as a stop request; never follow or delete it.
    if path is None:
        return False
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def exit_status(code: int | None) -> str:
    if code is None:
        return 'exit_unconfirmed'
    return 'completed' if code == 0 else 'failed'


class ReceiptPersistenceError(OSError):
    """Final receipt I/O failed; the observed execution outcome is still available.

    ``summary`` contains no command arguments, environment values or exception
    text. It does not say that the receipt is absent or that effects were undone.
    """

    def __init__(self, record: dict, failures: list[dict]) -> None:
        super().__init__('Receipt finalization failed; execution may already have occurred')
        keys = ('status', 'task_started', 'direct_child_exit_observed',
                'child_exit_code', 'stop_reason')
        self.summary = {
            'status': 'receipt_persistence_failed',
            'receipt_finalization_confirmed': False,
            'execution': {key: record[key] for key in keys},
            'receipt_errors': failures,
            'retry_warning': 'Do not infer non-execution or retry automatically from a missing receipt.',
        }


def _finish_receipt(handle, save, record: dict, saved_handlers: dict) -> None:
    """Restore caller handlers even when final save or close fails."""
    failures = []
    try:
        try:
            save()
        except OSError as exc:
            failures.append({'phase': 'write_flush_sync', 'error_type': type(exc).__name__})
    finally:
        try:
            handle.close()
        except OSError as exc:
            failures.append({'phase': 'close', 'error_type': type(exc).__name__})
        finally:
            for sig, old in saved_handlers.items():
                signal.signal(sig, old)
    if failures:
        raise ReceiptPersistenceError(record, failures)


def run_with_receipt(command: Sequence[str], receipt_path: Path, *,
                     stop_file: Path | None = None, timeout: float = 60.0,
                     grace: float = 1.0, poll: float = 0.05) -> dict:
    """Execute a trusted command; reserve a NEW receipt before starting it.

    Runs in the calling process's main thread because signal handlers are used.
    Arguments, environment values and child output are not copied into receipts.
    The child inherits the caller's environment and stdout/stderr. Do not run
    untrusted commands or put sensitive output into public CI logs.
    """
    if os.name != 'posix':
        raise RuntimeError('This implementation requires POSIX (tested on Linux)')
    if isinstance(command, (str, bytes)) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError('command must be a nonempty sequence of argument strings')
    timeout, grace, poll = positive(timeout, 'timeout'), positive(grace, 'grace'), positive(poll, 'poll')
    receipt_path = Path(receipt_path)
    stop_file = Path(stop_file) if stop_file is not None else None
    if stop_file is not None and stop_file.absolute() == receipt_path.absolute():
        raise ValueError('receipt and stop file must be different paths')
    # Missing parent or existing receipt is an error, BEFORE any child can run.
    handle = receipt_path.open('x', encoding='utf-8')
    started = time.monotonic()
    flags: list[int] = []
    saved_handlers: dict = {}
    child: subprocess.Popen | None = None
    record = dict(schema='process-receipt-v1', started_at=utc(), status='not_started',
                  task_started=False, stop_reason=None, child_exit_code=None,
                  direct_child_exit_observed=False, alive_when_stop_observed=False,
                  signal_exit_after_request_observed=False, signals_requested=[],
                  timeout_seconds=timeout, grace_seconds=grace, poll_seconds=poll,
                  scope='Trusted command; direct-child exit only; no rollback or hostile-code isolation')

    def save() -> None:
        # The running file is a checkpoint. It is final only after finished_at.
        handle.seek(0)
        json.dump(record, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n'); handle.truncate(); handle.flush(); os.fsync(handle.fileno())

    def send_group(sig: int) -> None:
        if child is None:
            return
        try:
            os.killpg(child.pid, sig)
            record['signals_requested'].append(signal.Signals(sig).name)
        except ProcessLookupError:
            pass
        except OSError as exc:
            record.setdefault('signal_errors', []).append(type(exc).__name__)

    def terminate() -> None:
        if child is None:
            return
        alive = child.poll() is None
        record['alive_when_stop_observed'] = alive
        if alive:
            send_group(signal.SIGTERM)
            try:
                child.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                send_group(signal.SIGKILL)
                try:
                    child.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    pass
        code = child.poll()
        record.update(child_exit_code=code, direct_child_exit_observed=code is not None,
                      signal_exit_after_request_observed=(alive and code in (-signal.SIGTERM, -signal.SIGKILL)
                                                        and bool(record['signals_requested'])))

    try:
        save()
        for sig in (signal.SIGINT, signal.SIGTERM):
            saved_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, lambda number, frame: flags.append(number) if not flags else None)
        if flags or stop_exists(stop_file):
            record.update(status='not_started', stop_reason='parent_signal' if flags else 'stop_file_before_start')
        else:
            child = subprocess.Popen(list(command), stdin=subprocess.DEVNULL, start_new_session=True)
            record.update(task_started=True, status='running', child_started_at=utc())
            began = time.monotonic()
            save()
            while True:
                elapsed = time.monotonic() - began
                code = child.poll()
                # Do not certify timely completion when it was first observed after the deadline.
                if elapsed >= timeout:
                    record['stop_reason'] = 'deadline_before_exit_confirmation'
                    terminate()
                    record['status'] = 'deadline_reached'
                    break
                if code is not None:
                    record.update(status=exit_status(code), child_exit_code=code,
                                  direct_child_exit_observed=True)
                    break
                reason = 'parent_signal' if flags else ('stop_file' if stop_exists(stop_file) else None)
                if reason:
                    record.update(stop_reason=reason, stop_observed_at=utc())
                    terminate()
                    record['status'] = ('interrupted' if record['signal_exit_after_request_observed']
                                        else 'finished_after_stop_request' if record['direct_child_exit_observed']
                                        else 'exit_unconfirmed')
                    break
                time.sleep(min(poll, max(0.0, timeout - elapsed)))
            record['child_observation_seconds'] = round(time.monotonic() - began, 6)
    except Exception as exc:
        record.update(status='supervisor_error', error_type=type(exc).__name__)
        if child is not None:
            terminate()
    finally:
        if child is not None:
            # Best-effort cleanup of same-group descendants, even if their parent exited.
            # No claim that escaped sessions, remote tasks, or every descendant were reaped.
            send_group(signal.SIGKILL)
            if child.poll() is None:
                try:
                    child.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    record['status'] = 'exit_unconfirmed'
            record['direct_child_exit_observed'] = child.poll() is not None
            record['child_exit_code'] = child.returncode
        record['parent_signal_received'] = flags[0] if flags else None
        record['finished_at'] = utc()
        record['elapsed_seconds'] = round(time.monotonic() - started, 6)
        _finish_receipt(handle, save, record, saved_handlers)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True, help='New JSON file; existing files are not overwritten')
    parser.add_argument('--stop-file', type=Path, help='Existence requests stop; never consumed or deleted')
    parser.add_argument('--timeout', type=float, default=60.0)
    parser.add_argument('--grace', type=float, default=1.0)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        result = run_with_receipt(command, args.receipt, stop_file=args.stop_file,
                                  timeout=args.timeout, grace=args.grace)
    except ReceiptPersistenceError as exc:
        print(json.dumps(exc.summary, ensure_ascii=True), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Launch rejected or receipt unavailable: {type(exc).__name__}', file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ('status', 'task_started', 'direct_child_exit_observed',
                                                 'child_exit_code', 'stop_reason')}))
    if result['status'] == 'completed': return 0
    if result['status'] == 'interrupted': return 130
    if result['status'] == 'deadline_reached': return 124
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
