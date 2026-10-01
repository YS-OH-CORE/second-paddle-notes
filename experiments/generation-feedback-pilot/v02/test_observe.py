import itertools
import json
import unittest
from copy import deepcopy
from pathlib import Path
import observe as o

class Checks(unittest.TestCase):
    def test_exhaustive_separation_for_32768_representations(self):
        for case in o.task.TASKS:
            for a in itertools.product(range(4), repeat=6):
                bare = json.dumps({'assignment': a})
                expected = all(x in range(3) for x in a) and all(a[u] != a[v] for u, v in case['edges'])
                for raw in (bare, '```json\n' + bare + '\n```'):
                    r = o.observe(raw, case)
                    self.assertEqual(r['strict'], o.task.evaluate(raw, case))
                    self.assertEqual(r['candidate_feasible'], expected)
                    self.assertEqual(r['candidate'], list(a))
    def test_fenced_valid_candidate_does_not_become_strict_success(self):
        r = o.observe('```json\n{"assignment":[0,1,0,1,0,1]}\n```', o.task.TASKS[0])
        self.assertTrue(r['candidate_feasible']); self.assertFalse(r['strict']['feasible'])
    def test_out_of_range_is_retained_not_clamped(self):
        r = o.observe('{"assignment":[0,1,2,3,4,5]}', o.task.TASKS[0])
        self.assertEqual(r['candidate'], [0,1,2,3,4,5])
        self.assertEqual(r['out_of_domain'], [{'station':3,'value':3},{'station':4,'value':4},{'station':5,'value':5}])
        self.assertEqual(r['equal_value_pairs'], []); self.assertFalse(r['candidate_feasible'])
    def test_no_substring_or_multiple_candidate_selection(self):
        x = '{"assignment":[0,1,0,1,0,1]}'
        for raw in ('answer: '+x, x+x, '```json\n'+x+'\n```\n'+x):
            self.assertFalse(o.observe(raw,o.task.TASKS[0])['shape_valid'])
    def test_no_duplicate_key_boolean_float_or_invented_value(self):
        for raw in ('{"assignment":[],"assignment":[0,1,0,1,0,1]}',
                    '{"assignment":[true,1,0,1,0,1]}', '{"assignment":[0.0,1,0,1,0,1]}',
                    '{"assignment":[0,1]}', '{"assignment":[NaN,1,0,1,0,1]}'):
            self.assertFalse(o.observe(raw,o.task.TASKS[0])['shape_valid'])
    def test_unknown_evaluation_stays_unknown(self):
        r = o.observe('No answer',o.task.TASKS[0])
        self.assertIsNone(r['out_of_domain']); self.assertIsNone(r['equal_value_pairs'])
    def test_frozen_initials_and_old_scores_preserved(self):
        rows=json.loads((Path(__file__).resolve().parent.parent/'OBSERVED.json').read_text())['rows']
        self.assertEqual(len(rows),12)
        for row in rows:
            case=next(t for t in o.task.TASKS if t['id']==row['case']);r=o.observe(row['raw_response'],case)
            self.assertTrue(r['shape_valid']);self.assertFalse(r['strict']['feasible']);self.assertFalse(r['candidate_feasible'])
    def test_feedback_not_a_replacement_answer(self):
        raw='```json\n{"assignment":[0,1,2,3,4,5]}\n```';case=o.task.TASKS[0]
        layered=o.cue(raw,case,'layered')
        self.assertIn('"station":3,"value":3',layered);self.assertNotIn('"assignment"',layered)
        self.assertEqual(o.cue(raw,case,'coarse'),o.task.feedback(o.task.evaluate(raw,case)))
    def test_sources_not_mutated(self):
        case=deepcopy(o.task.TASKS[0]);copy=deepcopy(case)
        o.observe('{"assignment":[0,1,2,3,4,5]}',case);self.assertEqual(case,copy)
    def test_partial_or_duplicate_inventory_rejected(self):
        with self.assertRaises(ValueError):o.summarize([])
        with self.assertRaises(ValueError):o.summarize([{'case':'G1','condition':'coarse'}]*12)

if __name__=='__main__':unittest.main(verbosity=2)
