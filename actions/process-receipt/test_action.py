"""Adapter contract checks; real inert child processes, selected injected I/O faults."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import run_action as a

RUNTIME = None
OBSERVATIONS = []


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = self.root/'receipt.json'
        self.marker = self.root/'actual-effect'

    def run_child(self, code='', **kwargs):
        command = [str(Path(sys._base_executable).resolve()), '-I', '-c', code or 'pass']
        result = a.execute(*RUNTIME, command, self.receipt, kwargs.get('stop'),
                           {'timeout': kwargs.get('timeout', 5), 'grace': 1})
        OBSERVATIONS.append({'case': self._testMethodName, 'result': result,
                             'marker_exists': self.marker.exists()})
        return result

    def test_validated_argument_vectors(self):
        literal = '한글  $(touch SHOULD_NOT_EXIST)\n  exact whitespace  '
        command, _ = a.parse_inputs({'PR_COMMAND_JSON': json.dumps(['python', literal])})
        self.assertEqual(command[1], literal)
        for invalid in ('[]', '"echo text"', '[1]', '[""]', '["x",null]'):
            with self.assertRaises(ValueError):
                a.parse_inputs({'PR_COMMAND_JSON': invalid})
        with self.assertRaises(ValueError):
            a.parse_inputs({'PR_COMMAND_JSON': '["python"]', 'PR_TIMEOUT': 'nan'})
        with self.assertRaises(ValueError):
            a.parse_inputs({'PR_COMMAND_JSON': '["python"]', 'PR_RECEIPT_PATH': 'x\nspoof=true'})

    def test_normal_output_is_observed(self):
        r = self.run_child(f'from pathlib import Path; Path({str(self.marker)!r}).write_text("executed")')
        self.assertEqual((r['action_status'], r['receipt_state']), ('completed', 'finalized'))
        self.assertTrue(r['execution']['task_started'])
        self.assertEqual(self.marker.read_text(), 'executed')

    def test_nonzero_is_not_success(self):
        r = self.run_child('raise SystemExit(7)')
        self.assertEqual(r['action_status'], 'failed')
        self.assertEqual(r['execution']['child_exit_code'], 7)

    def test_prestop_is_distinct_from_failure_after_execution(self):
        stop = self.root/'STOP'; stop.touch()
        r = self.run_child(f'open({str(self.marker)!r},"w").close()', stop=stop)
        self.assertEqual(r['execution']['status'], 'not_started')
        self.assertFalse(r['execution']['task_started'])
        self.assertFalse(self.marker.exists())
        self.assertTrue(stop.exists())

    def test_collision_does_not_read_old_success_as_new(self):
        old = b'{"status":"completed","task_started":true}'
        self.receipt.write_bytes(old)
        r = self.run_child(f'open({str(self.marker)!r},"w").close()')
        self.assertEqual(r['action_status'], 'rejected')
        self.assertFalse(r['execution']['task_started'])
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.receipt.read_bytes(), old)

    def test_timeout_is_observed_not_completed(self):
        r = self.run_child('import time; time.sleep(5)', timeout=0.1)
        self.assertEqual(r['execution']['status'], 'deadline_reached')
        self.assertTrue(r['execution']['direct_child_exit_observed'])
        self.assertEqual(r['action_status'], 'failed')

    def test_final_fsync_failure_preserves_actual_execution(self):
        core, _ = RUNTIME
        real_fsync = core.os.fsync
        count = 0
        def fault(fd):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError('injected test only')
            return real_fsync(fd)
        with patch.object(core.os, 'fsync', side_effect=fault):
            r = self.run_child(f'from pathlib import Path; Path({str(self.marker)!r}).write_text("executed")')
        self.assertEqual(count, 3)
        self.assertEqual(r['action_status'], 'receipt_persistence_failed')
        self.assertEqual(r['receipt_state'], 'unconfirmed')
        self.assertTrue(r['execution']['task_started'])
        self.assertEqual(r['execution']['status'], 'completed')
        self.assertEqual(r['execution']['child_exit_code'], 0)
        self.assertEqual(self.marker.read_text(), 'executed')

    def test_unexpected_runtime_error_remains_unknown(self):
        core, windows = RUNTIME
        target, name = ((windows, 'run_windows_with_receipt') if os.name == 'nt' else (core, 'run_with_receipt'))
        with patch.object(target, name, side_effect=RuntimeError('controlled unexpected exception')):
            r = self.run_child()
        self.assertEqual(r['action_status'], 'adapter_error')
        self.assertIsNone(r['execution']['task_started'])
        self.assertIsNone(r['execution']['direct_child_exit_observed'])

    def test_missing_program_does_not_claim_execution(self):
        r = a.execute(*RUNTIME, [str(self.root/'absent.exe')], self.receipt, None, {'timeout': 5})
        OBSERVATIONS.append({'case': self._testMethodName, 'result': r})
        self.assertEqual(r['action_status'], 'failed')
        self.assertFalse(r['execution']['task_started'])

    def test_unknown_fields_stay_unknown_in_workflow_outputs(self):
        r = dict(action_status='adapter_error', receipt_state='unconfirmed',
                 execution=a.unknown_execution(), receipt_path='a', summary_path='b')
        out = a.outputs(r)
        self.assertEqual(out['task-started'], 'unknown')
        self.assertEqual(out['child-exit-code'], 'unknown')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--wheel', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        RUNTIME = a.load_verified_wheel(args.wheel.read_bytes(), Path(tmp))
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
            'errors': len(result.errors), 'skips': len(result.skipped), 'observations': OBSERVATIONS,
            'scope': 'Adapter API around real inert children; final fsync and unexpected exception are injected.'},
            ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
        raise SystemExit(0 if result.wasSuccessful() else 1)
