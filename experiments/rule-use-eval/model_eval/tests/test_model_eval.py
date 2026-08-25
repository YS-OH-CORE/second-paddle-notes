from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL_EVAL = HERE.parent
sys.path.insert(0, str(MODEL_EVAL))

from build_bundle import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_GOLD,
    build_records,
    create_bundle_texts,
    reject_public_semantic_reuse,
    semantic_bundle_fingerprint,
    validate_hidden_protocol_default,
)
from common import jsonl_text, read_jsonl  # noqa: E402
from make_mock_responses import make_records  # noqa: E402
from parse_responses import parse_raw_response, parse_records  # noqa: E402
from run_public_smoke_dry_run import generate  # noqa: E402
from score_model_eval import cluster_bootstrap, score_records  # noqa: E402


def recursively_find_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(recursively_find_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursively_find_keys(child))
    return keys


def make_hidden_source(template_count: int = 24) -> tuple[list[dict], list[dict]]:
    cases: list[dict] = []
    gold: list[dict] = []
    for number in range(template_count):
        prefix = f"H{number:03d}"
        template_id = f"hidden-template-{number:03d}"
        rules = [
            {"rule_id": f"{prefix}R{index}", "text": f"Independent hidden rule {number}-{index}."}
            for index in range(3)
        ]
        triggers = [
            {"trigger_id": f"{prefix}T{index}", "example": f"Independent hidden trigger {number}-{index}."}
            for index in range(3)
        ] + [{"trigger_id": f"{prefix}TX", "example": f"Independent irrelevant event {number}."}]
        actions = [
            {"action_id": f"{prefix}A{index}", "check": f"Independent hidden check {number}-{index}."}
            for index in range(3)
        ] + [{"action_id": "NO_ACTION", "check": "No task action is taken"}]
        correct_links = [
            {
                "direction": "rule_to_trigger_to_action",
                "rule_id": f"{prefix}R{index}",
                "trigger_id": f"{prefix}T{index}",
                "action_id": f"{prefix}A{index}",
            }
            for index in range(3)
        ]
        shuffled_links = [
            {
                "direction": "rule_to_trigger_to_action",
                "rule_id": f"{prefix}R{index}",
                "trigger_id": f"{prefix}T{index}",
                "action_id": f"{prefix}A{(index + 1) % 3}",
            }
            for index in range(3)
        ]
        for scope, event, expected in (
            ("relevant", f"{prefix}T0", f"{prefix}A0"),
            ("irrelevant", f"{prefix}TX", "NO_ACTION"),
        ):
            common = {
                "instruction": "Choose exactly one registered action.",
                "observed_event": event,
                "rules": rules,
                "trigger_examples": triggers,
                "action_checks": actions,
                "verification_statement": "Return one listed action identifier.",
            }
            for condition, links in (("correct", correct_links), ("shuffled", shuffled_links)):
                case_id = f"HIDDEN-{number:03d}-{scope}-{condition}"
                cases.append({"case_id": case_id, "task_content": {**copy.deepcopy(common), "links": copy.deepcopy(links)}})
                gold.append(
                    {
                        "case_id": case_id,
                        "template_id": template_id,
                        "scope": scope,
                        "condition": condition,
                        "expected_action": expected,
                    }
                )
    return cases, gold


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = read_jsonl(DEFAULT_CASES, "case")
        cls.gold = read_jsonl(DEFAULT_GOLD, "gold")

    def test_runner_bundle_has_only_opaque_identity_and_no_evaluator_metadata(self) -> None:
        requests, mapping = build_records(self.cases, self.gold, repeats=2, order_seed=20260825)
        self.assertEqual(len(requests), 32)
        self.assertEqual(len(mapping), 32)
        banned = {
            "case_id",
            "source_case_id",
            "template_id",
            "scope",
            "condition",
            "expected_action",
            "repeat_index",
            "gold",
        }
        source_ids = {row["case_id"] for row in self.cases}
        serialized = "\n".join(json.dumps(row, sort_keys=True) for row in requests)
        for row in requests:
            self.assertRegex(row["trial_id"], r"^TRIAL-[A-F0-9]{20}$")
            self.assertTrue(banned.isdisjoint(recursively_find_keys(row)))
        self.assertTrue(all(case_id not in serialized for case_id in source_ids))
        self.assertTrue(all(set(row) >= banned - {"case_id", "gold"} for row in mapping))

    def test_seeded_order_and_ids_are_deterministic(self) -> None:
        first = build_records(self.cases, self.gold, repeats=2, order_seed=71)
        second = build_records(self.cases, self.gold, repeats=2, order_seed=71)
        other = build_records(self.cases, self.gold, repeats=2, order_seed=72)
        self.assertEqual(first, second)
        self.assertNotEqual([row["trial_id"] for row in first[0]], [row["trial_id"] for row in other[0]])
        self.assertEqual(
            sorted((row["template_id"], row["scope"], row["condition"], row["repeat_index"]) for row in first[1]),
            sorted((row["template_id"], row["scope"], row["condition"], row["repeat_index"]) for row in other[1]),
        )

    def test_nested_evaluator_metadata_in_task_content_is_rejected_at_runtime(self) -> None:
        cases = copy.deepcopy(self.cases)
        selected_id = next(row["case_id"] for row in self.gold if row["condition"] == "correct")
        selected = next(row for row in cases if row["case_id"] == selected_id)
        selected["task_content"]["nested"] = [{"condition": "correct"}]
        with self.assertRaisesRegex(ValueError, "evaluator metadata is forbidden"):
            build_records(cases, self.gold, repeats=1, order_seed=20260825)

    def test_hidden_candidate_fails_closed_for_public_sources_and_default_seed(self) -> None:
        with self.assertRaisesRegex(ValueError, "semantically equals"):
            create_bundle_texts(
                DEFAULT_CASES,
                DEFAULT_GOLD,
                repeats=1,
                order_seed=20260825,
                request_name="requests.jsonl",
                mapping_name="mapping.jsonl",
                study_kind="preregistered_hidden_candidate",
            )

    def test_hidden_candidate_rejects_low_width_seed_for_distinct_source_files(self) -> None:
        cases, gold = make_hidden_source()
        with tempfile.TemporaryDirectory() as temp:
            cases_path = Path(temp) / "cases.jsonl"
            gold_path = Path(temp) / "gold.jsonl"
            cases_path.write_text(jsonl_text(cases), encoding="utf-8")
            gold_path.write_text(jsonl_text(gold), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at least 128 bits wide"):
                create_bundle_texts(
                    cases_path,
                    gold_path,
                    repeats=1,
                    order_seed=20260825,
                    request_name="requests.jsonl",
                    mapping_name="mapping.jsonl",
                    study_kind="preregistered_hidden_candidate",
                )

    def test_public_semantics_are_detected_despite_whitespace_key_and_record_order(self) -> None:
        transformed_cases = [dict(reversed(list(row.items()))) for row in reversed(self.cases)]
        transformed_gold = [dict(reversed(list(row.items()))) for row in reversed(self.gold)]
        self.assertEqual(semantic_bundle_fingerprint(self.cases), semantic_bundle_fingerprint(transformed_cases))
        self.assertEqual(semantic_bundle_fingerprint(self.gold), semantic_bundle_fingerprint(transformed_gold))
        with self.assertRaisesRegex(ValueError, "semantically equals"):
            reject_public_semantic_reuse(transformed_cases, transformed_gold)

    def test_public_individual_payload_reuse_is_detected_even_with_new_case_id(self) -> None:
        cases, gold = make_hidden_source()
        cases[0] = {"case_id": "RENAMED-HIDDEN-ID", "task_content": copy.deepcopy(self.cases[0]["task_content"])}
        with self.assertRaisesRegex(ValueError, "public semantic record or payload"):
            reject_public_semantic_reuse(cases, gold)

    def test_valid_default_hidden_structure_builds_480_trials(self) -> None:
        cases, gold = make_hidden_source()
        with tempfile.TemporaryDirectory() as temp:
            cases_path = Path(temp) / "cases.jsonl"
            gold_path = Path(temp) / "gold.jsonl"
            cases_path.write_text(jsonl_text(cases), encoding="utf-8")
            gold_path.write_text(jsonl_text(gold), encoding="utf-8")
            requests, mapping, _ = create_bundle_texts(
                cases_path,
                gold_path,
                repeats=5,
                order_seed=(1 << 191) + 319,
                request_name="requests.jsonl",
                mapping_name="mapping.jsonl",
                study_kind="preregistered_hidden_candidate",
            )
        self.assertEqual(len(requests.strip().splitlines()), 480)
        self.assertEqual(len(mapping.strip().splitlines()), 480)

    def test_hidden_default_structure_fails_closed(self) -> None:
        cases, gold = make_hidden_source()
        with self.subTest("minimum templates"):
            short_cases, short_gold = make_hidden_source(23)
            with self.assertRaisesRegex(ValueError, "at least 24 templates"):
                validate_hidden_protocol_default(short_cases, short_gold, repeats=5)
        with self.subTest("minimum repeats"):
            with self.assertRaisesRegex(ValueError, "at least 5 repeats"):
                validate_hidden_protocol_default(cases, gold, repeats=4)
        with self.subTest("complete cells"):
            with self.assertRaisesRegex(ValueError, "exactly one of each primary cell"):
                validate_hidden_protocol_default(cases[:-1], gold[:-1], repeats=5)
        with self.subTest("matched non-link content"):
            changed = copy.deepcopy(cases)
            target = next(
                row
                for row in changed
                if row["case_id"] == "HIDDEN-000-relevant-shuffled"
            )
            target["task_content"]["instruction"] = "Changed after pairing."
            with self.assertRaisesRegex(ValueError, "differs outside links"):
                validate_hidden_protocol_default(changed, gold, repeats=5)
        with self.subTest("no fixed point"):
            changed = copy.deepcopy(cases)
            correct = next(row for row in changed if row["case_id"] == "HIDDEN-000-relevant-correct")
            shuffled = next(row for row in changed if row["case_id"] == "HIDDEN-000-relevant-shuffled")
            shuffled["task_content"]["links"] = copy.deepcopy(correct["task_content"]["links"])
            with self.assertRaisesRegex(ValueError, "fixed point"):
                validate_hidden_protocol_default(changed, gold, repeats=5)
        with self.subTest("equal link count"):
            changed = copy.deepcopy(cases)
            shuffled = next(row for row in changed if row["case_id"] == "HIDDEN-000-relevant-shuffled")
            shuffled["task_content"]["links"].pop()
            with self.assertRaisesRegex(ValueError, "link counts differ"):
                validate_hidden_protocol_default(changed, gold, repeats=5)


class ParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.allowed = ["A", "B", "NO_ACTION"]

    def test_exact_three_record_response_is_valid(self) -> None:
        raw = 'ACTION: A\nPROBABILITIES: {"A":0.8,"B":0.1,"NO_ACTION":0.1}\nEXPLANATION: short.'
        parsed = parse_raw_response(raw, self.allowed)
        self.assertTrue(parsed["format_valid"])
        self.assertEqual(parsed["action"], "A")
        self.assertEqual(parsed["raw_response"], raw)
        self.assertEqual(parsed["errors"], [])

    def test_malformed_distribution_preserves_raw_and_does_not_erase_action(self) -> None:
        malformed = 'ACTION: A\nPROBABILITIES: {"A":0.9,"B":0.1,"NO_ACTION":0.1}\nEXPLANATION:'
        parsed = parse_raw_response(malformed, self.allowed)
        self.assertFalse(parsed["format_valid"])
        self.assertTrue(parsed["action_valid"])
        self.assertFalse(parsed["probabilities_valid"])
        self.assertEqual(parsed["raw_response"], malformed)
        self.assertTrue(any(error.startswith("probability_sum:") for error in parsed["errors"]))

    def test_duplicate_missing_boolean_and_nonfinite_probabilities_are_rejected(self) -> None:
        payloads = (
            '{"A":0.5,"A":0.3,"B":0.1,"NO_ACTION":0.1}',
            '{"A":0.8,"B":0.2}',
            '{"A":true,"B":0.0,"NO_ACTION":0.0}',
            '{"A":NaN,"B":0.0,"NO_ACTION":1.0}',
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                raw = f"ACTION: A\nPROBABILITIES: {payload}\nEXPLANATION:"
                self.assertFalse(parse_raw_response(raw, self.allowed)["probabilities_valid"])

    def test_huge_integer_probability_is_invalid_and_raw_is_preserved(self) -> None:
        huge = "9" * 4000
        raw = f'ACTION: A\nPROBABILITIES: {{"A":{huge},"B":0,"NO_ACTION":0}}\nEXPLANATION:'
        parsed = parse_raw_response(raw, self.allowed)
        self.assertFalse(parsed["probabilities_valid"])
        self.assertFalse(parsed["format_valid"])
        self.assertEqual(parsed["raw_response"], raw)
        self.assertIn("probability_unrepresentable:A", parsed["errors"])

    def test_unlisted_action_and_explicit_refusal_are_distinct_invalid_outputs(self) -> None:
        unlisted = parse_raw_response(
            'ACTION: C\nPROBABILITIES: {"A":0.3,"B":0.3,"NO_ACTION":0.4}\nEXPLANATION:',
            self.allowed,
        )
        refusal = parse_raw_response(
            'ACTION: REFUSAL\nPROBABILITIES: {"A":0.3,"B":0.3,"NO_ACTION":0.4}\nEXPLANATION:',
            self.allowed,
        )
        self.assertFalse(unlisted["action_valid"])
        self.assertFalse(unlisted["refusal"])
        self.assertFalse(refusal["action_valid"])
        self.assertTrue(refusal["refusal"])

    def test_extra_record_is_strictly_invalid(self) -> None:
        raw = 'ACTION: A\nPROBABILITIES: {"A":0.8,"B":0.1,"NO_ACTION":0.1}\nEXPLANATION:\nEXTRA: repair'
        parsed = parse_raw_response(raw, self.allowed)
        self.assertFalse(parsed["format_valid"])
        self.assertIn("record_count:4", parsed["errors"])


class PipelineAndScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = read_jsonl(DEFAULT_CASES, "case")
        self.gold = read_jsonl(DEFAULT_GOLD, "gold")
        self.requests, self.mapping = build_records(self.cases, self.gold, repeats=2, order_seed=20260825)
        self.raw = make_records(self.requests)
        self.parsed = parse_records(self.requests, self.raw)

    def test_mock_pipeline_metrics_are_labeled_non_model_evidence(self) -> None:
        metrics = score_records(
            self.mapping,
            self.parsed,
            "public_smoke_mock_dry_run",
            bootstrap_resamples=10000,
            bootstrap_seed=9,
            delta=0.10,
        )
        self.assertEqual(metrics["report_status"], "DRY_RUN_ONLY_NOT_MODEL_EVIDENCE")
        self.assertEqual(metrics["primary_metric"]["value"], 1.0)
        interval = metrics["primary_metric"]["cluster_bootstrap_95_percent_interval"]
        self.assertEqual((interval["lower"], interval["upper"]), (1.0, 1.0))
        self.assertTrue(metrics["decision_rule"]["statistical_effect_criterion_met"])
        self.assertFalse(metrics["decision_rule"]["claim_supported"])
        self.assertEqual(metrics["validity_metrics"]["strict_invalid_output_rate"], 0.0)
        self.assertEqual(metrics["validity_metrics"]["explicit_refusal_rate"], 0.0)

    def test_refusal_and_malformed_confidence_metrics_are_counted(self) -> None:
        changed = copy.deepcopy(self.parsed)
        target = changed[0]
        metadata = next(row for row in self.mapping if row["trial_id"] == target["trial_id"])
        raw = "ACTION: REFUSAL\nPROBABILITIES: broken\nEXPLANATION:"
        target.update(parse_raw_response(raw, metadata["allowed_actions"]))
        metrics = score_records(self.mapping, changed, "public_smoke_mock_dry_run", bootstrap_resamples=10000)
        self.assertEqual(metrics["validity_metrics"]["explicit_refusal_rate"], 1 / 32)
        self.assertEqual(metrics["validity_metrics"]["strict_invalid_output_rate"], 1 / 32)
        self.assertGreater(metrics["probability_metrics"]["multiclass_brier_mean"], 0.0)

    def test_scorer_rejects_parsed_fields_that_disagree_with_retained_raw(self) -> None:
        changed = copy.deepcopy(self.parsed)
        alternatives = [action for action in changed[0]["probabilities"] if action != changed[0]["action"]]
        changed[0]["action"] = alternatives[0]
        with self.assertRaisesRegex(ValueError, "does not match retained raw response"):
            score_records(self.mapping, changed, "public_smoke_mock_dry_run", bootstrap_resamples=10000)

    def test_cluster_bootstrap_enforces_minimum_resamples(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 10000"):
            cluster_bootstrap({"one": 0.2, "two": 0.4}, resamples=9999)

    def test_incomplete_pair_is_rejected(self) -> None:
        removed_id = self.mapping[0]["trial_id"]
        mapping = [row for row in self.mapping if row["trial_id"] != removed_id]
        parsed = [row for row in self.parsed if row["trial_id"] != removed_id]
        with self.assertRaisesRegex(ValueError, "incomplete paired cells"):
            score_records(mapping, parsed, "public_smoke_mock_dry_run", bootstrap_resamples=10000)

    def test_committed_pipeline_generator_is_fully_offline_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = generate(Path(first_dir))
            second = generate(Path(second_dir))
            self.assertEqual(set(first), set(second))
            for key in first:
                self.assertEqual(first[key].read_bytes(), second[key].read_bytes(), key)
            raw = read_jsonl(first["raw"], "raw response")
            self.assertTrue(all(row["transport_metadata"]["model_called"] is False for row in raw))
            self.assertTrue(all(row["transport_metadata"]["network_used"] is False for row in raw))


if __name__ == "__main__":
    unittest.main()
