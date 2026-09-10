"""Stdlib regression checks using owned, inert processes and temporary files."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from process_receipt import run_with_receipt

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(os.name == 'posix', 'POSIX-only tool')
class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, code='pass', **kwargs):
        return run_with_receipt([sys.executable, '-I', '-c', code], self.root/'receipt.json', **kwargs)

    def test_normal_exit(self):
        r = self.invoke()
        self.assertEqual(r['status'], 'completed')
        self.assertTrue(r['direct_child_exit_observed'])
        self.assertEqual(r['child_exit_code'], 0)
        self.assertFalse(r['signal_exit_after_request_observed'])
        self.assertEqual(json.loads((self.root/'receipt.json').read_text()), r)

    def test_nonzero_exit(self):
        r = self.invoke('raise SystemExit(7)')
        self.assertEqual((r['status'], r['child_exit_code']), ('failed', 7))

    def test_stop_before_start(self):
        stop = self.root/'STOP'; stop.write_text('stop')
        r = self.invoke(f'open({str(self.root/"bad")!r}, "w").close()', stop_file=stop)
        self.assertEqual(r['status'], 'not_started')
        self.assertFalse(r['task_started'])
        self.assertFalse((self.root/'bad').exists())
        self.assertTrue(stop.exists())

    def test_dangling_symlink_is_stop(self):
        stop = self.root/'STOP'; stop.symlink_to(self.root/'absent')
        r = self.invoke(stop_file=stop)
        self.assertFalse(r['task_started'])
        self.assertTrue(stop.is_symlink())

    def test_existing_receipt_never_overwritten(self):
        path = self.root/'receipt.json'; path.write_text('original')
        with self.assertRaises(FileExistsError):
            self.invoke(f'open({str(self.root/"bad")!r}, "w").close()')
        self.assertEqual(path.read_text(), 'original')
        self.assertFalse((self.root/'bad').exists())

    def test_deadline(self):
        r = self.invoke('import time; time.sleep(4)', timeout=0.15, grace=0.1)
        self.assertEqual(r['status'], 'deadline_reached')
        self.assertTrue(r['direct_child_exit_observed'])
        self.assertLess(r['elapsed_seconds'], 2)

    def test_invalid_limits_prevent_launch(self):
        for value in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                self.invoke(timeout=value)
        self.assertFalse((self.root/'receipt.json').exists())

    def test_same_receipt_and_stop_rejected(self):
        with self.assertRaises(ValueError):
            self.invoke(stop_file=self.root/'receipt.json')
        self.assertFalse((self.root/'receipt.json').exists())

    def test_launch_error_is_not_execution(self):
        r = run_with_receipt([str(self.root/'missing-program')], self.root/'receipt.json')
        self.assertFalse(r['task_started'])
        self.assertEqual(r['status'], 'supervisor_error')
        self.assertFalse(r['direct_child_exit_observed'])

    def test_parent_signal_is_forwarded(self):
        # Signal a separate supervisor, never the unittest process itself.
        receipt = self.root/'receipt.json'; ready = self.root/'ready'
        cmd = [sys.executable, str(ROOT/'process_receipt.py'), '--receipt', str(receipt), '--timeout', '8', '--',
               sys.executable, '-I', '-c', f'import time; open({str(ready)!r}, "w").close(); time.sleep(6)']
        parent = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+4
            while not ready.exists() and parent.poll() is None and time.monotonic()<deadline:
                time.sleep(0.01)
            self.assertTrue(ready.exists())
            parent.send_signal(signal.SIGTERM)
            self.assertEqual(parent.wait(timeout=3), 130)
            r = json.loads(receipt.read_text())
            self.assertEqual(r['stop_reason'], 'parent_signal')
            self.assertEqual(r['status'], 'interrupted')
            self.assertTrue(r['signal_exit_after_request_observed'])
        finally:
            if parent.poll() is None:
                parent.kill(); parent.wait(timeout=2)

    def test_graceful_exit_is_not_claimed_as_signal_exit(self):
        stop = self.root/'STOP'; ready = self.root/'ready'
        code = ('import signal,time; '
                'signal.signal(signal.SIGTERM, lambda a,b: exit(0)); '
                f'open({str(ready)!r}, "w").close(); time.sleep(5)')
        def request():
            until = time.monotonic()+3
            while not ready.exists() and time.monotonic()<until:
                time.sleep(0.01)
            stop.write_text('stop')
        thread = threading.Thread(target=request); thread.start()
        r = self.invoke(code, stop_file=stop, timeout=6, grace=0.2)
        thread.join(timeout=4)
        self.assertEqual(r['status'], 'finished_after_stop_request')
        self.assertEqual(r['child_exit_code'], 0)
        self.assertFalse(r['signal_exit_after_request_observed'])


if __name__ == '__main__':
    unittest.main()
