from copy import deepcopy
import unittest
from round_graph import validate_answers

class AnswerChecks(unittest.TestCase):
    def test_exact_keys(self):
        r={'responses':{'one':{'action':'accept','content':{'text':'  한글\n'}}}}
        self.assertEqual(validate_answers(['one'],r),r['responses'])
    def test_independent_copy(self):
        r={'responses':{'one':{'action':'accept','content':{'yes':True}}}};old=deepcopy(r)
        validate_answers(['one'],r)['one']['content']['yes']=False
        self.assertEqual(r,old)
    def test_missing_key(self):
        with self.assertRaisesRegex(ValueError,'ANSWER_KEYS_DIFFER'):validate_answers(['one'],{'responses':{}})
    def test_extra_key(self):
        with self.assertRaisesRegex(ValueError,'ANSWER_KEYS_DIFFER'):validate_answers(['one'],{'responses':{'two':{'action':'accept'}}})
    def test_wrong_action(self):
        with self.assertRaisesRegex(ValueError,'ANSWER_ACTION'):validate_answers(['one'],{'responses':{'one':{'action':'maybe'}}})
    def test_decline_cancel(self):
        for action in ['decline','cancel']:
            self.assertEqual(validate_answers(['one'],{'responses':{'one':{'action':action}}}),{'one':{'action':action}})
    def test_refusal_has_no_content(self):
        with self.assertRaisesRegex(ValueError,'CONTENT_WITHOUT_ACCEPT'):validate_answers(['one'],{'responses':{'one':{'action':'decline','content':{'yes':True}}}})
    def test_unknown_envelope_not_ignored(self):
        with self.assertRaisesRegex(ValueError,'RESUME_SHAPE'):validate_answers(['one'],{'responses':{},'execute':True})

if __name__=='__main__':unittest.main()
