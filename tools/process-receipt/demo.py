#!/usr/bin/env python3
"""Produce public-safe receipts from real, inert local processes. No model calls."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import signal
import sys
import threading
import time
from process_receipt import run_with_receipt

WORKER = r'''
import json, signal, sys, time
from pathlib import Path
folder = Path(sys.argv[1])
if sys.argv[2] == 'ignore-term':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
(folder/'ready').write_text('ready', encoding='utf-8')
start = time.monotonic()
with (folder/'heartbeat.jsonl').open('x', encoding='utf-8') as f:
    while time.monotonic()-start < float(sys.argv[3]):
        f.write(json.dumps({'elapsed_seconds':round(time.monotonic()-start, 6)})+'\n')
        f.flush()
        time.sleep(0.05)
(folder/'natural_completion.json').write_text(json.dumps({'natural_completion':True}), encoding='utf-8')
'''


def demo(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    summaries = []
    for name, mode, duration, should_stop in (
        ('normal', 'normal', 0.25, False),
        ('stop', 'normal', 4.0, True),
        ('term_ignored', 'ignore-term', 4.0, True),
    ):
        folder = out/name
        folder.mkdir()
        stop = folder/'STOP'
        errors = []
        def request_stop():
            deadline = time.monotonic()+5
            while not (folder/'ready').exists():
                if time.monotonic() >= deadline:
                    errors.append('Worker readiness was not observed')
                    return
                time.sleep(0.01)
            time.sleep(0.15)
            stop.write_text('inert demo stop', encoding='utf-8')
        thread = threading.Thread(target=request_stop) if should_stop else None
        if thread:
            thread.start()
        receipt = run_with_receipt([sys.executable, '-I', '-c', WORKER, str(folder.resolve()), mode, str(duration)],
                                   folder/'receipt.json', stop_file=stop, timeout=6, grace=0.2, poll=0.02)
        if thread:
            thread.join(timeout=6)
            if thread.is_alive() or errors:
                raise RuntimeError('Demo stop request was not completed')
        natural = (folder/'natural_completion.json').exists()
        heartbeat = folder/'heartbeat.jsonl'
        count = len(heartbeat.read_text(encoding='utf-8').splitlines()) if heartbeat.exists() else 0
        expected = 'interrupted' if should_stop else 'completed'
        if receipt['status'] != expected or natural == should_stop or count == 0:
            raise AssertionError(f'{name}: receipt and actual files did not match expectations')
        if name == 'term_ignored' and receipt['child_exit_code'] != -signal.SIGKILL:
            raise AssertionError('Ignoring SIGTERM did not require an observed SIGKILL exit')
        if should_stop and not receipt['signal_exit_after_request_observed']:
            raise AssertionError('Missing direct-child signal exit evidence')
        summaries.append(dict(case=name, status=receipt['status'],
            child_exit_code=receipt['child_exit_code'], heartbeat_count=count,
            natural_completion_file=natural, duration_requested=duration,
            observed_seconds=receipt['child_observation_seconds']))
    summary = dict(schema='process-receipt-demo-v1', cases=summaries,
                   source='Real inert processes started by this script, not a language-model evaluation',
                   external_replication=False)
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New folder; must not exist')
    demo(parser.parse_args().out)
