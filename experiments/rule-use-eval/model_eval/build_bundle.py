#!/usr/bin/env python3
"""Build separated runner and evaluator bundles without calling a model."""

from __future__ import annotations

import argparse
import copy
import hashlib
import random
from pathlib import Path
from typing import Any

from common import (
    canonical_json,
    jsonl_text,
    pretty_json,
    read_jsonl,
    require_exact_fields,
    sha256_file,
    sha256_text,
    unique_by,
    write_text,
)


HERE = Path(__file__).resolve().parent
EVAL_ROOT = HERE.parent
DEFAULT_CASES = EVAL_ROOT / "data" / "cases.jsonl"
DEFAULT_GOLD = EVAL_ROOT / "data" / "gold.jsonl"
DEFAULT_REQUESTS = HERE / "artifacts" / "public-smoke.requests.jsonl"
DEFAULT_MAPPING = HERE / "artifacts" / "public-smoke.evaluator-mapping.jsonl"
DEFAULT_MANIFEST = HERE / "artifacts" / "public-smoke.bundle-manifest.json"
PRIMARY_CONDITIONS = ("correct", "shuffled")
ID_DOMAIN = "rule-use-model-eval-trial-v1"
DEFAULT_PUBLIC_ORDER_SEED = 20260825
FORBIDDEN_RUNNER_KEYS = frozenset(
    {
        "case_id",
        "source_case_id",
        "template_id",
        "scope",
        "condition",
        "expected_action",
        "repeat_index",
        "gold",
    }
)


def forbidden_runner_paths(value: Any, path: str = "task_content") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_RUNNER_KEYS:
                found.append(child_path)
            found.extend(forbidden_runner_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_runner_paths(child, f"{path}[{index}]"))
    return found


def semantic_bundle_fingerprint(records: list[dict[str, Any]]) -> str:
    """Hash JSONL semantics independent of whitespace, key order, and record order."""
    canonical_records = sorted(canonical_json(record) for record in records)
    return sha256_text("\n".join(canonical_records) + "\n")


def semantic_record_fingerprints(
    records: list[dict[str, Any]], *, payload_only: bool
) -> set[str]:
    fingerprints: set[str] = set()
    for record in records:
        if payload_only and "task_content" in record:
            value: Any = record["task_content"]
        elif payload_only:
            value = {key: item for key, item in record.items() if key != "case_id"}
        else:
            value = record
        fingerprints.add(sha256_text(canonical_json(value)))
    return fingerprints


def reject_public_semantic_reuse(
    candidate_cases: list[dict[str, Any]], candidate_gold: list[dict[str, Any]]
) -> None:
    public_cases = read_jsonl(DEFAULT_CASES, "public case")
    public_gold = read_jsonl(DEFAULT_GOLD, "public gold")
    for label, candidate, public in (
        ("cases", candidate_cases, public_cases),
        ("gold", candidate_gold, public_gold),
    ):
        if semantic_bundle_fingerprint(candidate) == semantic_bundle_fingerprint(public):
            raise ValueError(f"hidden candidate {label} semantically equals the committed public smoke bundle")
        full_overlap = semantic_record_fingerprints(candidate, payload_only=False) & semantic_record_fingerprints(
            public, payload_only=False
        )
        payload_overlap = semantic_record_fingerprints(candidate, payload_only=True) & semantic_record_fingerprints(
            public, payload_only=True
        )
        if full_overlap or payload_overlap:
            raise ValueError(
                f"hidden candidate {label} reuses {len(full_overlap | payload_overlap)} "
                "public semantic record or payload fingerprint(s)"
            )


def _forward_link_map(task: dict[str, Any], label: str) -> dict[tuple[str, str, str], str]:
    links = task.get("links")
    if not isinstance(links, list) or len(links) < 2:
        raise ValueError(f"{label}: primary links must contain at least two records")
    result: dict[tuple[str, str, str], str] = {}
    for index, link in enumerate(links, 1):
        if not isinstance(link, dict) or set(link) != {"direction", "rule_id", "trigger_id", "action_id"}:
            raise ValueError(f"{label}: link {index} must contain only direction, rule_id, trigger_id, action_id")
        if link["direction"] != "rule_to_trigger_to_action":
            raise ValueError(f"{label}: primary link {index} must use rule_to_trigger_to_action")
        if not all(isinstance(link[field], str) and link[field] for field in link):
            raise ValueError(f"{label}: primary link {index} fields must be non-empty strings")
        key = (link["direction"], link["rule_id"], link["trigger_id"])
        if key in result:
            raise ValueError(f"{label}: duplicate primary link identity: {key}")
        result[key] = link["action_id"]
    return result


