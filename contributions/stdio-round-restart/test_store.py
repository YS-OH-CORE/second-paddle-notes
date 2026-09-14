"""Standard-library fixture-store tests, not MCP transport tests."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from stdio_restart_probe import KEY, NOTE, RoundStore

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'server.sqlite'
        self.store = RoundStore(self.path)
        self.token, self.subject = self.store.issue()
        self.accept = {KEY: {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}}
    def test_reopened_store_keeps_original(self):
        self.assertEqual(RoundStore(self.path).answer(self.token, self.accept), ('previewed:draft-1', False))
        self.assertEqual(self.store.snapshot()['effects'], [[self.token, 'draft-1']])
    def test_new_question_is_distinct(self):
        token, subject = RoundStore(self.path).issue()
        self.assertNotEqual(token, self.token)
        self.assertEqual(subject, 'draft-2')
    def test_empty_server_store_rejects_old_state(self):
        other = RoundStore(Path(self.temp.name) / 'other.sqlite')
        self.assertEqual(other.answer(self.token, self.accept), ('UNKNOWN_ROUND', True))
        self.assertEqual(other.snapshot()['effects'], [])
    def test_unknown_token(self):
        self.assertEqual(self.store.answer("' OR 1=1 --", self.accept), ('UNKNOWN_ROUND', True))
    def test_wrong_key_does_not_consume(self):
        self.assertEqual(self.store.answer(self.token, {'different': self.accept[KEY]}), ('ANSWER_KEYS_DIFFER', True))
        self.assertEqual(self.store.answer(self.token, self.accept), ('previewed:draft-1', False))
    def test_decline(self):
        self.assertEqual(self.store.answer(self.token, {KEY: {'action': 'decline'}}), ('skipped:decline', False))
        self.assertEqual(self.store.snapshot()['effects'], [])
    def test_cancel(self):
        self.assertEqual(self.store.answer(self.token, {KEY: {'action': 'cancel'}}), ('skipped:cancel', False))
        self.assertEqual(self.store.snapshot()['effects'], [])
    def test_duplicate_does_not_repeat_label(self):
        self.store.answer(self.token, self.accept)
        self.assertEqual(self.store.answer(self.token, self.accept), ('ROUND_ALREADY_CLOSED', True))
        self.assertEqual(len(self.store.snapshot()['effects']), 1)
    def test_numeric_one_not_boolean_true(self):
        answer = deepcopy(self.accept)
        answer[KEY]['content']['yes'] = 1
        self.assertEqual(self.store.answer(self.token, answer), ('FORM_CONTENT_DIFFER', True))
    def test_whitespace_preserved(self):
        answer = deepcopy(self.accept)
        answer[KEY]['content']['note'] = NOTE.strip()
        self.assertEqual(self.store.answer(self.token, answer), ('FORM_CONTENT_DIFFER', True))
    def test_decline_with_content_rejected(self):
        answer = deepcopy(self.accept)
        answer[KEY]['action'] = 'decline'
        self.assertEqual(self.store.answer(self.token, answer), ('CONTENT_WITHOUT_ACCEPT', True))
    def test_invalid_action(self):
        self.assertEqual(self.store.answer(self.token, {KEY: {'action': 'unknown'}}), ('ANSWER_ACTION', True))

if __name__ == '__main__': unittest.main()
