#!/usr/bin/env python3
"""Score separated model-eval outputs with template-cluster uncertainty."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from common import pretty_json, read_jsonl, require_exact_fields, sha256_file, unique_by, write_text
from parse_responses import parse_raw_response


HERE = Path(__file__).resolve().parent
DEFAULT_MAPPING = HERE / "artifacts" / "public-smoke.evaluator-mapping.jsonl"
DEFAULT_MANIFEST = HERE / "artifacts" / "public-smoke.bundle-manifest.json"
DEFAULT_PARSED = HERE / "results" / "public-smoke-mock.parsed.jsonl"
DEFAULT_METRICS = HERE / "results" / "public-smoke-mock.metrics.json"
PRIMARY_CONDITIONS = ("correct", "shuffled")
SCOPES = ("relevant", "irrelevant")
WORST_BRIER = 2.0
LOG_FLOOR = 0.000001


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot take mean of empty metric group")
    return math.fsum(values) / len(values)


def rate(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> float:
    if not rows:
        raise ValueError("cannot take rate of empty metric group")
    return sum(1 for row in rows if predicate(row)) / len(rows)


def grouped_metric(
    rows: list[dict[str, Any]],
    key: str,
    value: Callable[[dict[str, Any]], float],
) -> dict[str, float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(float(value(row)))
    return {name: mean(values) for name, values in sorted(groups.items())}


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute percentile of empty list")
    position = probability * (len(sorted_values) - 1)
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = position - lower_index
    return sorted_values[lower_index] * (1.0 - fraction) + sorted_values[upper_index] * fraction


def cluster_bootstrap(
    template_values: dict[str, float],
    resamples: int = 10000,
    seed: int = 20260825,
) -> dict[str, Any]:
    if resamples < 10000:
        raise ValueError("cluster bootstrap requires at least 10000 resamples")
    names = sorted(template_values)
    if len(names) < 2:
        raise ValueError("cluster bootstrap requires at least two template clusters")
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(resamples):
        selected = [template_values[rng.choice(names)] for _ in names]
        samples.append(mean(selected))
    samples.sort()
    return {
        "method": "two-sided percentile bootstrap with templates resampled as clusters and repeats retained",
        "confidence_level": 0.95,
        "lower": percentile(samples, 0.025),
        "upper": percentile(samples, 0.975),
        "resamples": resamples,
        "seed": seed,
        "cluster_count": len(names),
    }


def _validate_mapping_and_parsed(
    mapping: list[dict[str, Any]], parsed: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    mapping_required = {
        "trial_id",
        "source_case_id",
        "template_id",
        "scope",
        "condition",
        "expected_action",
        "repeat_index",
        "allowed_actions",
    }
    parsed_required = {
        "trial_id",
        "raw_response",
        "action",
        "probabilities",
        "explanation",
        "action_valid",
        "probabilities_valid",
        "format_valid",
        "refusal",
        "errors",
    }
    for index, record in enumerate(mapping, 1):
        require_exact_fields(record, mapping_required, set(), f"mapping record {index}")
        if record["scope"] not in SCOPES or record["condition"] not in PRIMARY_CONDITIONS:
            raise ValueError(f"mapping record {index}: scorer accepts only primary scopes and conditions")
        if not isinstance(record["repeat_index"], int) or isinstance(record["repeat_index"], bool) or record["repeat_index"] < 1:
            raise ValueError(f"mapping record {index}: repeat_index must be a positive integer")
        actions = record["allowed_actions"]
        if not isinstance(actions, list) or not actions or not all(isinstance(action, str) for action in actions):
            raise ValueError(f"mapping record {index}: allowed_actions must be a non-empty string array")
        if len(set(actions)) != len(actions) or record["expected_action"] not in actions:
            raise ValueError(f"mapping record {index}: invalid allowed/gold actions")
    for index, record in enumerate(parsed, 1):
        require_exact_fields(record, parsed_required, {"transport_metadata"}, f"parsed record {index}")
        for flag in ("action_valid", "probabilities_valid", "format_valid", "refusal"):
            if not isinstance(record[flag], bool):
                raise ValueError(f"parsed record {index}: {flag} must be boolean")
        if not isinstance(record["raw_response"], str) or not isinstance(record["errors"], list):
            raise ValueError(f"parsed record {index}: malformed raw_response or errors")
    mapping_by_id = unique_by(mapping, "trial_id", "mapping")
    parsed_by_id = unique_by(parsed, "trial_id", "parsed")
    if set(mapping_by_id) != set(parsed_by_id):
        raise ValueError("mapping and parsed trial IDs do not match exactly")
    return mapping_by_id, parsed_by_id


def joined_rows(mapping: list[dict[str, Any]], parsed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping_by_id, parsed_by_id = _validate_mapping_and_parsed(mapping, parsed)
    rows: list[dict[str, Any]] = []
    for trial_id, metadata in mapping_by_id.items():
        response = parsed_by_id[trial_id]
        reparsed = parse_raw_response(response["raw_response"], metadata["allowed_actions"])
        for key in (
            "raw_response",
            "action",
            "probabilities",
            "explanation",
            "action_valid",
            "probabilities_valid",
            "format_valid",
            "refusal",
            "errors",
        ):
            if response[key] != reparsed[key]:
                raise ValueError(f"{trial_id}: parsed field {key} does not match retained raw response")
        action = response["action"]
        action_valid = bool(response["action_valid"]) and action in metadata["allowed_actions"]
        probability_valid = bool(response["probabilities_valid"])
        probabilities = response["probabilities"]
        if probability_valid:
            if not isinstance(probabilities, dict) or set(probabilities) != set(metadata["allowed_actions"]):
                raise ValueError(f"{trial_id}: parsed probabilities disagree with evaluator action set")
            brier = math.fsum(
                (float(probabilities[candidate]) - float(candidate == metadata["expected_action"])) ** 2
                for candidate in metadata["allowed_actions"]
            )
            log_loss = -math.log(max(float(probabilities[metadata["expected_action"]]), LOG_FLOOR))
        else:
            brier = WORST_BRIER
            log_loss = -math.log(LOG_FLOOR)
        correct = action_valid and action == metadata["expected_action"]
        false_action = metadata["scope"] == "irrelevant" and action_valid and action != "NO_ACTION"
        rows.append(
            {
                **metadata,
                "action": action,
                "correct": correct,
                "false_action": false_action,
                "strict_invalid": not response["format_valid"],
                "action_invalid": not action_valid,
                "refusal": response["refusal"],
                "brier": brier,
                "log_loss": log_loss,
            }
        )
    return rows


def template_effects(rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["template_id"], row["repeat_index"])].append(row)
    repeat_effects: dict[str, dict[str, float]] = defaultdict(dict)
    for (template_id, repeat_index), selected in sorted(grouped.items()):
        cells: dict[tuple[str, str], dict[str, Any]] = {}
        for row in selected:
            cell = (row["scope"], row["condition"])
            if cell in cells:
                raise ValueError(f"duplicate paired cell: {template_id}/repeat-{repeat_index}/{cell}")
            cells[cell] = row
        required = {(scope, condition) for scope in SCOPES for condition in PRIMARY_CONDITIONS}
        if set(cells) != required:
            raise ValueError(
                f"incomplete paired cells for {template_id}/repeat-{repeat_index}: "
                f"missing={sorted(required - set(cells))}, extra={sorted(set(cells) - required)}"
            )
        relevant = float(cells[("relevant", "correct")]["correct"]) - float(
            cells[("relevant", "shuffled")]["correct"]
        )
        collateral = float(cells[("irrelevant", "correct")]["false_action"]) - float(
            cells[("irrelevant", "shuffled")]["false_action"]
        )
        repeat_effects[template_id][str(repeat_index)] = relevant - collateral
    per_template = {
        template_id: mean(list(effects.values()))
        for template_id, effects in sorted(repeat_effects.items())
    }
    return per_template, dict(sorted(repeat_effects.items()))


def _cell_rates(rows: list[dict[str, Any]], field: str) -> dict[str, float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[f"{row['scope']}|{row['condition']}"].append(float(row[field]))
    return {key: mean(values) for key, values in sorted(groups.items())}


def score_records(
    mapping: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    study_kind: str,
    bootstrap_resamples: int = 10000,
    bootstrap_seed: int = 20260825,
    delta: float = 0.10,
) -> dict[str, Any]:
    if delta < 0.0:
        raise ValueError("delta must be non-negative")
    rows = joined_rows(mapping, parsed)
    per_template, per_template_repeat = template_effects(rows)
    primary = mean(list(per_template.values()))
    interval = cluster_bootstrap(per_template, bootstrap_resamples, bootstrap_seed)
    threshold_met = primary >= delta
    lower_above_zero = interval["lower"] > 0.0
    statistical_criterion_met = threshold_met and lower_above_zero
    dry_run = study_kind == "public_smoke_mock_dry_run"

    irrelevant = [row for row in rows if row["scope"] == "irrelevant"]
    result = {
        "schema_version": 1,
        "report_status": "DRY_RUN_ONLY_NOT_MODEL_EVIDENCE" if dry_run else "EVALUATOR_OUTPUT_REQUIRES_PROTOCOL_AUDIT",
        "study_kind": study_kind,
        "trial_count": len(rows),
        "template_count": len(per_template),
        "primary_metric": {
            "name": "paired_scope_controlled_correct_vs_shuffled_rule_use_effect",
            "value": primary,
            "formula": "(Y relevant,correct - Y relevant,shuffled) - (F irrelevant,correct - F irrelevant,shuffled), paired by template and repeat and macro-averaged by template",
            "per_template": per_template,
            "per_template_repeat": per_template_repeat,
            "cluster_bootstrap_95_percent_interval": interval,
        },
        "decision_rule": {
            "delta": delta,
            "point_estimate_at_least_delta": threshold_met,
            "bootstrap_lower_bound_above_zero": lower_above_zero,
            "statistical_effect_criterion_met": statistical_criterion_met,
            "claim_supported": False if dry_run else None,
            "reason": (
                "Public deterministic mock data can exercise the decision rule but can never support a model claim."
                if dry_run
                else "A statistical criterion alone is insufficient; apply every registration, integrity, leakage, exclusion, and stop-condition gate in the protocol."
            ),
        },
        "action_metrics": {
            "overall_exact_action_accuracy": rate(rows, lambda row: row["correct"]),
            "exact_action_accuracy_by_condition": grouped_metric(rows, "condition", lambda row: row["correct"]),
            "exact_action_accuracy_by_scope": grouped_metric(rows, "scope", lambda row: row["correct"]),
            "exact_action_accuracy_by_scope_and_condition": _cell_rates(rows, "correct"),
            "irrelevant_false_action_rate_overall": rate(irrelevant, lambda row: row["false_action"]),
            "irrelevant_false_action_rate_by_condition": grouped_metric(
                irrelevant, "condition", lambda row: row["false_action"]
            ),
        },
        "validity_metrics": {
            "strict_invalid_output_rate": rate(rows, lambda row: row["strict_invalid"]),
            "action_invalid_rate": rate(rows, lambda row: row["action_invalid"]),
            "explicit_refusal_rate": rate(rows, lambda row: row["refusal"]),
            "strict_invalid_rate_by_condition": grouped_metric(
                rows, "condition", lambda row: row["strict_invalid"]
            ),
            "explicit_refusal_rate_by_condition": grouped_metric(rows, "condition", lambda row: row["refusal"]),
        },
        "probability_metrics": {
            "multiclass_brier_mean": mean([row["brier"] for row in rows]),
            "multiclass_brier_by_condition": grouped_metric(rows, "condition", lambda row: row["brier"]),
            "multiclass_brier_by_scope": grouped_metric(rows, "scope", lambda row: row["brier"]),
            "log_loss_mean": mean([row["log_loss"] for row in rows]),
            "log_loss_by_condition": grouped_metric(rows, "condition", lambda row: row["log_loss"]),
            "log_loss_by_scope": grouped_metric(rows, "scope", lambda row: row["log_loss"]),
            "malformed_distribution_penalty": {"brier": WORST_BRIER, "log_loss": -math.log(LOG_FLOOR)},
        },
        "claim_boundary": (
            "This committed output comes only from a deterministic public-smoke fixture. No language model, "
            "API, SDK, network service, or paid endpoint was used."
            if dry_run
            else "This score file is not independently a claim. MODEL_EVALUATION_PROTOCOL.md defines the remaining mandatory gates."
        ),
    }
    return result


def load_manifest(path: Path, mapping_path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    evaluator = manifest.get("evaluator_bundle")
    if not isinstance(evaluator, dict) or evaluator.get("sha256") != sha256_file(mapping_path):
        raise ValueError("evaluator mapping hash does not match frozen bundle manifest")
    study_kind = manifest.get("study_kind")
    if study_kind not in {"public_smoke_mock_dry_run", "preregistered_hidden_candidate"}:
        raise ValueError("unsupported or missing manifest study_kind")
    return manifest


def score_files(
    mapping_path: Path,
    parsed_path: Path,
    manifest_path: Path,
    bootstrap_resamples: int = 10000,
    bootstrap_seed: int = 20260825,
    delta: float = 0.10,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, mapping_path)
    metrics = score_records(
        read_jsonl(mapping_path, "evaluator mapping"),
        read_jsonl(parsed_path, "parsed response"),
        str(manifest["study_kind"]),
        bootstrap_resamples,
        bootstrap_seed,
        delta,
    )
    metrics["input_integrity"] = {
        "bundle_manifest_sha256": sha256_file(manifest_path),
        "evaluator_mapping_sha256": sha256_file(mapping_path),
        "parsed_responses_sha256": sha256_file(parsed_path),
        "evaluator_mapping_hash_verified": True,
        "parsed_fields_recomputed_from_retained_raw": True,
    }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--parsed", type=Path, default=DEFAULT_PARSED)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--bootstrap-resamples", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260825)
    parser.add_argument("--delta", type=float, default=0.10)
    args = parser.parse_args()
    metrics = score_files(
        args.mapping,
        args.parsed,
        args.manifest,
        args.bootstrap_resamples,
        args.bootstrap_seed,
        args.delta,
    )
    write_text(args.output, pretty_json(metrics))
    print(
        f"wrote {args.output}; status={metrics['report_status']}; "
        f"primary={metrics['primary_metric']['value']:.6f}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