def _validate_matched_pair(correct: dict[str, Any], shuffled: dict[str, Any], label: str) -> None:
    correct_task = correct["task_content"]
    shuffled_task = shuffled["task_content"]
    if not isinstance(correct_task, dict) or not isinstance(shuffled_task, dict):
        raise ValueError(f"{label}: task_content must be an object")
    if "links" not in correct_task or "links" not in shuffled_task:
        raise ValueError(f"{label}: both matched tasks require links")
    correct_without_links = {key: value for key, value in correct_task.items() if key != "links"}
    shuffled_without_links = {key: value for key, value in shuffled_task.items() if key != "links"}
    if canonical_json(correct_without_links) != canonical_json(shuffled_without_links):
        raise ValueError(f"{label}: correct/shuffled content differs outside links")
    correct_links = correct_task["links"]
    shuffled_links = shuffled_task["links"]
    if not isinstance(correct_links, list) or not isinstance(shuffled_links, list) or len(correct_links) != len(shuffled_links):
        raise ValueError(f"{label}: correct/shuffled link counts differ")
    correct_map = _forward_link_map(correct_task, f"{label}/correct")
    shuffled_map = _forward_link_map(shuffled_task, f"{label}/shuffled")
    if set(correct_map) != set(shuffled_map):
        raise ValueError(f"{label}: correct/shuffled link identities differ")
    if sorted(correct_map.values()) != sorted(shuffled_map.values()):
        raise ValueError(f"{label}: shuffled actions are not a permutation of correct actions")
    fixed_points = [key for key in correct_map if correct_map[key] == shuffled_map[key]]
    if fixed_points:
        raise ValueError(f"{label}: shuffled mapping has fixed point(s): {fixed_points}")
    correct_size = len(canonical_json(correct_task).encode("utf-8"))
    shuffled_size = len(canonical_json(shuffled_task).encode("utf-8"))
    if correct_size != shuffled_size:
        raise ValueError(
            f"{label}: canonical serialized lengths differ: correct={correct_size}, shuffled={shuffled_size}"
        )


def validate_hidden_protocol_default(
    cases: list[dict[str, Any]], gold: list[dict[str, Any]], repeats: int
) -> None:
    if repeats < 5:
        raise ValueError("hidden candidate requires at least 5 repeats per registered cell")
    case_by_id, gold_by_id = _validate_source(cases, gold)
    grouped: dict[str, dict[tuple[str, str], str]] = {}
    for case_id, metadata in gold_by_id.items():
        template_id = metadata["template_id"]
        scope = metadata["scope"]
        condition = metadata["condition"]
        if not isinstance(template_id, str) or not template_id:
            raise ValueError(f"hidden gold {case_id}: template_id must be a non-empty string")
        if scope not in {"relevant", "irrelevant"} or condition not in set(PRIMARY_CONDITIONS):
            raise ValueError(
                f"hidden gold {case_id}: toolkit permits only relevant/irrelevant x correct/shuffled primary cells"
            )
        cell = (scope, condition)
        cells = grouped.setdefault(template_id, {})
        if cell in cells:
            raise ValueError(f"hidden template {template_id}: duplicate primary cell {cell}")
        cells[cell] = case_id
    if len(grouped) < 24:
        raise ValueError(f"hidden candidate requires at least 24 templates; found {len(grouped)}")
    required = {(scope, condition) for scope in ("relevant", "irrelevant") for condition in PRIMARY_CONDITIONS}
    for template_id, cells in sorted(grouped.items()):
        if set(cells) != required:
            raise ValueError(
                f"hidden template {template_id}: requires exactly one of each primary cell; "
                f"missing={sorted(required - set(cells))}, extra={sorted(set(cells) - required)}"
            )
        for scope in ("relevant", "irrelevant"):
            correct_id = cells[(scope, "correct")]
            shuffled_id = cells[(scope, "shuffled")]
            correct_gold = gold_by_id[correct_id]
            shuffled_gold = gold_by_id[shuffled_id]
            if correct_gold["expected_action"] != shuffled_gold["expected_action"]:
                raise ValueError(f"hidden {template_id}/{scope}: matched expected actions differ")
            _validate_matched_pair(
                case_by_id[correct_id],
                case_by_id[shuffled_id],
                f"hidden {template_id}/{scope}",
            )


