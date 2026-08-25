#!/usr/bin/env python3
"""Build the public, deterministic rule-use smoke dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CONDITIONS = ("correct", "shuffled", "reversed", "absent", "irrelevant_probe")
ID_SALT = "rule-use-smoke-v1-fixed-public-salt"

TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "template_id": "facility",
        "rules": (
            ("FAC_R1", "FAC_WATER_WET", "FAC_CLOSE_VALVE", "Water sensor reports wet", "Valve closure is confirmed", "Facility liquid-hazard isolation rule."),
            ("FAC_R2", "FAC_SMOKE_SEEN", "FAC_START_FANS", "Smoke sensor reports particles", "Exhaust fans report active", "Facility airborne-hazard control rule."),
            ("FAC_R3", "FAC_FREEZER_WARM", "FAC_MOVE_SAMPLES", "Freezer exceeds its limit", "Samples are logged in backup storage", "Cold-storage preservation rule."),
        ),
        "irrelevant": ("FAC_RAIN_OUTSIDE", "Rain is reported outside"),
        "ack": "FAC_ACK_ONLY",
    },
    {
        "template_id": "data",
        "rules": (
            ("DAT_R1", "DAT_CHECKSUM_FAIL", "DAT_QUARANTINE_FILE", "A file checksum fails", "The file is isolated from consumers", "Data-integrity containment rule."),
            ("DAT_R2", "DAT_QUOTA_SPIKE", "DAT_THROTTLE_WRITES", "Write quota spikes", "The write limiter reports active", "Write-capacity protection rule."),
            ("DAT_R3", "DAT_CLOCK_DRIFT", "DAT_SYNC_CLOCK", "Clock drift exceeds tolerance", "Clock offset returns within tolerance", "Distributed-time consistency rule."),
        ),
        "irrelevant": ("DAT_DARK_THEME", "A user enables dark theme"),
        "ack": "DAT_ACK_ONLY",
    },
    {
        "template_id": "support",
        "rules": (
            ("SUP_R1", "SUP_DUPLICATE_BILL", "SUP_HOLD_REFUND", "A duplicate bill is confirmed", "Refund remains held for review", "Duplicate-charge review rule."),
            ("SUP_R2", "SUP_ID_MISMATCH", "SUP_ESCALATE_ID", "Account identity details conflict", "Identity review receives the case", "Account-identity escalation rule."),
            ("SUP_R3", "SUP_LANGUAGE_GAP", "SUP_ROUTE_TRANSLATOR", "No shared support language is available", "A translator queue accepts the case", "Language-access routing rule."),
        ),
        "irrelevant": ("SUP_AVATAR_CHANGE", "A user changes an avatar"),
        "ack": "SUP_ACK_ONLY",
    },
    {
        "template_id": "factory",
        "rules": (
            ("MFG_R1", "MFG_GUARD_OPEN", "MFG_STOP_CELL", "A machine guard opens", "The production cell reports stopped", "Machine-access safety rule."),
            ("MFG_R2", "MFG_TORQUE_LOW", "MFG_REWORK_BATCH", "Fastener torque is below limit", "The batch enters the rework queue", "Assembly-quality recovery rule."),
            ("MFG_R3", "MFG_LABEL_MISMATCH", "MFG_HOLD_SHIPMENT", "Product and carton labels differ", "Shipment status reports held", "Shipment-identity control rule."),
        ),
        "irrelevant": ("MFG_BREAKROOM_LIGHT", "A breakroom light is switched on"),
        "ack": "MFG_ACK_ONLY",
    },
)


def links_for(template: dict[str, Any], condition: str) -> list[dict[str, str]]:
    triples = [(row[0], row[1], row[2]) for row in template["rules"]]
    if condition == "correct":
        return [
            {"direction": "rule_to_trigger_to_action", "rule_id": rule, "trigger_id": trigger, "action_id": action}
            for rule, trigger, action in triples
        ]
    if condition == "shuffled":
        actions = [action for _, _, action in triples]
        rotated = actions[1:] + actions[:1]
        return [
            {"direction": "rule_to_trigger_to_action", "rule_id": rule, "trigger_id": trigger, "action_id": action}
            for (rule, trigger, _), action in zip(triples, rotated)
        ]
    if condition == "reversed":
        return [
            {"direction": "action_to_trigger_to_rule", "rule_id": rule, "trigger_id": trigger, "action_id": action}
            for rule, trigger, action in triples
        ]
    if condition == "absent":
        return []
    if condition == "irrelevant_probe":
        return [
            {
                "direction": "rule_to_trigger_to_action",
                "rule_id": template["rules"][0][0],
                "trigger_id": template["irrelevant"][0],
                "action_id": template["ack"],
            }
        ]
    raise ValueError(f"unknown condition: {condition}")


def task_content(template: dict[str, Any], observed_event: str, condition: str) -> dict[str, Any]:
    rules = [
        {"rule_id": row[0], "text": row[5]}
        for row in template["rules"]
    ]
    triggers = [
        {"trigger_id": row[1], "example": row[3]}
        for row in template["rules"]
    ] + [{"trigger_id": template["irrelevant"][0], "example": template["irrelevant"][1]}]
    actions = [
        {"action_id": row[2], "check": row[4]}
        for row in template["rules"]
    ] + [
        {"action_id": template["ack"], "check": "The event is acknowledged without task action"},
        {"action_id": "NO_ACTION", "check": "No task action is taken"},
    ]
    return {
        "instruction": "Return exactly one action_id for the observed event.",
        "observed_event": observed_event,
        "rules": rules,
        "trigger_examples": triggers,
        "action_checks": actions,
        "verification_statement": "The returned value must exactly match one listed action_id.",
        "links": links_for(template, condition),
    }


def opaque_case_id(template_id: str, scope: str, condition: str) -> str:
    source = f"{ID_SALT}|{template_id}|{scope}|{condition}".encode("utf-8")
    return "RUE-" + hashlib.sha256(source).hexdigest()[:12].upper()


def build_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for template in TEMPLATES:
        primary_trigger = template["rules"][0][1]
        primary_action = template["rules"][0][2]
        for scope, observed_event, expected_action in (
            ("relevant", primary_trigger, primary_action),
            ("irrelevant", template["irrelevant"][0], "NO_ACTION"),
        ):
            for condition in CONDITIONS:
                case_id = opaque_case_id(template["template_id"], scope, condition)
                cases.append(
                    {
                        "case_id": case_id,
                        "task_content": task_content(template, observed_event, condition),
                    }
                )
                gold.append(
                    {
                        "case_id": case_id,
                        "template_id": template["template_id"],
                        "scope": scope,
                        "condition": condition,
                        "expected_action": expected_action,
                    }
                )
    cases.sort(key=lambda row: row["case_id"])
    gold.sort(key=lambda row: row["case_id"])
    return cases, gold


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records)


def expected_outputs() -> dict[Path, str]:
    cases, gold = build_records()
    return {
        DATA_DIR / "cases.jsonl": jsonl_text(cases),
        DATA_DIR / "gold.jsonl": jsonl_text(gold),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if committed data differs from generated data")
    args = parser.parse_args()

    outputs = expected_outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, text in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise SystemExit("stale or missing generated data: " + ", ".join(stale))
        print(f"dataset check passed: {len(build_records()[0])} cases")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
