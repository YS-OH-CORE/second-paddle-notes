import copy
import unittest
from smoke import cases, parse_decision
import json

class HarnessTests(unittest.TestCase):
    def test_specified_choices(self):
        self.assertEqual([c['expected']['selected'] for c in cases()], ['Beryl','Aster','Tarin','Vela'])
    def test_full_positive_and_wrong_choice(self):
        for c in cases():
            e = c['expected']
            self.assertTrue(parse_decision(json.dumps(e), e)['smoke_match'])
            wrong = dict(e, selected='wrong')
            self.assertFalse(parse_decision(json.dumps(wrong),e)['smoke_match'])
    def test_retention_order_not_semantic(self):
        c = cases()[0]
        v = copy.deepcopy(c['expected'])
        v['retained'].reverse()
        self.assertTrue(parse_decision(json.dumps(v),c['expected'])['smoke_match'])
    def test_duplicate_unknown_and_missing_fields(self):
        c = cases()[0]['expected']
        for s in ['{"criterion":"latency","criterion":"reproducibility"}', '{}', 'not json']:
            self.assertFalse(parse_decision(s,c)['smoke_match'])
        v = dict(c, extra=True)
        self.assertFalse(parse_decision(json.dumps(v),c)['smoke_match'])
    def test_model_history_excludes_oracle(self):
        for c in cases():
            self.assertTrue(all(set(m)=={'role','content'} for m in c['history']))
            self.assertNotIn('expected',json.dumps(c['history']))

if __name__ == '__main__': unittest.main()
