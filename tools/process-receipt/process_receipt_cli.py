"""Installed cross-platform entry point; the historical POSIX API is unchanged."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
from process_receipt import ReceiptPersistenceError


def main() -> int:
    parser = argparse.ArgumentParser(description='Supervise one trusted executable; observe direct-child exit, not goal completion.')
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--stop-file', type=Path)
    parser.add_argument('--timeout', type=float, default=60.0)
    parser.add_argument('--grace', type=float, default=1.0,
                        help='POSIX graceful-stop wait; Windows post-TerminateProcess wait')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if os.name == 'nt':
        from process_receipt_windows import run_windows_with_receipt as run
    else:
        from process_receipt import run_with_receipt as run
    try:
        result = run(command, args.receipt, stop_file=args.stop_file,
                     timeout=args.timeout, grace=args.grace)
    except ReceiptPersistenceError as exc:
        print(json.dumps(exc.summary, ensure_ascii=True), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        # A final receipt write can fail AFTER execution; never say "not launched" here.
        print(f'Launch rejected or receipt unavailable: {type(exc).__name__}', file=sys.stderr)
        return 2
    keys = ('status', 'task_started', 'direct_child_exit_observed', 'child_exit_code', 'stop_reason')
    print(json.dumps({key: result[key] for key in keys}))
    if result['status'] == 'completed':
        return 0
    if result['status'] == 'deadline_reached':
        return 124
    if (result['status'] == 'interrupted' or
            (result.get('backend') == 'windows-direct-child'
             and result['status'] == 'finished_after_stop_request'
             and result['exit_observed_after_termination_request'])):
        return 130
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
