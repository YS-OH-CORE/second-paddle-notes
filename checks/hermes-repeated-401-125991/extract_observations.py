#!/usr/bin/env python3
"""Extract corroborating observations from completed, retained Hermes 401 runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


def file_record(path: Path, relative_to: Path | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(relative_to) if relative_to else path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"sqlite_blob_hex": value.hex()}
    return value


def tool_rows(database: Path) -> list[dict[str, Any]]:
    # immutable=1 can omit uncheckpointed WAL rows. Read a private copy with
    # normal WAL handling so opening SQLite cannot alter the retained SHM file.
    with tempfile.TemporaryDirectory(prefix="hermes401-observations-") as tmp:
        copied = Path(tmp) / database.name
        for suffix in ("", "-wal", "-shm"):
            source = Path(str(database) + suffix)
            if source.exists():
                shutil.copyfile(source, Path(str(copied) + suffix))
        connection = sqlite3.connect(copied.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            return [
                {key: json_value(row[key]) for key in row.keys()}
                for row in connection.execute(
                    "SELECT * FROM messages WHERE role = 'tool' ORDER BY id"
                )
            ]
        finally:
            connection.close()


def parsed_payload(content: str) -> dict[str, Any]:
    # Same regex, flags and JSON decoding as mcp_plugins._helpers.payload().
    match = re.search(r"^\{.*\}$", content, re.M | re.S)
    if match is None:
        raise ValueError(f"no JSON payload in tool result: {content!r}")
    return json.loads(match.group(0))


def extract_fixture(log: Path, run: Path) -> dict[str, Any]:
    database = log.parent / "home" / ".hermes" / "state.db"
    inputs = [log, database]
    inputs.extend(
        sidecar for suffix in ("-wal", "-shm")
        if (sidecar := Path(str(database) + suffix)).exists()
    )
    before = [file_record(path, run) for path in inputs]
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    messages = [record["msg"] for record in records]
    calls = [m for m in messages if isinstance(m, dict) and m.get("method") == "tools/call"]
    after_first = messages[messages.index(calls[0]) + 1:] if calls else []
    initialization_after_first = [
        m for m in after_first
        if isinstance(m, dict) and m.get("method") in {"initialize", "server/discover"}
    ]
    rows = tool_rows(database)
    payloads = []
    for row in rows:
        try:
            payloads.append({"message_row_id": row["id"], "payload": parsed_payload(row["content"])})
        except (TypeError, ValueError) as error:
            payloads.append({"message_row_id": row["id"], "parse_error": str(error)})
    if before != [file_record(path, run) for path in inputs]:
        raise RuntimeError(f"retained inputs changed while extracting {log}")
    return {
        "fixture": str(log.parent.relative_to(run)),
        "source_files": before,
        "retained_inputs_unchanged": True,
        "http_inbound_records": records,
        "request_ids": [m["id"] for m in messages if isinstance(m, dict) and "id" in m and "method" in m],
        "tool_call_request_ids": [m["id"] for m in calls],
        "rejected_request_ids": [m["injected_401_for"] for m in messages if isinstance(m, dict) and "injected_401_for" in m],
        "initialization_after_first_call_count": len(initialization_after_first) if calls else None,
        "initialization_after_first_call": initialization_after_first,
        "raw_tool_message_rows": rows,
        "parsed_tool_payloads": payloads,
    }


def extract_run(run: Path) -> Path:
    run = run.resolve(strict=True)
    execution_file = run / "execution.json"
    execution = json.loads(execution_file.read_text(encoding="utf-8"))
    if "exitCode" not in execution or not execution.get("finishedAt"):
        raise ValueError(f"run is not recorded as completed: {run}")
    logs = sorted((run / "pytest").glob("unauth*/http_inbound.jsonl"))
    if not logs:
        raise ValueError(f"no retained unauthorized fixture logs: {run}")
    # pytest's unauthcurrent symlink, when present, is the same fixture.
    logs = list(dict.fromkeys(path.resolve(strict=True) for path in logs))
    result = {
        "schema_version": 1,
        "run": {key: execution.get(key) for key in (
            "label", "checkout", "head", "command", "exitCode", "startedAt", "finishedAt"
        )},
        "source_file_sha256_recorded_before_run": execution.get("inputSha256", {}),
        "execution_file": file_record(execution_file, run),
        "extractor_source": file_record(Path(__file__).resolve()),
        "provenance": {
            "database_role": "Corroboration only. These are persisted SQLite tool-message rows, not a captured provider request.",
            "pytest_assertions": "The frozen test calls tool_results(srv), which reads tool contents in the fake provider's final real main request; pytest assertions use those contents, not SQLite rows.",
            "database_read": "Copy retained state.db and existing WAL/SHM into a temporary directory; open the copy with SQLite URI mode=ro and PRAGMA query_only=ON. Hash retained inputs before and after. No retained fixture file is modified.",
            "payload_parser": {"pattern": r"^\{.*\}$", "flags": ["re.M", "re.S"], "decode": "json.loads(match.group(0))", "semantics_source": "tests/e2e/core/mcp_plugins/_helpers.py:payload"},
            "source_hash_origin": "execution.json inputSha256, recorded before the test run; files are not reinterpreted from a later checkout.",
            "sqlite_blob_encoding": "Raw BLOB columns are represented losslessly as {sqlite_blob_hex: hex_string}; other column values are unchanged.",
            "limits": [
                "The fixture does not retain the fake provider's final request as a separate file. This extractor does not reconstruct or independently re-assert that request.",
                "Tool rows are ordered by SQLite message id; HTTP calls are ordered by inbound log position. No identifier equivalence between provider tool-call ids and MCP request ids is assumed.",
                "This extractor records observed data and parsing errors; it does not produce a conformance verdict or rerun tests.",
            ],
        },
        "fixtures": [extract_fixture(log, run) for log in logs],
    }
    output = run / "observations.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directories", type=Path, nargs="+")
    args = parser.parse_args()
    for run in args.run_directories:
        print(extract_run(run))


if __name__ == "__main__":
    main()
