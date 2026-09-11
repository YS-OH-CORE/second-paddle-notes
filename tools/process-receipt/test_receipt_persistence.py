"""Real owned-child effects with injected receipt-only fsync/close faults.

No real disk exhaustion, model calls, network traffic or private inputs. Run on
native Linux/Windows. Legacy POSIX entrypoint check is intentionally POSIX-only.
"""
from contextlib import redirect_stderr, redirect_stdout
import errno
import importlib
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock

import process_receipt
import process_receipt_cli


class ReceiptPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = self.root/'receipt.json'
        self.effect = self.root/'actual-effect.txt'
        self.signals = (signal.SIGINT, signal.SIGTERM)
        if os.name == 'nt':
            self.signals += (signal.SIGBREAK,)
        self.handlers = {s: signal.getsignal(s) for s in self.signals}
        self.addCleanup(self.restore_handlers)

    def restore_handlers(self):
        for sig, handler in self.handlers.items():
            signal.signal(sig, handler)

    def operation(self, *, entry='process_receipt_cli', fault='final_sync', exit_code=0, direct=False):
        # Base executable avoids the extra launcher process in a Windows venv.
        worker = str(Path(sys._base_executable).resolve())
        command = [worker, '-I', '-c',
            "from pathlib import Path; Path("+repr(str(self.effect))+").write_text('실제 실행됨', encoding='utf-8'); raise SystemExit("+str(exit_code)+")"]
        original_sync = os.fsync
        original_open = Path.open
        calls = 0
        target = self.receipt

        def sync(fd):
            nonlocal calls
            calls += 1
            if (fault in ('final_sync', 'both') and calls == 3) or fault == 'all_sync':
                raise OSError(errno.ENOSPC, 'INJECTED_PRIVATE_ERROR_TEXT')
            return original_sync(fd)

        class ClosingFault:
            def __init__(self, inner): self.inner = inner
            def __getattr__(self, name): return getattr(self.inner, name)
            def close(self):
                self.inner.close()
                raise OSError(errno.EIO, 'INJECTED_PRIVATE_ERROR_TEXT')

        def opened(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            if path == target and args and args[0] == 'x' and fault in ('close', 'both'):
                return ClosingFault(stream)
            return stream

        out, err = io.StringIO(), io.StringIO()
        raised = None
        result = None
        with mock.patch.object(os, 'fsync', sync), mock.patch.object(Path, 'open', opened):
            with redirect_stderr(err), redirect_stdout(out):
                if direct:
                    module = importlib.import_module('process_receipt_windows') if os.name == 'nt' else process_receipt
                    run = module.run_windows_with_receipt if os.name == 'nt' else module.run_with_receipt
                    try:
                        result = run(command, self.receipt)
                    except OSError as exc:
                        raised = exc
                else:
                    module = importlib.import_module(entry)
                    with mock.patch.object(sys, 'argv', ['receipt', '--receipt', str(self.receipt), '--', *command]):
                        result = module.main()
        observation = dict(case=self.id(), platform=sys.platform, entrypoint=entry, fault=fault,
            returncode=result if not direct else None,
            exception_type=type(raised).__name__ if raised else None,
            stdout=out.getvalue(), stderr=err.getvalue(), child_effect_exists=self.effect.exists(),
            child_effect=self.effect.read_text(encoding='utf-8') if self.effect.exists() else None,
            handlers_restored=all(signal.getsignal(s) == h for s,h in self.handlers.items()),
            sync_calls=calls, api_summary=getattr(raised, 'summary', None),
            runtime_paths={n: sys.modules[n].__file__ for n in
                ('process_receipt','process_receipt_cli','process_receipt_windows') if n in sys.modules})
        dest = os.environ.get('RECEIPT_IO_OBSERVATIONS')
        if dest:
            with original_open(Path(dest), 'a', encoding='utf-8') as stream:
                stream.write(json.dumps(observation, ensure_ascii=True)+'\n')
        return observation, raised

    def structured(self, observation):
        self.assertEqual(observation['returncode'], 2)
        self.assertTrue(observation['stderr'].strip().startswith('{'), 'No structured execution outcome: '+observation['stderr'])
        data = json.loads(observation['stderr'])
        self.assertEqual(data['status'], 'receipt_persistence_failed')
        self.assertFalse(data['receipt_finalization_confirmed'])
        self.assertNotIn('INJECTED_PRIVATE_ERROR_TEXT', observation['stderr'])
        self.assertNotIn(str(self.effect), observation['stderr'])
        return data

    def test_portable_retains_actual_success_after_final_sync_failure(self):
        o,_=self.operation(); data=self.structured(o)
        self.assertTrue(o['child_effect_exists'])
        self.assertEqual(data['execution']['status'], 'completed')
        self.assertTrue(data['execution']['task_started'])
        self.assertTrue(data['execution']['direct_child_exit_observed'])
        self.assertEqual(data['execution']['child_exit_code'], 0)

    def test_portable_retains_nonzero_effect_after_final_sync_failure(self):
        o,_=self.operation(exit_code=7); data=self.structured(o)
        self.assertTrue(o['child_effect_exists'])
        self.assertEqual((data['execution']['status'], data['execution']['child_exit_code']), ('failed',7))

    @unittest.skipUnless(os.name == 'posix', 'Historical module entrypoint is POSIX-only')
    def test_legacy_cli_never_denies_observed_execution(self):
        o,_=self.operation(entry='process_receipt'); data=self.structured(o)
        self.assertTrue(o['child_effect_exists'])
        self.assertTrue(data['execution']['task_started'])
        self.assertNotIn('not launched', o['stderr'])

    def test_persistent_initial_sync_fault_does_not_launch_child(self):
        o,_=self.operation(fault='all_sync'); data=self.structured(o)
        self.assertFalse(o['child_effect_exists'])
        self.assertFalse(data['execution']['task_started'])
        self.assertFalse(data['execution']['direct_child_exit_observed'])

    def test_close_failure_keeps_actual_outcome_and_restores_handlers(self):
        o,_=self.operation(fault='close')
        self.assertTrue(o['handlers_restored'], 'Receipt close failure leaked supervisor signal handlers')
        data=self.structured(o)
        self.assertTrue(o['child_effect_exists'])
        self.assertEqual(data['execution']['child_exit_code'], 0)
        self.assertEqual([e['phase'] for e in data['receipt_errors']], ['close'])

    def test_both_failures_are_reported_without_losing_cleanup(self):
        o,_=self.operation(fault='both')
        self.assertTrue(o['handlers_restored'], 'Final save+close failure leaked signal handlers')
        data=self.structured(o)
        self.assertEqual([e['phase'] for e in data['receipt_errors']], ['write_flush_sync','close'])
        self.assertTrue(data['execution']['task_started'])

    def test_api_error_carries_observed_execution(self):
        o,exc=self.operation(direct=True)
        self.assertTrue(o['child_effect_exists'])
        self.assertIsNotNone(exc)
        self.assertIsNotNone(getattr(exc, 'summary', None), 'API exception lost the observed execution outcome')
        self.assertTrue(exc.summary['execution']['task_started'])
        self.assertEqual(exc.summary['execution']['child_exit_code'], 0)

    def test_no_fault_stays_completed(self):
        o,_=self.operation(fault='none')
        self.assertEqual(o['returncode'],0)
        self.assertEqual(o['stderr'],'')
        self.assertTrue(o['child_effect_exists'])
        self.assertTrue(o['handlers_restored'])
        self.assertEqual(json.loads(self.receipt.read_text())['status'],'completed')

    def test_existing_receipt_is_not_replaced_or_executed(self):
        self.receipt.write_bytes(b'original record')
        o,_=self.operation(fault='none')
        self.assertEqual(o['returncode'],2)
        self.assertFalse(o['child_effect_exists'])
        self.assertEqual(self.receipt.read_bytes(), b'original record')


if __name__ == '__main__':
    unittest.main(verbosity=2)
