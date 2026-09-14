"""Fixture-store tests only, not SDK or OS-crash experiments."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from receipt_store import ARGS, KEY, NOTE, ReceiptStore


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'store.sqlite'
        self.store = ReceiptStore(self.path, 'receipt')
        self.token = self.store.issue(ARGS)
        self.answers = {KEY: {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}}

    def call(self, store=None, answers=None, token=None, name='preview', arguments=None):
        return (store or self.store).complete(name, arguments if arguments is not None else ARGS,
                    token or self.token, self.answers if answers is None else answers)

    def test_receipt_after_reopen(self):
        first, route = self.call()
        second, replay = self.call(ReceiptStore(self.path, 'receipt'))
        self.assertEqual(route, 'effect_committed')
        self.assertEqual(replay, 'receipt_replayed')
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.snapshot()['effects']), 1)

    def test_naive_control_duplicates(self):
        store = ReceiptStore(Path(self.temp.name) / 'naive.sqlite', 'naive')
        token = store.issue(ARGS)
        first, _ = self.call(store, token=token)
        second, _ = self.call(store, token=token)
        self.assertNotEqual(first, second)
        self.assertEqual(len(store.snapshot()['effects']), 2)

    def test_guard_loses_completion_result(self):
        store = ReceiptStore(Path(self.temp.name) / 'guard.sqlite', 'closed_guard')
        token = store.issue(ARGS)
        self.call(store, token=token)
        result, route = self.call(store, token=token)
        self.assertEqual(route, 'closed')
        self.assertTrue(result['isError'])
        self.assertEqual(len(store.snapshot()['effects']), 1)

    def test_changed_answer_rejected(self):
        self.call()
        changed = deepcopy(self.answers)
        changed[KEY]['content']['note'] += 'different'
        self.assertEqual(self.call(answers=changed)[1], 'mismatch')
        self.assertEqual(len(self.store.snapshot()['effects']), 1)

    def test_changed_arguments_rejected(self):
        self.call()
        self.assertEqual(self.call(arguments={'label': 'draft-2'})[1], 'mismatch')

    def test_changed_name_rejected(self):
        self.call()
        self.assertEqual(self.call(name='other')[1], 'mismatch')

    def test_unknown_token(self):
        self.assertEqual(self.call(token="' OR 1=1 --")[1], 'unknown')
        self.assertEqual(self.store.snapshot()['effects'], [])

    def test_numeric_one_not_true(self):
        changed = deepcopy(self.answers)
        changed[KEY]['content']['yes'] = 1
        self.assertTrue(self.call(answers=changed)[0]['isError'])
        self.assertEqual(self.store.snapshot()['effects'], [])

    def test_numeric_one_not_same_cached_answer(self):
        self.call()
        changed = deepcopy(self.answers)
        changed[KEY]['content']['yes'] = 1
        self.assertEqual(self.call(answers=changed)[1], 'mismatch')

    def test_whitespace_is_bound(self):
        self.call()
        changed = deepcopy(self.answers)
        changed[KEY]['content']['note'] = NOTE.strip()
        self.assertEqual(self.call(answers=changed)[1], 'mismatch')

    def test_key_order_not_significant(self):
        self.call()
        reordered = {KEY: {'content': {'note': NOTE, 'yes': True}, 'action': 'accept'}}
        self.assertEqual(self.call(answers=reordered)[1], 'receipt_replayed')

    def test_missing_answer_does_not_consume(self):
        self.assertEqual(self.call(answers={})[1], 'invalid')
        self.assertEqual(self.call()[1], 'effect_committed')

    def test_store_mode_cannot_change(self):
        with self.assertRaisesRegex(ValueError, 'STORE_MODE_CHANGED'):
            ReceiptStore(self.path, 'naive')

    def test_receipt_update_failure_rolls_back_label(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON rounds BEGIN SELECT RAISE(ABORT, 'fixture rollback'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.call()
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['effects'], [])
        self.assertIsNone(snapshot['rounds'][0][2])
        self.assertIsNone(snapshot['rounds'][0][3])

    def test_distinct_rounds_have_distinct_receipts(self):
        first, _ = self.call()
        token = self.store.issue(ARGS)
        second, _ = self.call(token=token)
        self.assertNotEqual(self.token, token)
        self.assertNotEqual(first['structuredContent']['effect_id'], second['structuredContent']['effect_id'])

    def test_returned_result_mutation_does_not_change_stored_receipt(self):
        first, _ = self.call()
        original = deepcopy(first)
        first['content'][0]['text'] = 'changed outside'
        replay, _ = self.call()
        self.assertEqual(original, replay)


if __name__ == '__main__':
    unittest.main()
