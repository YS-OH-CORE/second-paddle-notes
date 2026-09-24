"""Negative controls for the offline evidence calculator; no model execution."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import verify_evidence as v

HERE = Path(__file__).resolve().parent

class EvidenceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name, sha = v.ARCHIVES['order']
        cls.data = v.read_archive(HERE / name, sha)
        cls.fixture = v.literals(cls.data['pilot.py'])
        cls.rows = [json.loads(x) for x in cls.data['inference/raw.jsonl'].decode().splitlines()]

    def check_rows(self, rows):
        return v.check_rows(rows, self.fixture['CASES'], self.fixture['SYSTEM'], 'order')

    def test_original_archives(self):
        result = v.verify(HERE)
        self.assertEqual(result['recorded_forward_passes'], 168)
        self.assertEqual(result['new_forward_passes'], 0)
        for view in v.VIEWS:
            self.assertEqual(result['order']['summary'][view]['correct'], 31)

    def test_missing_row(self):
        with self.assertRaisesRegex(ValueError, 'row count'):
            self.check_rows(deepcopy(self.rows[:-1]))

    def test_duplicate_cell(self):
        rows = deepcopy(self.rows)
        rows[-1] = deepcopy(rows[0])
        rows[-1]['ordinal'] = len(rows) - 1
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.check_rows(rows)

    def test_changed_correctness(self):
        rows = deepcopy(self.rows)
        rows[0]['correct'] = not rows[0]['correct']
        with self.assertRaisesRegex(ValueError, 'correctness'):
            self.check_rows(rows)

    def test_bad_semantic_mapping(self):
        rows = deepcopy(self.rows)
        rows[0]['selected_semantic_id'] = (rows[0]['selected_semantic_id'] + 1) % 3
        with self.assertRaisesRegex(ValueError, 'mapping'):
            self.check_rows(rows)

    def test_modified_archive(self):
        name, sha = v.ARCHIVES['order']
        with tempfile.TemporaryDirectory(prefix='evidence-check-') as d:
            p = Path(d) / name
            p.write_bytes((HERE / name).read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                v.read_archive(p, sha)

if __name__ == '__main__':
    unittest.main()
