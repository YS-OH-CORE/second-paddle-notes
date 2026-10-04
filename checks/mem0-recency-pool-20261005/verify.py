# SPDX-License-Identifier: Apache-2.0
"""Offline scoring-boundary experiment. Zero × Youngseok Oh.

Use --source with the exact scoring.py from Kylinny/mem0 commit 01fcd26a.
No package installation, embeddings, network calls, or model invocation occurs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone
import unittest
from fixed_reference import rank

SOURCE_COMMIT = '01fcd26ac6ab29d761e4cc8896f3588e28cf6d32'
SOURCE_BLOB = 'e1f4df5e68eec57bc03e46de451c00016a3d3d5e'
AS_OF = datetime(2026, 10, 5, tzinfo=timezone.utc)
PAIR = [
    {'id': 'old', 'score': .650003, 'payload': {'created_at': '2026-08-01T00:00:00Z'}},
    {'id': 'new', 'score': .646012, 'payload': {'created_at': '2026-09-01T00:00:00Z'}},
]
ARCHIVE = {'id': 'archive', 'score': .31, 'payload': {'created_at': '2020-01-01T00:00:00Z'}}
scoring = None


def candidate(rows, bm25=None, entities=None, threshold=.3, top_k=2, weight=.1):
    return scoring.score_and_rank(rows, bm25 or {}, entities or {}, threshold, top_k, True, weight)


def fixed(rows, bm25=None, entities=None, threshold=.3, top_k=2, **kwargs):
    return rank(scoring, rows, bm25 or {}, entities or {}, threshold, top_k,
                as_of=AS_OF, explain=True, **kwargs)


def ids(rows):
    return [row['id'] for row in rows]


def matrix():
    observations = []
    for signal in ('semantic', 'bm25', 'entity', 'both'):
        bm25 = {'old': .2, 'new': .2} if signal in ('bm25', 'both') else {}
        entities = {'old': .1, 'new': .1} if signal in ('entity', 'both') else {}
        for archive_date in ('2020-01-01T00:00:00Z', '2023-01-01T00:00:00Z'):
            archive = copy.deepcopy(ARCHIVE)
            archive['payload']['created_at'] = archive_date
            for perm in itertools.permutations(PAIR + [archive]):
                ordered_pair = [r for r in perm if r['id'] != 'archive']
                before = candidate(ordered_pair, bm25, entities)
                after = candidate(list(perm), bm25, entities)
                fbefore = fixed(ordered_pair, bm25, entities)
                fafter = fixed(list(perm), bm25, entities)
                observations.append({
                    'signal': signal, 'archive_date': archive_date, 'input_order': ids(perm),
                    'candidate_before': ids(before), 'candidate_after': ids(after),
                    'reference_before': ids(fbefore), 'reference_after': ids(fafter),
                    'candidate_pair_reversed': ids(before) == ['new', 'old'] and ids(after) == ['old', 'new'],
                    'reference_pair_scores_unchanged': fbefore == fafter,
                    'archive_outside_returned_top_two': 'archive' not in ids(after) + ids(fafter),
                })
    return observations


class Controls(unittest.TestCase):
    def test_actual_candidate_reversal(self):
        self.assertEqual(ids(candidate(PAIR)), ['new', 'old'])
        self.assertEqual(ids(candidate(PAIR + [ARCHIVE])), ['old', 'new'])

    def test_fixed_reference_pair_and_scores(self):
        self.assertEqual(ids(fixed(PAIR)), ['new', 'old'])
        self.assertEqual(fixed(PAIR), fixed(PAIR + [ARCHIVE]))

    def test_feature_off_negative_control(self):
        self.assertEqual(ids(candidate(PAIR, weight=0)), ['old', 'new'])
        self.assertEqual(candidate(PAIR, weight=0), candidate(PAIR + [ARCHIVE], weight=0))

    def test_below_threshold_archive_does_not_shift_original(self):
        row = {**ARCHIVE, 'score': .299}
        self.assertEqual(candidate(PAIR), candidate(PAIR + [row]))

    def test_48_permutations_and_fixed_hybrid_signals(self):
        rows = matrix()
        self.assertEqual(len(rows), 48)
        self.assertTrue(all(r['candidate_pair_reversed'] for r in rows))
        self.assertTrue(all(r['reference_pair_scores_unchanged'] for r in rows))
        self.assertTrue(all(r['archive_outside_returned_top_two'] for r in rows))

    def test_no_input_mutation(self):
        rows = copy.deepcopy(PAIR + [ARCHIVE]); before = copy.deepcopy(rows)
        candidate(rows); fixed(rows)
        self.assertEqual(rows, before)

    def test_updated_at_precedence(self):
        first = copy.deepcopy(PAIR)
        first[0]['payload']['updated_at'] = '2026-10-01T00:00:00Z'
        equivalent = copy.deepcopy(first)
        equivalent[0]['payload'] = {'created_at': '2026-10-01T00:00:00Z'}
        self.assertEqual([r['score'] for r in fixed(first)], [r['score'] for r in fixed(equivalent)])

    def test_timezone_equivalence(self):
        local = copy.deepcopy(PAIR)
        local[1]['payload']['created_at'] = '2026-09-01T09:00:00+09:00'
        self.assertEqual([r['score'] for r in fixed(PAIR)], [r['score'] for r in fixed(local)])

    def test_missing_dates_do_not_activate_signal(self):
        rows = [{**r, 'payload': {}} for r in PAIR]
        self.assertEqual(fixed(rows), candidate(rows, weight=0))

    def test_invalid_updated_at_uses_created_at(self):
        rows = copy.deepcopy(PAIR); rows[0]['payload']['updated_at'] = 'invalid'
        self.assertEqual([r['score'] for r in fixed(PAIR)], [r['score'] for r in fixed(rows)])

    def test_default_disable_exact_compatibility(self):
        self.assertEqual(fixed(PAIR, weight=0), candidate(PAIR, weight=0))
        self.assertEqual(fixed(PAIR, weight=-1), candidate(PAIR, weight=-1))

    def test_more_recent_is_not_always_winner(self):
        rows = [{**PAIR[0], 'score': .95}, {**PAIR[1], 'score': .31}]
        self.assertEqual(ids(fixed(rows)), ['old', 'new'])

    def test_equal_dates_preserve_semantic_order(self):
        rows = copy.deepcopy(PAIR); rows[1]['payload'] = copy.deepcopy(rows[0]['payload'])
        self.assertEqual(ids(fixed(rows)), ['old', 'new'])

    def test_future_dates_bounded(self):
        rows = [{**PAIR[0], 'payload': {'created_at': '2027-01-01T00:00:00Z'}}]
        self.assertEqual(fixed(rows)[0]['score_details']['recency_score'], 1.0)

    def test_cannot_recover_missing_candidate(self):
        self.assertEqual(ids(fixed([PAIR[0]])), ['old'])
        self.assertNotIn('new', ids(fixed([PAIR[0]])))

    def test_half_life_is_policy_not_tuned_accuracy(self):
        for days in (30, 90, 180, 365, 730, 3650):
            self.assertEqual(fixed(PAIR, half_life_days=days), fixed(PAIR + [ARCHIVE], half_life_days=days))

    def test_bad_reference_parameters_rejected(self):
        for weight in (float('nan'), float('inf'), True):
            with self.assertRaises(ValueError): fixed(PAIR, weight=weight)
        for days in (0, -1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError): fixed(PAIR, half_life_days=days)
        with self.assertRaises(ValueError):
            rank(scoring, PAIR, {}, {}, .3, 2, as_of=datetime(2026, 10, 5))

    def test_empty_and_zero_result_limit(self):
        self.assertEqual(fixed([]), [])
        self.assertEqual(fixed(PAIR, top_k=0), [])


def main():
    global scoring
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob != SOURCE_BLOB:
        parser.error('Source bytes do not match the pinned, reviewed scoring module')
    spec = importlib.util.spec_from_file_location('pinned_mem0_candidate', args.source)
    scoring = importlib.util.module_from_spec(spec); spec.loader.exec_module(scoring)
    results = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    examples = {label: {'pair': func(PAIR), 'with_archive': func(PAIR + [ARCHIVE])}
                for label, func in [('candidate_recency', candidate), ('fixed_reference', fixed)]}
    payload = {
        'schema': 'zero-temporal-pool-boundary/1', 'source_commit': SOURCE_COMMIT,
        'source_git_blob': blob, 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'platform': platform.platform(), 'python': sys.version,
        'as_of': AS_OF.isoformat(), 'illustrative_half_life_days': 180,
        'control_test_count': results.testsRun, 'failures': len(results.failures),
        'errors': len(results.errors), 'skipped': len(results.skipped),
        'examples': examples, 'matrix': matrix(),
        'scope': 'Actual unmodified candidate scoring function plus our discussion-only wrapper, with synthetic candidates. Not Memory.search, embeddings, LLM answers, end-to-end benchmark, main-branch bug, human review, or upstream adoption.',
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if results.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())
