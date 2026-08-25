#!/usr/bin/env python3
"""Create deterministic public-smoke fixture responses; never call a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import canonical_json, jsonl_text, read_jsonl, require_exact_fields, sha256_file, write_text


HERE = Path(__file__).resolve().parent
DEFAULT_REQUESTS = HERE / "artifacts" / "public-smoke.requests.jsonl"
DEFAULT_MANIFEST = HERE / "artifacts" / "public-smoke.bundle-manifest.json"
DEFAULT_RAW = HERE / "results" / "public-smoke-mock.raw.jsonl"


def fixture_action(task: dict[str, Any], allowed: list[str]) -> str:
    event = task.get("observed_event")
    links = task.get("links")
    if not isinstance(event, str) or not isinstance(links, list):
        raise ValueError("mock fixture requires observed_event and links")
    for link in links:
        if (
            isinstance(link, dict)
            and link.get("direction") == "rule_to_trigger_to_action"
            and link.get("trigger_id") == event
            and link.get("action_id") in allowed
        ):
            return str(link["action_id"])
    if "NO_ACTION" not in allowed:
        raise ValueError("mock fixture requires NO_ACTION in allowed actions")
    return "NO_ACTION"


def fixture_probabilities(selected: str, allowed: list[str]) -> dict[str, float]:
    if len(allowed) == 1:
        return {allowed[0]: 1.0}
    remainder = 0.08 / (len(allowed) - 1)
    values = {action: remainder for action in allowed}
    values[selected] = 0.92
    # Assign the tiny binary rounding residue deterministically to the last action.
    values[allowed[-1]] += 1.0 - sum(values.values())
    return values


def make_records(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(requests, 1):
        require_exact_fields(row, {"trial_id", "request"}, set(), f"request record {index}")
        trial_id = row["trial_id"]
        if not isinstance(trial_id, str) or not trial_id or trial_id in seen:
            raise ValueError(f"request record {index}: invalid or duplicate trial_id")
        seen.add(trial_id)
        request = row["request"]
        if not isinstance(request, dict):
            raise ValueError(f"{trial_id}: request must be an object")
        task = request.get("task_content")
        contract = request.get("response_contract")
        if not isinstance(task, dict) or not isinstance(contract, dict):
            raise ValueError(f"{trial_id}: malformed request")
        allowed = contract.get("allowed_actions")
        if not isinstance(allowed, list) or not all(isinstance(action, str) for action in allowed):
            raise ValueError(f"{trial_id}: malformed allowed_actions")
        action = fixture_action(task, allowed)
        probabilities = fixture_probabilities(action, allowed)
        raw = "\n".join(
            (
                f"ACTION: {action}",
                f"PROBABILITIES: {canonical_json(probabilities)}",
                "EXPLANATION: Deterministic fixture followed only a matching forward link.",
            )
        )
        outputs.append(
            {
                "trial_id": trial_id,
                "raw_response": raw,
                "transport_metadata": {
                    "source": "deterministic_public_smoke_fixture",
                    "model_called": False,
                    "network_used": False,
                },
            }
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, default=DEFAULT_REQUESTS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_RAW)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("study_kind") != "public_smoke_mock_dry_run":
        raise ValueError("deterministic mock responses are allowed only for public_smoke_mock_dry_run")
    runner = manifest.get("runner_bundle")
    if not isinstance(runner, dict) or runner.get("sha256") != sha256_file(args.requests):
        raise ValueError("runner request hash does not match frozen bundle manifest")
    records = make_records(read_jsonl(args.requests, "request"))
    write_text(args.output, jsonl_text(records))
    print(f"wrote {len(records)} deterministic mock responses; model calls=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