def allowed_actions(task_content: dict[str, Any]) -> list[str]:
    checks = task_content.get("action_checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("task_content.action_checks must be a non-empty array")
    actions: list[str] = []
    for index, check in enumerate(checks, 1):
        if not isinstance(check, dict) or set(check) != {"action_id", "check"}:
            raise ValueError(f"action_checks[{index}] must contain only action_id and check")
        action = check["action_id"]
        if not isinstance(action, str) or not action:
            raise ValueError(f"action_checks[{index}].action_id must be a non-empty string")
        if action in actions:
            raise ValueError(f"duplicate allowed action: {action}")
        actions.append(action)
    return actions


def opaque_trial_id(case_id: str, repeat_index: int, order_seed: int) -> str:
    material = f"{ID_DOMAIN}|{order_seed}|{case_id}|{repeat_index}".encode("utf-8")
    return "TRIAL-" + hashlib.sha256(material).hexdigest()[:20].upper()


def _validate_source(cases: list[dict[str, Any]], gold: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    for index, record in enumerate(cases, 1):
        require_exact_fields(record, {"case_id", "task_content"}, set(), f"case record {index}")
        if not isinstance(record["task_content"], dict):
            raise ValueError(f"case record {index}: task_content must be an object")
    for index, record in enumerate(gold, 1):
        require_exact_fields(
            record,
            {"case_id", "template_id", "scope", "condition", "expected_action"},
            set(),
            f"gold record {index}",
        )
    case_by_id = unique_by(cases, "case_id", "case")
    gold_by_id = unique_by(gold, "case_id", "gold")
    if set(case_by_id) != set(gold_by_id):
        raise ValueError("case and gold IDs do not match exactly")
    return case_by_id, gold_by_id


def build_records(
    cases: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    repeats: int,
    order_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    case_by_id, gold_by_id = _validate_source(cases, gold)
    joined: list[tuple[dict[str, Any], dict[str, Any]]] = []

    selected_ids = [
        case_id
        for case_id, metadata in gold_by_id.items()
        if metadata["condition"] in PRIMARY_CONDITIONS
    ]
    if not selected_ids:
        raise ValueError("source contains no correct/shuffled primary cases")

    for case_id in sorted(selected_ids):
        case = case_by_id[case_id]
        metadata = gold_by_id[case_id]
        if metadata["scope"] not in {"relevant", "irrelevant"}:
            raise ValueError(f"unsupported primary scope for {case_id}: {metadata['scope']!r}")
        task = copy.deepcopy(case["task_content"])
        forbidden = forbidden_runner_paths(task)
        if forbidden:
            raise ValueError(
                f"evaluator metadata is forbidden inside runner task content for {case_id}: {forbidden}"
            )
        actions = allowed_actions(task)
        if metadata["expected_action"] not in actions:
            raise ValueError(f"gold action is not allowed for {case_id}")
        for repeat_index in range(1, repeats + 1):
            trial_id = opaque_trial_id(case_id, repeat_index, order_seed)
            request = {
                "trial_id": trial_id,
                "request": {
                    "task_content": copy.deepcopy(task),
                    "response_contract": {
                        "record_order": ["ACTION", "PROBABILITIES", "EXPLANATION"],
                        "allowed_actions": list(actions),
                        "probability_sum_tolerance": 0.000001,
                        "explicit_refusal_token": "REFUSAL",
                        "instruction": (
                            "Return exactly three plain-text records in the registered order. "
                            "ACTION must contain one allowed action_id or the exact token REFUSAL; "
                            "PROBABILITIES must be a JSON object containing every allowed action_id exactly once; "
                            "EXPLANATION may contain one sentence or be empty."
                        ),
                    },
                },
            }
            evaluator = {
                "trial_id": trial_id,
                "source_case_id": case_id,
                "template_id": metadata["template_id"],
                "scope": metadata["scope"],
                "condition": metadata["condition"],
                "expected_action": metadata["expected_action"],
                "repeat_index": repeat_index,
                "allowed_actions": list(actions),
            }
            joined.append((request, evaluator))

    rng = random.Random(order_seed)
    rng.shuffle(joined)
    requests = [pair[0] for pair in joined]
    # Keep evaluator records out of runner order so line position is not a second join key.
    mapping = sorted((pair[1] for pair in joined), key=lambda row: row["trial_id"])
    if len({row["trial_id"] for row in requests}) != len(requests):
        raise ValueError("opaque trial ID collision")
    return requests, mapping


def build_manifest(
    cases_path: Path,
    gold_path: Path,
    requests_text: str,
    mapping_text: str,
    request_name: str,
    mapping_name: str,
    repeats: int,
    order_seed: int,
    trial_count: int,
    study_kind: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact": "provider-neutral separated model-evaluation bundle",
        "study_kind": study_kind,
        "trial_count": trial_count,
        "repeats_per_cell": repeats,
        "primary_conditions": list(PRIMARY_CONDITIONS),
        "order_seed": order_seed if study_kind == "public_smoke_mock_dry_run" else None,
        "order_seed_sha256": sha256_text(str(order_seed)),
        "source": {
            "cases_sha256": sha256_file(cases_path),
            "gold_sha256": sha256_file(gold_path),
        },
        "runner_bundle": {
            "file": request_name,
            "sha256": sha256_text(requests_text),
            "contains_evaluator_metadata": False,
        },
        "evaluator_bundle": {
            "file": mapping_name,
            "sha256": sha256_text(mapping_text),
            "runner_must_not_receive": True,
        },
        "claim_boundary": (
            "A study_kind label does not make a run claim-bearing. The frozen hidden-set, "
            "preregistration, leakage audit, model identity, raw-release, and stop-condition "
            "requirements in ../MODEL_EVALUATION_PROTOCOL.md still apply."
        ),
    }


def create_bundle_texts(
    cases_path: Path,
    gold_path: Path,
    repeats: int,
    order_seed: int,
    request_name: str,
    mapping_name: str,
    study_kind: str,
) -> tuple[str, str, str]:
    cases = read_jsonl(cases_path, "case")
    gold = read_jsonl(gold_path, "gold")
    if study_kind == "preregistered_hidden_candidate":
        reject_public_semantic_reuse(cases, gold)
        if abs(order_seed).bit_length() < 128:
            raise ValueError("hidden candidate requires a separately generated seed value at least 128 bits wide")
        validate_hidden_protocol_default(cases, gold, repeats)
    requests, mapping = build_records(cases, gold, repeats, order_seed)
    requests_text = jsonl_text(requests)
    mapping_text = jsonl_text(mapping)
    manifest = build_manifest(
        cases_path,
        gold_path,
        requests_text,
        mapping_text,
        request_name,
        mapping_name,
        repeats,
        order_seed,
        len(requests),
        study_kind,
    )
    return requests_text, mapping_text, pretty_json(manifest)


def write_bundle(
    cases_path: Path,
    gold_path: Path,
    requests_path: Path,
    mapping_path: Path,
    manifest_path: Path,
    repeats: int,
    order_seed: int,
    study_kind: str,
) -> None:
    requests_text, mapping_text, manifest_text = create_bundle_texts(
        cases_path,
        gold_path,
        repeats,
        order_seed,
        requests_path.name,
        mapping_path.name,
        study_kind,
    )
    write_text(requests_path, requests_text)
    write_text(mapping_path, mapping_text)
    write_text(manifest_path, manifest_text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--requests-output", type=Path, default=DEFAULT_REQUESTS)
    parser.add_argument("--mapping-output", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--order-seed", type=int, default=DEFAULT_PUBLIC_ORDER_SEED)
    parser.add_argument(
        "--study-kind",
        choices=("public_smoke_mock_dry_run", "preregistered_hidden_candidate"),
        default="public_smoke_mock_dry_run",
    )
    args = parser.parse_args()
    write_bundle(
        args.cases,
        args.gold,
        args.requests_output,
        args.mapping_output,
        args.manifest_output,
        args.repeats,
        args.order_seed,
        args.study_kind,
    )
    print(f"wrote {args.requests_output} and evaluator-only {args.mapping_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
