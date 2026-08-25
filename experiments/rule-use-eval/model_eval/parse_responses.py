#!/usr/bin/env python3
"""Strictly parse three-record model responses while retaining raw text."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from common import jsonl_text, read_jsonl, require_exact_fields, sha256_file, unique_by, write_text


HERE = Path(__file__).resolve().parent
DEFAULT_REQUESTS = HERE / "artifacts" / "public-smoke.requests.jsonl"
DEFAULT_MANIFEST = HERE / "artifacts" / "public-smoke.bundle-manifest.json"
DEFAULT_RAW = HERE / "results" / "public-smoke-mock.raw.jsonl"
DEFAULT_PARSED = HERE / "results" / "public-smoke-mock.parsed.jsonl"
TOLERANCE = 0.000001
REFUSAL_TOKEN = "REFUSAL"


class DuplicateProbabilityKey(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateProbabilityKey(f"duplicate probability key: {key}")
        result[key] = value
    return result


def parse_raw_response(raw_response: str, allowed_actions: list[str]) -> dict[str, Any]:
    if not isinstance(raw_response, str):
        raise ValueError("raw_response must be a string")
    if not allowed_actions or len(set(allowed_actions)) != len(allowed_actions):
        raise ValueError("allowed_actions must be non-empty and unique")

    errors: list[str] = []
    lines = raw_response.splitlines()
    if len(lines) != 3:
        errors.append(f"record_count:{len(lines)}")

    action: str | None = None
    action_valid = False
    refusal = False
    if lines and lines[0].startswith("ACTION: "):
        candidate = lines[0][len("ACTION: ") :]
        action = candidate
        refusal = candidate == REFUSAL_TOKEN
        if candidate in allowed_actions:
            action_valid = True
        elif refusal:
            errors.append("explicit_refusal")
        else:
            errors.append("unlisted_action")
    else:
        errors.append("missing_or_misordered_action_record")

    probabilities: dict[str, float] | None = None
    probabilities_valid = False
    if len(lines) >= 2 and lines[1].startswith("PROBABILITIES: "):
        payload = lines[1][len("PROBABILITIES: ") :]
        try:
            decoded = json.loads(payload, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        except (json.JSONDecodeError, DuplicateProbabilityKey, ValueError) as exc:
            errors.append(f"invalid_probability_json:{exc}")
        else:
            if not isinstance(decoded, dict):
                errors.append("probabilities_not_object")
            elif set(decoded) != set(allowed_actions):
                missing = sorted(set(allowed_actions) - set(decoded))
                extra = sorted(set(decoded) - set(allowed_actions))
                errors.append(f"probability_keys_mismatch:missing={missing},extra={extra}")
            else:
                valid_numbers = True
                converted: dict[str, float] = {}
                for key in allowed_actions:
                    value = decoded[key]
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        errors.append(f"probability_not_number:{key}")
                        valid_numbers = False
                        continue
                    try:
                        numeric = float(value)
                    except (OverflowError, ValueError):
                        errors.append(f"probability_unrepresentable:{key}")
                        valid_numbers = False
                        continue
                    if not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0:
                        errors.append(f"probability_out_of_range:{key}")
                        valid_numbers = False
                    converted[key] = numeric
                if valid_numbers:
                    total = math.fsum(converted.values())
                    if abs(total - 1.0) > TOLERANCE:
                        errors.append(f"probability_sum:{total:.17g}")
                    else:
                        probabilities = converted
                        probabilities_valid = True
    else:
        errors.append("missing_or_misordered_probabilities_record")

    explanation: str | None = None
    explanation_valid = False
    if len(lines) >= 3 and lines[2].startswith("EXPLANATION:"):
        suffix = lines[2][len("EXPLANATION:") :]
        if suffix and not suffix.startswith(" "):
            errors.append("explanation_separator")
        else:
            explanation = suffix[1:] if suffix.startswith(" ") else ""
            explanation_valid = True
    else:
        errors.append("missing_or_misordered_explanation_record")

    format_valid = (
        len(lines) == 3
        and action_valid
        and probabilities_valid
        and explanation_valid
        and not errors
    )
    return {
        "raw_response": raw_response,
        "action": action,
        "probabilities": probabilities,
        "explanation": explanation,
        "action_valid": action_valid,
        "probabilities_valid": probabilities_valid,
        "format_valid": format_valid,
        "refusal": refusal,
        "errors": errors,
    }


def parse_records(requests: list[dict[str, Any]], raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, row in enumerate(requests, 1):
        require_exact_fields(row, {"trial_id", "request"}, set(), f"request record {index}")
        if not isinstance(row["request"], dict):
            raise ValueError(f"request record {index}: request must be an object")
    for index, row in enumerate(raw_records, 1):
        require_exact_fields(
            row,
            {"trial_id", "raw_response"},
            {"transport_metadata"},
            f"raw response record {index}",
        )
        if "transport_metadata" in row and not isinstance(row["transport_metadata"], dict):
            raise ValueError(f"raw response record {index}: transport_metadata must be an object")
    request_by_id = unique_by(requests, "trial_id", "request")
    raw_by_id = unique_by(raw_records, "trial_id", "raw response")
    if set(request_by_id) != set(raw_by_id):
        missing = sorted(set(request_by_id) - set(raw_by_id))
        unknown = sorted(set(raw_by_id) - set(request_by_id))
        raise ValueError(f"raw trial coverage mismatch: missing={missing}, unknown={unknown}")

    parsed: list[dict[str, Any]] = []
    for request_row in requests:
        trial_id = request_row["trial_id"]
        request = request_row["request"]
        contract = request.get("response_contract")
        if not isinstance(contract, dict):
            raise ValueError(f"{trial_id}: response_contract must be an object")
        actions = contract.get("allowed_actions")
        if not isinstance(actions, list) or not all(isinstance(action, str) for action in actions):
            raise ValueError(f"{trial_id}: allowed_actions must be a string array")
        raw = raw_by_id[trial_id]
        result = parse_raw_response(raw["raw_response"], actions)
        output = {"trial_id": trial_id, **result}
        if "transport_metadata" in raw:
            output["transport_metadata"] = raw["transport_metadata"]
        parsed.append(output)
    return parsed


def verify_runner_bundle(manifest_path: Path, requests_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runner = manifest.get("runner_bundle") if isinstance(manifest, dict) else None
    if not isinstance(runner, dict) or runner.get("sha256") != sha256_file(requests_path):
        raise ValueError("runner request hash does not match frozen bundle manifest")


def parse_files(requests_path: Path, raw_path: Path, manifest_path: Path | None = None) -> list[dict[str, Any]]:
    if manifest_path is not None:
        verify_runner_bundle(manifest_path, requests_path)
    return parse_records(read_jsonl(requests_path, "request"), read_jsonl(raw_path, "raw response"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, default=DEFAULT_REQUESTS)
    parser.add_argument("--raw-responses", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_PARSED)
    args = parser.parse_args()
    parsed = parse_files(args.requests, args.raw_responses, args.manifest)
    write_text(args.output, jsonl_text(parsed))
    valid = sum(1 for row in parsed if row["format_valid"])
    print(f"parsed {len(parsed)} raw responses; strict-valid={valid}; raw text retained")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
