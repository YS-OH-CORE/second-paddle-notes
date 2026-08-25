#!/usr/bin/env python3
"""Run deterministic baselines for the rule-use smoke evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "data" / "cases.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            records.append(record)
    return records


def link_following_action(content: dict[str, Any]) -> str:
    observed = content["observed_event"]
    candidates = [
        link["action_id"]
        for link in content["links"]
        if link.get("direction") == "rule_to_trigger_to_action"
        and link.get("trigger_id") == observed
    ]
    return sorted(candidates)[0] if candidates else "NO_ACTION"


def link_ignoring_action(content: dict[str, Any]) -> str:
    del content
    return "NO_ACTION"


def model_payload(case: dict[str, Any]) -> dict[str, Any]:
    """Return the only object a model-facing adapter is allowed to receive."""
    return case["task_content"]


def generate_predictions(cases: Iterable[dict[str, Any]], baseline: str) -> list[dict[str, str]]:
    function = {
        "link-following": link_following_action,
        "link-ignoring": link_ignoring_action,
    }[baseline]
    return [{"case_id": case["case_id"], "action": function(model_payload(case))} for case in cases]


def write_jsonl(path: Path, records: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, choices=("link-following", "link-ignoring"))
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    predictions = generate_predictions(read_jsonl(args.cases), args.baseline)
    write_jsonl(args.output, predictions)
    print(f"wrote {len(predictions)} predictions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
