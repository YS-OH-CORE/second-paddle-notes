#!/usr/bin/env python3
"""Strict scorer for rule-use JSONL predictions."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "data" / "cases.jsonl"
DEFAULT_GOLD = ROOT / "data" / "gold.jsonl"
CONDITIONS = ("correct", "shuffled", "reversed", "absent", "irrelevant_probe")


def read_jsonl(path: Path, required: set[str], allowed: set[str], kind: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected object")
            missing = required - set(record)
            extra = set(record) - allowed
            if missing:
                raise ValueError(f"{path}:{line_number}: missing fields: {sorted(missing)}")
            if extra:
                raise ValueError(f"{path}:{line_number}: unknown fields: {sorted(extra)}")
            case_id = record.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                raise ValueError(f"{path}:{line_number}: case_id must be a non-empty string")
            if case_id in seen:
                raise ValueError(f"{path}:{line_number}: duplicate {kind} case_id: {case_id}")
            seen.add(case_id)
            records.append(record)
    if not records:
        raise ValueError(f"{path}: no {kind} records")
    return records


def load_inputs(cases_path: Path, gold_path: Path, predictions_path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    cases = read_jsonl(
        cases_path,
        {"case_id", "task_content"},
        {"case_id", "task_content"},
        "case",
    )
    gold_records = read_jsonl(
        gold_path,
        {"case_id", "template_id", "scope", "condition", "expected_action"},
        {"case_id", "template_id", "scope", "condition", "expected_action"},
        "gold",
    )
    prediction_records = read_jsonl(
        predictions_path,
        {"case_id", "action"},
        {"case_id", "action"},
        "prediction",
    )

    case_by_id = {row["case_id"]: row for row in cases}
    gold_by_id = {row["case_id"]: row for row in gold_records}
    prediction_by_id = {row["case_id"]: row["action"] for row in prediction_records}
    case_ids = set(case_by_id)

    for label, ids in (("gold", set(gold_by_id)), ("predictions", set(prediction_by_id))):
        unknown = ids - case_ids
        missing = case_ids - ids
        if unknown:
            raise ValueError(f"unknown {label} case IDs: {sorted(unknown)}")
        if missing:
            raise ValueError(f"missing {label} case IDs: {sorted(missing)}")

    for case_id, case in case_by_id.items():
        gold = gold_by_id[case_id]
        valid_actions = {row["action_id"] for row in case["task_content"]["action_checks"]}
        predicted = prediction_by_id[case_id]
        expected = gold["expected_action"]
        if not isinstance(predicted, str) or predicted not in valid_actions:
            raise ValueError(f"unknown action for {case_id}: {predicted!r}")
        if expected not in valid_actions:
            raise ValueError(f"gold action is not allowed for {case_id}: {expected!r}")
    return cases, gold_by_id, prediction_by_id


def rate(rows: Iterable[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> float:
    rows = list(rows)
    if not rows:
        raise ValueError("metric group is empty")
    return sum(1 for row in rows if predicate(row)) / len(rows)


def score_records(cases: list[dict[str, Any]], gold: dict[str, dict[str, Any]], predictions: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["case_id"]
        predicted = predictions[case_id]
        expected = gold[case_id]["expected_action"]
        rows.append(
            {
                "case_id": case_id,
                "template_id": gold[case_id]["template_id"],
                "scope": gold[case_id]["scope"],
                "condition": gold[case_id]["condition"],
                "correct": predicted == expected,
                "false_action": gold[case_id]["scope"] == "irrelevant" and predicted != "NO_ACTION",
            }
        )

    accuracy_by_condition: dict[str, float] = {}
    relevant_accuracy: dict[str, float] = {}
    irrelevant_false_action_rate: dict[str, float] = {}
    for condition in CONDITIONS:
        condition_rows = [row for row in rows if row["condition"] == condition]
        relevant_rows = [row for row in condition_rows if row["scope"] == "relevant"]
        irrelevant_rows = [row for row in condition_rows if row["scope"] == "irrelevant"]
        accuracy_by_condition[condition] = rate(condition_rows, lambda row: row["correct"])
        relevant_accuracy[condition] = rate(relevant_rows, lambda row: row["correct"])
        irrelevant_false_action_rate[condition] = rate(irrelevant_rows, lambda row: row["false_action"])

    by_scope = {
        scope: rate([row for row in rows if row["scope"] == scope], lambda row: row["correct"])
        for scope in ("relevant", "irrelevant")
    }

    template_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        template_rows[row["template_id"]].append(row)
    per_template: dict[str, float] = {}
    for template_id, selected in sorted(template_rows.items()):
        def one(scope: str, condition: str) -> dict[str, Any]:
            matches = [row for row in selected if row["scope"] == scope and row["condition"] == condition]
            if len(matches) != 1:
                raise ValueError(f"expected one {template_id}/{scope}/{condition} row, found {len(matches)}")
            return matches[0]

        relevant_effect = float(one("relevant", "correct")["correct"]) - float(one("relevant", "shuffled")["correct"])
        collateral_effect = float(one("irrelevant", "correct")["false_action"]) - float(one("irrelevant", "shuffled")["false_action"])
        per_template[template_id] = relevant_effect - collateral_effect

    primary_value = sum(per_template.values()) / len(per_template)
    manipulated = ("shuffled", "reversed", "absent", "irrelevant_probe")
    manipulated_mean = sum(relevant_accuracy[name] for name in manipulated) / len(manipulated)

    return {
        "schema_version": 1,
        "case_count": len(rows),
        "primary_metric": {
            "name": "paired_scope_controlled_rule_use_effect",
            "value": primary_value,
            "higher_is_more_link_sensitive": True,
            "formula": "(relevant_accuracy_correct - relevant_accuracy_shuffled) - (irrelevant_false_action_rate_correct - irrelevant_false_action_rate_shuffled), macro-averaged over templates",
            "per_template": per_template,
        },
        "secondary_metrics": {
            "overall_exact_action_accuracy": rate(rows, lambda row: row["correct"]),
            "exact_action_accuracy_by_condition": accuracy_by_condition,
            "exact_action_accuracy_by_scope": by_scope,
            "relevant_exact_action_accuracy_by_condition": relevant_accuracy,
            "irrelevant_false_action_rate_by_condition": irrelevant_false_action_rate,
            "correct_vs_manipulated_relevant_accuracy_gap": relevant_accuracy["correct"] - manipulated_mean,
        },
        "claim_boundary": "Deterministic smoke-harness output only; no language model was evaluated.",
    }


def score_files(cases_path: Path, gold_path: Path, predictions_path: Path) -> dict[str, Any]:
    cases, gold, predictions = load_inputs(cases_path, gold_path, predictions_path)
    return score_records(cases, gold, predictions)


def write_metrics(path: Path, metrics: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    metrics = score_files(args.cases, args.gold, args.predictions)
    if args.output:
        write_metrics(args.output, metrics)
        print(f"wrote metrics to {args.output}")
    else:
        print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
