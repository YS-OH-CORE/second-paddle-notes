"""Instrument checks only. No provider, model, GPU, or network is involved."""
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import pilot as p


class InstrumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests, cls.gold = p.build()
        cls.labels = {r['request_id']: r for r in cls.gold}
        cls.by_id = {r['request_id']: r for r in cls.requests}
        cls.outputs = p.fixture_outputs(cls.requests, 'oracle')

    def test_count_not_independent_trials(self):
        self.assertEqual(len(self.requests), 576)
        self.assertEqual(len({g['pair_key'] for g in self.gold}), 288)
        self.assertEqual(len({g['domain'] for g in self.gold}), 4)

    def test_deterministic_generation(self):
        self.assertEqual((self.requests, self.gold), p.build())

    def test_unique_matching_inventories(self):
        self.assertEqual(len(self.by_id), len(self.requests))
        self.assertEqual(set(self.by_id), set(self.labels))

    def test_no_gold_or_condition_metadata_in_requests(self):
        for r in self.requests:
            self.assertEqual(set(r), {'request_id', 'payload'})
            self.assertEqual(set(r['payload']), {'instruction','setting','history','actions','query'})
            text = p.canonical(r)
            for forbidden in ('expected_action','pair_key','user_update','user_reaffirm','assistant_proposal','probe'):
                self.assertNotIn(forbidden, text)

    def test_equal_length_opaque_destinations(self):
        for r in self.requests:
            codes = [a['action_id'] for a in r['payload']['actions']]
            self.assertEqual(len(set(codes)), 3)
            self.assertEqual({len(c) for c in codes}, {8})

    def test_balanced_answer_positions(self):
        position = defaultdict(Counter)
        for r in self.requests:
            g = self.labels[r['request_id']]
            key = (g['domain'],g['condition'],g['scope'],g['probe'],g['wording'])
            codes = [a['action_id'] for a in r['payload']['actions']]
            position[key][codes.index(g['expected_action'])] += 1
        self.assertTrue(all(count == Counter({0:2,1:2,2:2}) for count in position.values()))

    def test_recall_choice_context_equal_except_query(self):
        pairs = defaultdict(list)
        for r in self.requests:
            pairs[self.labels[r['request_id']]['pair_key']].append(r)
        for pair in pairs.values():
            self.assertEqual(len(pair), 2)
            a,b = [deepcopy(r['payload']) for r in pair]
            self.assertNotEqual(a.pop('query'), b.pop('query'))
            self.assertEqual(a,b)

    def test_primary_condition_changes_one_destination_only(self):
        groups = defaultdict(dict)
        for r in self.requests:
            g = self.labels[r['request_id']]
            key = (g['domain'],g['counterbalance'],g['wording'],g['scope'],g['probe'])
            groups[key][g['condition']] = r
        for group in groups.values():
            a = deepcopy(group['user_update']['payload'])
            b = deepcopy(group['user_reaffirm']['payload'])
            self.assertEqual(len(p.canonical(a).encode()),len(p.canonical(b).encode()))
            ra = a['history'][1]['assignments'][0]
            rb = b['history'][1]['assignments'][0]
            self.assertNotEqual(ra['action_id'],rb['action_id'])
            ra['action_id'] = rb['action_id']
            self.assertEqual(a,b)

    def test_gold_follows_current_authorized_content_not_fixed_old_answer(self):
        for r in self.requests:
            g = self.labels[r['request_id']]
            self.assertEqual(p.resolve(r['payload'],'oracle'),g['expected_action'])
            if g['scope']=='touched' and g['condition']=='user_update':
                self.assertNotEqual(g['expected_action'],g['old_action'])

    def test_author_control_is_not_approved_update(self):
        cases = [g for g in self.gold if g['condition']=='assistant_proposal' and g['scope']=='touched']
        self.assertTrue(cases)
        self.assertTrue(all(g['expected_action']==g['old_action'] for g in cases))

    def test_unaffected_scope_gold_constant(self):
        self.assertTrue(all(g['expected_action']==g['unaffected_action'] for g in self.gold if g['scope']=='untouched'))

    def test_oracle_score_has_no_recall_choice_gap(self):
        result=p.score(self.requests,self.gold,self.outputs)
        self.assertEqual(result['accuracy'],{'recall':1.0,'choice':1.0})
        self.assertEqual(result['paired_recall_correct_choice_wrong'],0)
        self.assertEqual(result['scope_adjusted_update_sensitivity'],{'recall':1.0,'choice':1.0})

    def test_reciting_program_is_distinguished_from_oracle(self):
        result=p.score(self.requests,self.gold,p.fixture_outputs(self.requests,'recall_only'))
        self.assertEqual(result['paired_recall_correct_choice_wrong'],48)
        self.assertEqual(result['scope_adjusted_update_sensitivity'],{'recall':1.0,'choice':0.0})
        self.assertAlmostEqual(result['recall_minus_choice_accuracy'],1/6)
        for cell in result['cells']:
            if cell['condition']=='user_update' and cell['scope']=='touched':
                self.assertEqual(cell['accuracy'],1.0 if cell['probe']=='recall' else 0.0)

    def test_stale_program_is_not_mislabeled_as_recall_choice_gap(self):
        result=p.score(self.requests,self.gold,p.fixture_outputs(self.requests,'stale'))
        self.assertEqual(result['paired_recall_correct_choice_wrong'],0)
        self.assertEqual(result['scope_adjusted_update_sensitivity'],{'recall':0.0,'choice':0.0})
        self.assertAlmostEqual(result['accuracy']['choice'],5/6)

    def test_overgeneralized_latest_action_is_not_scored_as_scope_specific(self):
        result=p.score(self.requests,self.gold,p.fixture_outputs(self.requests,'blind_latest'))
        self.assertEqual(result['scope_adjusted_update_sensitivity'],{'recall':0.0,'choice':0.0})

    def test_programs_do_not_mutate_input(self):
        before=deepcopy(self.requests)
        for mode in ('oracle','stale','recall_only','blind_latest'):
            p.fixture_outputs(self.requests,mode)
        self.assertEqual(before,self.requests)

    def test_prediction_order_does_not_change_metrics(self):
        self.assertEqual(p.score(self.requests,self.gold,self.outputs),p.score(self.requests,self.gold,list(reversed(self.outputs))))

    def test_missing_output_is_not_silently_dropped(self):
        with self.assertRaises(ValueError):p.score(self.requests,self.gold,self.outputs[:-1])

    def test_extra_output_is_rejected(self):
        with self.assertRaises(ValueError):p.score(self.requests,self.gold,self.outputs+[{'request_id':'unknown','raw':'{}'}])

    def test_duplicate_output_is_rejected(self):
        with self.assertRaises(ValueError):p.score(self.requests,self.gold,self.outputs+[self.outputs[0]])

    def test_empty_run_is_not_a_success(self):
        with self.assertRaises(ValueError):p.score([],[],[])

    def test_format_failure_counts_and_is_not_repaired_by_explanation(self):
        outputs=deepcopy(self.outputs);outputs[0]['raw']='The answer is '+outputs[0]['raw']
        result=p.score(self.requests,self.gold,outputs)
        self.assertEqual(result['invalid_outputs'],1)
        self.assertLess(sum(result['accuracy'].values()),2)

    def test_duplicate_json_keys_extra_fields_and_unlisted_codes_rejected(self):
        for text in ('{"action_id":"D0000000","action_id":"D1111111"}',
                     '{"action_id":"D0000000","explanation":"trust me"}',
                     '{"action_id":"absent"}', '{"action_id":null}',
                     '{"action_id":NaN}', '```json\n{"action_id":"D0000000"}\n```'):
            with self.subTest(text=text):self.assertIsNone(p.parse_choice(text,{'D0000000','D1111111'}))

    def test_pair_gold_mismatch_rejected(self):
        gold=deepcopy(self.gold)
        first=gold[0]
        first['expected_action']=next(a['action_id'] for a in self.by_id[first['request_id']]['payload']['actions'] if a['action_id']!=first['expected_action'])
        with self.assertRaises(ValueError):p.score(self.requests,gold,self.outputs)

    def test_existing_artifacts_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'rows.jsonl'
            p.dump_jsonl(target, [{'a':1}])
            before=target.read_bytes()
            with self.assertRaises(FileExistsError):p.dump_jsonl(target,[{'a':2}])
            self.assertEqual(before,target.read_bytes())


if __name__=='__main__':unittest.main(verbosity=2)
