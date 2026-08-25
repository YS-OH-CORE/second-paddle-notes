#!/usr/bin/env python3
"""Small, dependency-free helpers shared by the offline model-eval tools."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def jsonl_text(records: Iterable[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path, kind: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid {kind} JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: {kind} record must be an object")
            records.append(value)
    if not records:
        raise ValueError(f"{path}: no {kind} records")
    return records


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def require_exact_fields(record: dict[str, Any], required: set[str], optional: set[str], label: str) -> None:
    missing = required - set(record)
    extra = set(record) - required - optional
    if missing:
        raise ValueError(f"{label}: missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label}: unknown fields: {sorted(extra)}")


def unique_by(records: Iterable[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records, 1):
        value = record.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} record {index}: {key} must be a non-empty string")
        if value in result:
            raise ValueError(f"{label} record {index}: duplicate {key}: {value}")
        result[value] = record
    return result
