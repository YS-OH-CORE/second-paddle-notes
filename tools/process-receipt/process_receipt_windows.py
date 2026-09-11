"""Experimental Windows backend: observe only the directly launched EXE.

Uses Python's owned process handle, not taskkill/PID enumeration. TerminateProcess
is not a POSIX signal, a graceful shutdown, or a process-tree/rollback guarantee.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
from typing import Sequence

from process_receipt import positive, stop_exists, utc


def run_windows_with_receipt(command: Sequence[str], receipt_path: Path, *,
                             stop_file: Path | None = None, timeout: float = 60.0,
                             grace: float = 1.0, poll: float = 0.05) -> dict:
    """Run a trusted EXE; a stop requests direct-child TerminateProcess only.

    ``grace`` bounds the wait AFTER forcible termination, not a graceful phase.
    The child inherits environment and output streams. Batch files are rejected
    rather than implicitly invoking a shell. Use a trusted filesystem/workload.
    """
    if os.name != 'nt':
        raise RuntimeError('Windows backend requires Windows')
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('Run the supervisor in the main thread')
    if (isinstance(command, (str, bytes)) or not command or
            not all(isinstance(x, str) and '\0' not in x for x in command)):
        raise ValueError('command must contain argument strings without NUL')
    timeout, grace, poll = (positive(timeout, 'timeout'), positive(grace, 'grace'),
                            positive(poll, 'poll'))
    executable = shutil.which(command[0]) or command[0]
    if Path(executable).suffix.lower() != '.exe':
        raise ValueError('Windows backend requires an EXE, not an implicit batch shell')
    args = [executable, *command[1:]]
    receipt_path = Path(receipt_path)
    stop_file = Path(stop_file) if stop_file is not None else None
    if stop_file is not None and os.path.normcase(str(stop_file.resolve())) == os.path.normcase(str(receipt_path.resolve())):
        raise ValueError('receipt and stop file must be different paths')
    handle = receipt_path.open('x', encoding='utf-8', newline='\n')
    began = time.monotonic()
    child = None
    flags: list[int] = []
    previous_handlers = {}
    record = dict(schema='process-receipt-v1', backend='windows-direct-child',
        started_at=utc(), status='not_started', task_started=False, stop_reason=None,
        child_exit_code=None, direct_child_exit_observed=False,
        alive_when_stop_observed=False, signal_exit_after_request_observed=False,
        signals_requested=[], termination_requests=[], termination_request_returned=False,
        exit_observed_after_termination_request=False,
        timeout_seconds=timeout, grace_seconds=grace, poll_seconds=poll,
        scope='Only the directly launched Windows EXE; descendants, remote jobs and rollback are NOT covered')

    def save() -> None:
        handle.seek(0)
        json.dump(record, handle, ensure_ascii=False, allow_nan=False, indent=2)
        handle.write('\n')
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())

    def receive(number, frame) -> None:
        if not flags:
            flags.append(number)

    def request_termination() -> None:
        if child is None:
            return
        alive = child.poll() is None
        record['alive_when_stop_observed'] |= alive
        if alive:
            record['termination_requests'].append('TerminateProcess')
            try:
                child.terminate()
                record['termination_request_returned'] = True
            except OSError as exc:
                record.setdefault('termination_errors', []).append(type(exc).__name__)
            try:
                child.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
        code = child.poll()
        record['child_exit_code'] = code
        record['direct_child_exit_observed'] = code is not None
        record['exit_observed_after_termination_request'] = bool(
            record['alive_when_stop_observed'] and record['termination_request_returned']
            and code is not None)

    try:
        save()
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGBREAK):
            previous_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, receive)
        if flags or stop_exists(stop_file):
            record['stop_reason'] = 'parent_signal' if flags else 'stop_file_before_start'
        else:
            child = subprocess.Popen(args, shell=False, stdin=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            record.update(task_started=True, status='running', child_started_at=utc())
            launched = time.monotonic()
            save()
            while True:
                elapsed = time.monotonic() - launched
                code = child.poll()
                if elapsed >= timeout:
                    record['stop_reason'] = 'deadline_before_exit_confirmation'
                    request_termination()
                    record['status'] = 'deadline_reached' if record['direct_child_exit_observed'] else 'exit_unconfirmed'
                    break
                if code is not None:
                    record.update(status='completed' if code == 0 else 'failed',
                                  child_exit_code=code, direct_child_exit_observed=True)
                    break
                reason = 'parent_signal' if flags else ('stop_file' if stop_exists(stop_file) else None)
                if reason:
                    record.update(stop_reason=reason, stop_observed_at=utc())
                    request_termination()
                    record['status'] = 'finished_after_stop_request' if record['direct_child_exit_observed'] else 'exit_unconfirmed'
                    break
                time.sleep(min(poll, max(0.0, timeout - elapsed)))
            record['child_observation_seconds'] = round(time.monotonic() - launched, 6)
    except Exception as exc:
        record.update(status='supervisor_error', error_type=type(exc).__name__)
        request_termination()
    finally:
        if child is not None:
            if child.poll() is None:
                request_termination()
            record['direct_child_exit_observed'] = child.poll() is not None
            record['child_exit_code'] = child.returncode
            if child.returncode is None:
                record['status'] = 'exit_unconfirmed'
        record.update(parent_signal_received=flags[0] if flags else None,
                      finished_at=utc(), elapsed_seconds=round(time.monotonic() - began, 6))
        try:
            save()
        finally:
            handle.close()
            for sig, previous in previous_handlers.items():
                signal.signal(sig, previous)
    return record
