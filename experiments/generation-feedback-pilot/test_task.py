import itertools,json,unittest
from copy import deepcopy
import task

class Checks(unittest.TestCase):
    def test_all_2916_assignments_match_independent_partition_oracle(self):
        for t in task.TASKS:
            edges={frozenset(e) for e in t['edges']}
            for a in itertools.product(range(3),repeat=6):
                same={frozenset((u,v)) for group in range(3)
                      for u,v in itertools.combinations([i for i,c in enumerate(a) if c==group],2)}
                expected=not bool(same&edges)
                self.assertEqual(task.evaluate(json.dumps({'assignment':a}),t)['feasible'],expected)
    def test_multiple_valid_answers_each_task(self):
        for t in task.TASKS:self.assertGreater(len(task.solutions(t)),1)
    def test_no_automatic_prose_repair(self):
        t=task.TASKS[0];x=json.dumps({'assignment':task.solutions(t)[0]})
        for raw in ('Sure '+x,'```json\n'+x+'\n```',x+x):self.assertFalse(task.evaluate(raw,t)['format_valid'])
    def test_duplicates_booleans_floats_out_of_range(self):
        for raw in ('{"assignment":[],"assignment":[0,1,2,0,1,2]}',
                    '{"assignment":[true,1,2,0,1,2]}','{"assignment":[0.0,1,2,0,1,2]}',
                    '{"assignment":[3,1,2,0,1,2]}','{"assignment":[NaN,1,2,0,1,2]}'):
            self.assertFalse(task.evaluate(raw,task.TASKS[0])['format_valid'])
    def test_syntax_failure_is_not_invented_constraint_feedback(self):
        f=task.feedback(task.evaluate('not JSON',task.TASKS[0]))
        self.assertIn('"format_valid":false',f);self.assertNotIn('violated_pairs',f)
    def test_feedback_contains_all_conflicts_but_no_replacement_assignment(self):
        t=task.TASKS[0];e=task.evaluate('{"assignment":[0,0,0,0,0,0]}',t)
        self.assertEqual(e['violated_pairs'],t['edges'])
        self.assertNotIn('"assignment"',task.feedback(e))
    def test_progress_and_new_breakage_are_separate(self):
        t=task.TASKS[0];a=task.evaluate('{"assignment":[0,1,0,1,0,1]}',t)
        b=task.evaluate('{"assignment":[0,0,0,0,0,0]}',t)
        self.assertEqual(task.compare(a,b,t)['previously_satisfied_lost'],6)
        self.assertEqual(task.compare(b,a,t)['newly_satisfied'],6)
    def test_candidates_and_tasks_not_mutated(self):
        t=deepcopy(task.TASKS[0]);before=deepcopy(t)
        e=task.evaluate('{"assignment":[0,1,0,1,0,1]}',t);snap=deepcopy(e)
        task.feedback(e);task.compare(e,e,t);self.assertEqual(e,snap);self.assertEqual(t,before)
    def test_all_color_permutations_of_solution_accepted(self):
        for t in task.TASKS:
            a=task.solutions(t)[0]
            for p in itertools.permutations(range(3)):
                self.assertTrue(task.evaluate(json.dumps({'assignment':[p[x] for x in a]}),t)['feasible'])
    def test_fixed_task_inventory(self):
        self.assertEqual([t['id'] for t in task.TASKS],['G1','G2','G3','G4'])
        for t in task.TASKS:
            self.assertEqual(len(t['edges']),len({tuple(e) for e in t['edges']}))
            self.assertTrue(all(0<=u<6 and 0<=v<6 and u!=v for u,v in t['edges']))

if __name__=='__main__':unittest.main(verbosity=2)
