"""Software checks, not model experiments or independent research replication."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import audit
import demo


def case(case_id, actions, available=None, weight=1, request='same decision'):
    return {'id': case_id, 'request': request, 'available': available,
            'acceptable_actions': list(actions), 'weight': weight}


def document(rows):
    return {'schema': audit.SCHEMA, 'scope': 'Synthetic test: complete declared immediate input only.',
            'expected_case_ids': [r['id'] for r in rows], 'cases': rows}


class AuditChecks(unittest.TestCase):
    def test_disjoint_answers_same_input(self):
        r = audit.audit(document([case('a', ['A']), case('b', ['B'])]))
        self.assertEqual(r['conflicting_groups'], 1)
        self.assertEqual(r['finite_full_coverage_ceiling']['numerator'], 1)
        self.assertEqual(r['finite_full_coverage_ceiling']['denominator'], 2)

    def test_shared_acceptable_action_is_not_conflict(self):
        r = audit.audit(document([case('a', ['A', 'ask']), case('b', ['B', 'ask'])]))
        self.assertEqual(r['conflicting_groups'], 0)
        self.assertEqual(r['compatible_shared_view_groups'], 1)

    def test_joint_conflict_even_when_every_pair_overlaps(self):
        sets = [('A', 'B'), ('B', 'C'), ('A', 'C')]
        self.assertTrue(all(set(a) & set(b) for a, b in itertools.combinations(sets, 2)))
        r = audit.audit(document([case(str(i), a) for i, a in enumerate(sets)]))
        self.assertEqual(r['conflicting_groups'], 1)
        self.assertEqual(r['finite_full_coverage_ceiling']['best_covered_weight'], 2)
        self.assertEqual(len(r['witnesses'][0]['case_ids']), 3)

    def test_side_information_disambiguates(self):
        rows = [case('a', ['A'], {'state': 'left'}), case('b', ['B'], {'state': 'right'})]
        self.assertEqual(audit.audit(document(rows))['distinct_available_inputs'], 2)
        self.assertEqual(audit.audit(document(rows))['conflicting_groups'], 0)

    def test_different_request_is_different_input(self):
        rows = [case('a', ['A'], request='one'), case('b', ['B'], request='two')]
        self.assertEqual(audit.audit(document(rows))['conflicting_groups'], 0)

    def test_weights_are_exact_not_model_accuracy(self):
        rows = [case('a', ['A'], weight=7), case('b', ['B'], weight=3)]
        r = audit.audit(document(rows))['finite_full_coverage_ceiling']
        self.assertEqual((r['numerator'], r['denominator']), (7, 10))

    def test_all_small_set_systems_against_enumerated_policies(self):
        actions = ('A', 'B', 'C')
        choices = [set(s) for n in range(1, 4) for s in itertools.combinations(actions, n)]
        partitions = [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (0, 1, 2)]
        comparisons = 0
        for allowed in itertools.product(choices, repeat=3):
            for partition in partitions:
                states = sorted(set(partition))
                for weights in ((1, 1, 1), (2, 1, 3)):
                    # Independent oracle enumerates every deterministic policy on the finite inputs.
                    scores = []
                    for outputs in itertools.product(actions, repeat=len(states)):
                        policy = dict(zip(states, outputs))
                        scores.append(sum(w for a, s, w in zip(allowed, partition, weights) if policy[s] in a))
                    rows = [case(str(i), sorted(a), s, w) for i, (a, s, w) in enumerate(zip(allowed, partition, weights))]
                    result = audit.audit(document(rows))
                    bound = result['finite_full_coverage_ceiling']
                    self.assertEqual(bound['best_covered_weight'], max(scores))
                    self.assertEqual(Fraction(bound['numerator'], bound['denominator']), Fraction(max(scores), sum(weights)))
                    self.assertEqual(result['conflicting_groups'] == 0, max(scores) == sum(weights))
                    comparisons += 1
        self.assertEqual(comparisons, 3430)

    def test_dict_order_ignored_but_string_and_list_order_retained(self):
        rows = [case('a', ['A'], {'x': 1, 'y': 2}), case('b', ['B'], {'y': 2, 'x': 1})]
        self.assertEqual(audit.audit(document(rows))['conflicting_groups'], 1)
        for a, b in (([0, 1], [1, 0]), ('a b', 'ab'), ('x\n', 'x')):
            self.assertEqual(audit.audit(document([case('a', ['A'], a), case('b', ['B'], b)]))['conflicting_groups'], 0)

    def test_bool_and_integer_observations_not_merged(self):
        r = audit.audit(document([case('a', ['A'], True), case('b', ['B'], 1)]))
        self.assertEqual(r['distinct_available_inputs'], 2)

    def test_case_ids_do_not_leak_into_available_input(self):
        d = document([case('secret-answer-A', ['A']), case('secret-answer-B', ['B'])])
        self.assertEqual(audit.audit(d)['conflicting_groups'], 1)

    def test_labels_or_extra_fields_cannot_be_silently_misspelled(self):
        d = document([case('a', ['A'])]); d['cases'][0]['requestt'] = 'typo'
        with self.assertRaises(ValueError): audit.audit(d)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError): audit.audit(document([]))

    def test_missing_expected_case_rejected(self):
        d = document([case('a', ['A']), case('b', ['B'])]); d['cases'].pop()
        with self.assertRaises(ValueError): audit.audit(d)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError): audit.audit(document([case('a', ['A']), case('a', ['B'])]))

    def test_unexpected_replacement_id_rejected(self):
        d = document([case('a', ['A']), case('b', ['B'])]); d['cases'][1]['id'] = 'other'
        with self.assertRaises(ValueError): audit.audit(d)

    def test_empty_or_duplicate_acceptable_actions_rejected(self):
        for actions in ([], ['A', 'A'], ['']):
            with self.assertRaises(ValueError): audit.audit(document([case('a', actions)]))

    def test_invalid_weights_rejected(self):
        for weight in (0, -1, True, 0.5, '1', 1000001):
            with self.assertRaises(ValueError): audit.audit(document([case('a', ['A'], weight=weight)]))

    def test_float_observations_rejected_instead_of_rounded(self):
        with self.assertRaises(ValueError): audit.audit(document([case('a', ['A'], 0.1)]))

    def test_duplicate_json_keys_rejected(self):
        raw = b'{"schema":"handoff-audit/0.1","schema":"handoff-audit/0.1"}'
        with self.assertRaises(ValueError): audit.load_bytes(raw)

    def test_nonfinite_json_rejected(self):
        raw = json.dumps(document([case('a', ['A'], None)])).replace('null', 'NaN').encode()
        with self.assertRaises(ValueError): audit.load_bytes(raw)

    def test_unreadable_or_excessive_input_rejected(self):
        for data in (b'\xff', b'{' * 100, b' ' * (audit.MAX_BYTES + 1)):
            with self.assertRaises((ValueError, UnicodeError)): audit.load_bytes(data)

    def test_too_deep_available_input_rejected(self):
        value = None
        for _ in range(42): value = [value]
        with self.assertRaises(ValueError): audit.audit(document([case('a', ['A'], value)]))

    def test_input_is_not_mutated(self):
        d = document([case('a', ['A', 'B'], {'x': ['y']}), case('b', ['B'])]); before = deepcopy(d)
        audit.audit(d); self.assertEqual(d, before)

    def test_raw_available_content_not_in_default_report(self):
        d = document([case('a', ['A'], {'text': 'PRIVATE-CONTENT'}), case('b', ['B'], {'text': 'PRIVATE-CONTENT'})])
        self.assertNotIn('PRIVATE-CONTENT', json.dumps(audit.audit(d)))

    def test_real_helper_demo(self):
        result = demo.run()['reports']
        self.assertEqual(result['v13_messages_only']['conflicting_groups'], 1)
        self.assertEqual(result['v13_messages_only']['witnesses'][0]['case_ids'], ['AA', 'AB', 'BB'])
        self.assertEqual(result['v13_messages_only']['finite_full_coverage_ceiling']['denominator'], 4)
        for name in ('v15_identity', 'v13_with_sidecar', 'v13_clarification_allowed'):
            self.assertEqual(result[name]['conflicting_groups'], 0)
        self.assertEqual(result['v13_clarification_allowed']['distinct_available_inputs'], 2)
        self.assertEqual(result['v13_with_sidecar']['distinct_available_inputs'], 4)

    def test_published_demo_scores_recompute(self):
        path = Path(__file__).resolve().parent / 'DEMO_RESULTS.json'
        self.assertEqual(demo.run(), json.loads(path.read_text()))

    def test_cli_conflict_success_invalid_and_no_overwrite(self):
        script = Path(audit.__file__).resolve()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder); src = folder / 'in.json'; out = folder / 'out.json'
            for rows, expected_exit in (([case('a', ['A']), case('b', ['B'])], 1), ([case('a', ['A'])], 0)):
                src.write_text(json.dumps(document(rows)))
                r = subprocess.run([sys.executable, '-B', str(script), str(src)], capture_output=True, text=True, timeout=10)
                self.assertEqual(r.returncode, expected_exit)
                self.assertIn('input_file_sha256', json.loads(r.stdout))
            src.write_text('{}')
            r = subprocess.run([sys.executable, '-B', str(script), str(src)], capture_output=True, timeout=10)
            self.assertEqual(r.returncode, 2)
            src.write_text(json.dumps(document([case('a', ['A'])]))); out.write_bytes(b'keep me')
            r = subprocess.run([sys.executable, '-B', str(script), str(src), '--out', str(out)], capture_output=True, timeout=10)
            self.assertEqual(r.returncode, 2); self.assertEqual(out.read_bytes(), b'keep me')


if __name__ == '__main__':
    unittest.main(verbosity=2)
