from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_dataset  # noqa: E402
import run_baseline  # noqa: E402
import score  # noqa: E402


class DatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases, self.gold = build_dataset.build_records()
        self.case_by_id = {row["case_id"]: row for row in self.cases}

    def test_dataset_has_four_balanced_templates_and_forty_cases(self) -> None:
        self.assertEqual(40, len(self.cases))
        self.assertEqual(40, len(self.gold))
        self.assertEqual(40, len({row["case_id"] for row in self.cases}))
        counts: dict[tuple[str, str, str], int] = defaultdict(int)
        for row in self.gold:
            counts[(row["template_id"], row["scope"], row["condition"])] += 1
        self.assertEqual(4 * 2 * 5, len(counts))
        self.assertTrue(all(value == 1 for value in counts.values()))

    def test_case_ids_and_model_payload_do_not_leak_evaluator_labels(self) -> None:
        for case in self.cases:
            self.assertRegex(case["case_id"], r"^RUE-[A-F0-9]{12}$")
            self.assertEqual({"case_id", "task_content"}, set(case))
            self.assertIs(case["task_content"], run_baseline.model_payload(case))
            payload = json.dumps(case["task_content"], sort_keys=True)
            self.assertNotIn('"condition"', payload)
            self.assertNotIn('"scope"', payload)
            self.assertNotIn('"expected_action"', payload)
            self.assertNotIn('"template_id"', payload)

    def test_rule_text_does_not_expose_trigger_action_pairs(self) -> None:
        for case in self.cases:
            content = case["task_content"]
            atom_ids = {
                row["trigger_id"] for row in content["trigger_examples"]
            } | {row["action_id"] for row in content["action_checks"]}
            for rule in content["rules"]:
                self.assertTrue(all(atom_id not in rule["text"] for atom_id in atom_ids))

    def test_only_links_change_within_matched_condition_groups(self) -> None:
        groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        for gold in self.gold:
            content = copy.deepcopy(self.case_by_id[gold["case_id"]]["task_content"])
            content.pop("links")
            groups[(gold["template_id"], gold["scope"])].append(content)
        self.assertEqual(8, len(groups))
        for values in groups.values():
            self.assertEqual(5, len(values))
            self.assertTrue(all(value == values[0] for value in values[1:]))

    def test_correct_and_shuffled_are_edge_and_byte_matched(self) -> None:
        grouped: dict[tuple[str, str], dict[str, dict[str, object]]] = defaultdict(dict)
        for gold in self.gold:
            grouped[(gold["template_id"], gold["scope"])][gold["condition"]] = self.case_by_id[gold["case_id"]]["task_content"]
        for conditions in grouped.values():
            correct = conditions["correct"]["links"]
            shuffled = conditions["shuffled"]["links"]
            self.assertEqual(3, len(correct))
            self.assertEqual(3, len(shuffled))
            encode = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.assertEqual(len(encode(correct)), len(encode(shuffled)))

    def test_irrelevant_probe_is_single_edge_unmatched_diagnostic(self) -> None:
        for gold in self.gold:
            if gold["condition"] != "irrelevant_probe":
                continue
            content = self.case_by_id[gold["case_id"]]["task_content"]
            self.assertEqual(1, len(content["links"]))
            probe = content["links"][0]
            if gold["scope"] == "irrelevant":
                self.assertEqual(content["observed_event"], probe["trigger_id"])
            else:
                self.assertNotEqual(content["observed_event"], probe["trigger_id"])

    def test_hash_ids_are_stable_without_sequential_condition_cycle(self) -> None:
        expected = {
            (row["template_id"], row["scope"], row["condition"]): row["case_id"]
            for row in self.gold
        }
        recomputed = {
            key: build_dataset.opaque_case_id(*key)
            for key in reversed(tuple(expected))
        }
        self.assertEqual(expected, recomputed)
        ordered_conditions = [row["condition"] for row in self.gold]
        self.assertNotEqual(list(build_dataset.CONDITIONS), ordered_conditions[:5])


class BaselineAndMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases, self.gold_records = build_dataset.build_records()
        self.gold = {row["case_id"]: row for row in self.gold_records}

    def metrics_for(self, baseline: str) -> dict[str, object]:
        records = run_baseline.generate_predictions(self.cases, baseline)
        predictions = {row["case_id"]: row["action"] for row in records}
        return score.score_records(self.cases, self.gold, predictions)

    def test_link_following_baseline_has_expected_contrast(self) -> None:
        metrics = self.metrics_for("link-following")
        self.assertEqual(1.0, metrics["primary_metric"]["value"])
        self.assertEqual(0.5, metrics["secondary_metrics"]["overall_exact_action_accuracy"])
        self.assertEqual(1.0, metrics["secondary_metrics"]["irrelevant_false_action_rate_by_condition"]["irrelevant_probe"])

    def test_link_ignoring_baseline_has_zero_link_contrast(self) -> None:
        metrics = self.metrics_for("link-ignoring")
        self.assertEqual(0.0, metrics["primary_metric"]["value"])
        self.assertEqual(0.5, metrics["secondary_metrics"]["overall_exact_action_accuracy"])
        self.assertEqual(0.0, metrics["secondary_metrics"]["exact_action_accuracy_by_scope"]["relevant"])
        self.assertEqual(1.0, metrics["secondary_metrics"]["exact_action_accuracy_by_scope"]["irrelevant"])

    def test_committed_generated_outputs_are_current(self) -> None:
        for baseline in ("link-following", "link-ignoring"):
            expected_predictions = run_baseline.generate_predictions(self.cases, baseline)
            prediction_path = ROOT / "results" / f"{baseline}.predictions.jsonl"
            actual_predictions = run_baseline.read_jsonl(prediction_path)
            self.assertEqual(expected_predictions, actual_predictions)
            prediction_map = {row["case_id"]: row["action"] for row in expected_predictions}
            expected_metrics = score.score_records(self.cases, self.gold, prediction_map)
            metrics_path = ROOT / "results" / f"{baseline}.metrics.json"
            actual_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            self.assertEqual(expected_metrics, actual_metrics)


class StrictValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases, self.gold = build_dataset.build_records()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cases_path = self.root / "cases.jsonl"
        self.gold_path = self.root / "gold.jsonl"
        self.cases_path.write_text(build_dataset.jsonl_text(self.cases), encoding="utf-8")
        self.gold_path.write_text(build_dataset.jsonl_text(self.gold), encoding="utf-8")
        self.valid = run_baseline.generate_predictions(self.cases, "link-following")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_predictions(self, records: list[dict[str, str]]) -> Path:
        path = self.root / "predictions.jsonl"
        path.write_text(build_dataset.jsonl_text(records), encoding="utf-8")
        return path

    def test_duplicate_prediction_is_rejected(self) -> None:
        path = self.write_predictions(self.valid + [self.valid[0]])
        with self.assertRaisesRegex(ValueError, "duplicate prediction case_id"):
            score.load_inputs(self.cases_path, self.gold_path, path)

    def test_missing_prediction_is_rejected(self) -> None:
        path = self.write_predictions(self.valid[:-1])
        with self.assertRaisesRegex(ValueError, "missing predictions case IDs"):
            score.load_inputs(self.cases_path, self.gold_path, path)

    def test_unknown_case_is_rejected(self) -> None:
        records = copy.deepcopy(self.valid)
        records[-1]["case_id"] = "RUE-FFFFFFFFFFFF"
        path = self.write_predictions(records)
        with self.assertRaisesRegex(ValueError, "unknown predictions case IDs"):
            score.load_inputs(self.cases_path, self.gold_path, path)

    def test_unknown_action_is_rejected(self) -> None:
        records = copy.deepcopy(self.valid)
        records[0]["action"] = "INVENTED_ACTION"
        path = self.write_predictions(records)
        with self.assertRaisesRegex(ValueError, "unknown action"):
            score.load_inputs(self.cases_path, self.gold_path, path)

    def test_extra_prediction_field_is_rejected(self) -> None:
        records = copy.deepcopy(self.valid)
        records[0]["confidence"] = 0.9  # type: ignore[assignment]
        path = self.write_predictions(records)
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            score.load_inputs(self.cases_path, self.gold_path, path)


if __name__ == "__main__":
    unittest.main()
