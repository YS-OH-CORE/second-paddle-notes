#!/usr/bin/env python3
"""Observe compound identity filters through real Mem0, Chroma, and SQLite.

Run in a fresh Python process against an explicit checkout. This script does not
install dependencies, patch Mem0 methods, or modify the selected checkout.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import logging
import os
import platform
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCOPES = {
    "user-agent": {"user_id": "alice", "agent_id": "agent-a"},
    "user-agent-run": {"user_id": "alice", "agent_id": "agent-a", "run_id": "run-a"},
}
IDENTITY_KEYS = ("user_id", "agent_id", "run_id")
SOURCE_FILES = (
    "mem0/memory/main.py",
    "mem0/memory/storage.py",
    "mem0/vector_stores/chroma.py",
    "mem0/vector_stores/langchain.py",
    "mem0/configs/vector_stores/chroma.py",
    "mem0/configs/vector_stores/langchain.py",
    "pyproject.toml",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_value(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return json_value(value.model_dump(mode="json"))
    if hasattr(value, "tolist"):
        return json_value(value.tolist())
    raise TypeError(f"Cannot serialize observed value of type {qualified_class(value)}")


def qualified_class(instance):
    return f"{type(instance).__module__}.{type(instance).__name__}"


def exception_record(exc):
    return {
        "type": qualified_class(exc),
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    }


class AdapterLogCapture(logging.Handler):
    """Retain the adapter's emitted errors without suppressing normal stderr logs."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append({"level": record.levelname, "logger": record.name, "message": record.getMessage()})


async def observe(function):
    started = time.perf_counter()
    capture = AdapterLogCapture()
    logger = logging.getLogger("mem0.vector_stores.langchain")
    logger.addHandler(capture)
    try:
        try:
            result = function()
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            operation = {"status": "raised", "exception": exception_record(exc)}
        else:
            try:
                operation = {"status": "returned", "value": json_value(result)}
            except Exception as exc:
                operation = {
                    "status": "serialization_error",
                    "returned_type": qualified_class(result),
                    "exception": exception_record(exc),
                }
    finally:
        logger.removeHandler(capture)
    operation["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    operation["adapter_logs"] = capture.records
    return operation


def returned(operation):
    return operation.get("status") == "returned"


def git_observation(repo, *arguments):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *arguments], text=True, capture_output=True, timeout=10, check=False
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"exception": exception_record(exc)}


def source_identity(repo):
    hashes = {}
    for relative in SOURCE_FILES:
        path = repo / relative
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {
        "repo": str(repo),
        "git_head": git_observation(repo, "rev-parse", "HEAD"),
        "git_status_tracked": git_observation(repo, "status", "--short", "--untracked-files=no"),
        "file_sha256": hashes,
    }


class UnusedEmbedder:
    """Allow construction but fail immediately if an observed operation calls a model."""

    def __init__(self, calls):
        self.calls = calls
        self.config = SimpleNamespace(embedding_dims=4)

    def embed(self, *args, **kwargs):
        self.calls.append("embed")
        raise AssertionError("Unexpected embedding call in listing/deletion-only harness")

    def embed_batch(self, *args, **kwargs):
        self.calls.append("embed_batch")
        raise AssertionError("Unexpected batch embedding call in listing/deletion-only harness")


class UnusedLLM:
    def __init__(self, calls):
        self.calls = calls

    def generate_response(self, *args, **kwargs):
        self.calls.append("generate_response")
        raise AssertionError("Unexpected LLM call in listing/deletion-only harness")


def fixture_records(scope_name):
    # With no run_id filter, another run remains in scope. The two-field fixture
    # deliberately includes a target in run-b to detect accidental run scoping.
    identities = {
        "target-0": ("alice", "agent-a", "run-a"),
        "target-1": ("alice", "agent-a", "run-b" if scope_name == "user-agent" else "run-a"),
        "outside-user": ("bob", "agent-a", "run-a"),
        "outside-agent": ("alice", "agent-b", "run-a"),
    }
    if scope_name == "user-agent":
        identities["outside-user-and-agent"] = ("bob", "agent-b", "run-c")
    else:
        identities["outside-run"] = ("alice", "agent-a", "run-b")
    records = {}
    for index, (memory_id, identity) in enumerate(identities.items()):
        document = f"Controlled compound-filter fixture {memory_id}."
        records[memory_id] = {
            "document": document,
            "metadata": {
                **dict(zip(IDENTITY_KEYS, identity)),
                "data": document,
                "hash": hashlib.md5(document.encode("utf-8")).hexdigest(),
                "created_at": "2026-10-18T00:00:00+00:00",
                "updated_at": "2026-10-18T00:00:00+00:00",
                "fixture": "mem0-compound-filters",
            },
            "embedding": [float(index + 1), 0.5, 0.25, 1.0],
        }
    return records


def matching_ids(records, filters):
    return sorted(
        memory_id
        for memory_id, record in records.items()
        if all(record["metadata"].get(key) == value for key, value in filters.items())
    )


def canonical_chroma_where(filters):
    # Independent fixed equality witness for this fixture; no Mem0 normalizer is
    # used to determine ground truth or to construct the public API arguments.
    return {"$and": [{key: {"$eq": value}} for key, value in filters.items()]}


def seed_collection(collection, records):
    ids = sorted(records)
    collection.add(
        ids=ids,
        embeddings=[records[memory_id]["embedding"] for memory_id in ids],
        documents=[records[memory_id]["document"] for memory_id in ids],
        metadatas=[records[memory_id]["metadata"] for memory_id in ids],
    )


def direct_snapshot(collection, records, *, where=None):
    raw = collection.get(ids=sorted(records), where=where, include=["documents", "metadatas"])
    found = {
        memory_id: {"document": raw["documents"][index], "metadata": raw["metadatas"][index]}
        for index, memory_id in enumerate(raw["ids"])
    }
    return {
        "collection_count": collection.count(),
        "records": found,
        "present_ids": sorted(found),
        "absent_known_ids": sorted(set(records) - set(found)),
    }


def snapshot_matches(operation, expected_ids, records, *, expected_collection_count=None):
    if not returned(operation):
        return False
    value = operation["value"]
    if value["present_ids"] != sorted(expected_ids):
        return False
    count = len(expected_ids) if expected_collection_count is None else expected_collection_count
    if value["collection_count"] != count:
        return False
    return all(
        value["records"][memory_id]
        == {"document": records[memory_id]["document"], "metadata": records[memory_id]["metadata"]}
        for memory_id in expected_ids
    )


def row_matches(row, memory_id, records):
    return (
        isinstance(row, dict)
        and row.get("id") == memory_id
        and row.get("memory") == records[memory_id]["document"]
        and all(row.get(key) == records[memory_id]["metadata"][key] for key in IDENTITY_KEYS)
    )


def get_all_matches(operation, expected_ids, records):
    if not returned(operation):
        return False
    value = operation["value"]
    if not isinstance(value, dict) or not isinstance(value.get("results"), list):
        return False
    rows = value["results"]
    if not all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in rows):
        return False
    if sorted(row["id"] for row in rows) != sorted(expected_ids):
        return False
    return all(row_matches(row, row["id"], records) for row in rows)


def nested_adapter_list_matches(operation, expected_ids, records):
    if not returned(operation):
        return False
    value = operation["value"]
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], list):
        return False
    rows = value[0]
    if not all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in rows):
        return False
    if sorted(row["id"] for row in rows) != sorted(expected_ids):
        return False
    return all(row.get("payload") == records[row["id"]]["metadata"] for row in rows)


async def read_known_ids(memory, records):
    return {
        memory_id: await observe(lambda memory_id=memory_id: memory.get(memory_id))
        for memory_id in sorted(records)
    }


def public_id_reads_match(operations, present_ids, records):
    for memory_id, operation in operations.items():
        if not returned(operation):
            return False
        if memory_id not in present_ids:
            if operation["value"] is not None:
                return False
        elif not row_matches(operation["value"], memory_id, records):
            return False
    return True


def history_snapshot(memory):
    rows = memory.db.connection.execute(
        "SELECT memory_id, event, is_deleted FROM history ORDER BY memory_id, id"
    ).fetchall()
    return [{"memory_id": row[0], "event": row[1], "is_deleted": row[2]} for row in rows]


async def run_case(runtime, adapter, api, scope_name, case_dir):
    filters = dict(SCOPES[scope_name])
    records = fixture_records(scope_name)
    target_ids = matching_ids(records, filters)
    survivor_ids = sorted(set(records) - set(target_ids))
    single_user_ids = matching_ids(records, {"user_id": "alice"})
    single_user_survivors = sorted(set(single_user_ids) - set(target_ids))
    where = canonical_chroma_where(filters)
    collection_name = f"compound-{adapter}-{api}-{uuid.uuid4().hex[:12]}"
    case = {
        "adapter": adapter,
        "api": api,
        "scope_name": scope_name,
        "filters": filters,
        "canonical_chroma_where": where,
        "fixture_records": records,
        "expected_target_ids": target_ids,
        "expected_survivor_ids": survivor_ids,
        "collection_name": collection_name,
        "history_path": str(case_dir / "history.sqlite3"),
        "started_at": utc_now(),
        "operations": {},
    }
    memory = None
    model_calls = []
    stage = "constructor"
    try:
        if target_ids != ["target-0", "target-1"] or len(survivor_ids) != 3:
            raise AssertionError("Fixture must have exactly two matching targets and three nonmatching controls")
        client = runtime["chromadb"].EphemeralClient(
            settings=runtime["ChromaSettings"](anonymized_telemetry=False)
        )
        if adapter == "native-chroma":
            vector_config = {
                "provider": "chroma",
                "config": {
                    "client": client,
                    "path": str(case_dir / "unused-native-path"),
                    "collection_name": collection_name,
                },
            }
        else:
            lc_client = runtime["LangchainChroma"](
                client=client, collection_name=collection_name, embedding_function=None
            )
            vector_config = {
                "provider": "langchain",
                "config": {"client": lc_client, "collection_name": collection_name},
            }
        config = {
            "vector_store": vector_config,
            "history_db_path": case["history_path"],
            "version": "v1.1",
        }
        memory_type = runtime["Memory"] if api == "sync" else runtime["AsyncMemory"]
        with (
            patch.object(
                runtime["main"].EmbedderFactory, "create", return_value=UnusedEmbedder(model_calls)
            ) as embed_factory,
            patch.object(runtime["main"].LlmFactory, "create", return_value=UnusedLLM(model_calls)) as llm_factory,
        ):
            memory = memory_type.from_config(config)
        case["constructor"] = {
            "status": "returned",
            "memory_class": qualified_class(memory),
            "adapter_class": qualified_class(memory.vector_store),
            "history_class": qualified_class(memory.db),
            "embedder_factory_calls": embed_factory.call_count,
            "llm_factory_calls": llm_factory.call_count,
            "history_file_created": Path(case["history_path"]).is_file(),
            "chroma_is_persistent": client.get_settings().is_persistent,
        }
        collection = (
            memory.vector_store.collection
            if adapter == "native-chroma"
            else memory.vector_store.client._collection
        )
        stage = "seed"
        seed_collection(collection, records)
        ops = case["operations"]
        ops["direct_chroma_before"] = await observe(lambda: direct_snapshot(collection, records))
        ops["direct_canonical_scope_before"] = await observe(
            lambda: direct_snapshot(collection, records, where=where)
        )
        ops["sqlite_history_before"] = await observe(lambda: history_snapshot(memory))
        if not snapshot_matches(ops["direct_chroma_before"], records, records):
            raise AssertionError("Full fixture was not initialized exactly")
        if not snapshot_matches(
            ops["direct_canonical_scope_before"], target_ids, records, expected_collection_count=len(records)
        ):
            raise AssertionError("Direct canonical equality filter did not select the two intended targets")
        if not returned(ops["sqlite_history_before"]) or ops["sqlite_history_before"]["value"] != []:
            raise AssertionError("Fresh SQLite history must start empty; fixture insertion bypasses ingestion")
        case["fixture_valid"] = True
        stage = "observations"
        # This diagnostic intentionally submits the same flat predicate directly
        # to the backend. Its exception/result is retained, not counted as a
        # failed Mem0 case or used as a substitute for observing the public API.
        ops["direct_flat_scope_before"] = await observe(
            lambda: direct_snapshot(collection, records, where=filters)
        )
        ops["adapter_compound_list_before"] = await observe(
            lambda: memory.vector_store.list(filters=dict(filters), top_k=20)
        )
        ops["get_all_compound_before"] = await observe(
            lambda: memory.get_all(filters=dict(filters), top_k=20)
        )
        ops["get_all_single_user_before"] = await observe(
            lambda: memory.get_all(filters={"user_id": "alice"}, top_k=20)
        )
        ops["get_known_ids_before"] = await read_known_ids(memory, records)
        ops["delete_all"] = await observe(lambda: memory.delete_all(**filters))
        ops["direct_chroma_after"] = await observe(lambda: direct_snapshot(collection, records))
        ops["direct_canonical_scope_after"] = await observe(
            lambda: direct_snapshot(collection, records, where=where)
        )
        ops["get_known_ids_after"] = await read_known_ids(memory, records)
        ops["get_all_compound_after"] = await observe(
            lambda: memory.get_all(filters=dict(filters), top_k=20)
        )
        ops["get_all_single_user_after"] = await observe(
            lambda: memory.get_all(filters={"user_id": "alice"}, top_k=20)
        )
        ops["sqlite_history_after"] = await observe(lambda: history_snapshot(memory))

        delete_ok = returned(ops["delete_all"]) and ops["delete_all"]["value"] == {
            "message": "Memories deleted successfully!"
        }
        expected_history = [
            {"memory_id": memory_id, "event": "DELETE", "is_deleted": 1} for memory_id in target_ids
        ]
        after = ops["direct_chroma_after"]
        case["checks"] = {
            "real_sqlite_created": case["constructor"]["history_file_created"],
            "embedded_ephemeral_chroma": case["constructor"]["chroma_is_persistent"] is False,
            "adapter_compound_list_before_exact_nested_targets": nested_adapter_list_matches(
                ops["adapter_compound_list_before"], target_ids, records
            ),
            "get_all_compound_before_exact_targets": get_all_matches(
                ops["get_all_compound_before"], target_ids, records
            ),
            "get_all_single_user_before_exact": get_all_matches(
                ops["get_all_single_user_before"], single_user_ids, records
            ),
            "public_known_id_reads_before_exact": public_id_reads_match(
                ops["get_known_ids_before"], records, records
            ),
            "delete_all_returned_success": delete_ok,
            "direct_state_after_exact_survivors": snapshot_matches(after, survivor_ids, records),
            "direct_canonical_scope_after_empty": snapshot_matches(
                ops["direct_canonical_scope_after"], [], records, expected_collection_count=len(survivor_ids)
            ),
            "public_known_id_reads_after_exact": public_id_reads_match(
                ops["get_known_ids_after"], survivor_ids, records
            ),
            "get_all_compound_after_empty": get_all_matches(ops["get_all_compound_after"], [], records),
            "get_all_single_user_after_exact": get_all_matches(
                ops["get_all_single_user_after"], single_user_survivors, records
            ),
            "real_delete_history_exact": (
                returned(ops["sqlite_history_after"]) and ops["sqlite_history_after"]["value"] == expected_history
            ),
            "no_model_calls": not model_calls,
        }
        before_listing = ops["get_all_compound_before"]
        case["listing_outcome"] = (
            "false_empty_target_records_present"
            if get_all_matches(before_listing, [], records)
            else "exact_targets"
            if case["checks"]["get_all_compound_before_exact_targets"]
            else "other_result_or_exception"
        )
        present_after = set(after.get("value", {}).get("present_ids", []))
        case["target_ids_remaining"] = sorted(present_after & set(target_ids)) if returned(after) else None
        case["control_ids_missing"] = sorted(set(survivor_ids) - present_after) if returned(after) else None
        if not returned(after):
            case["deletion_outcome"] = "state_observation_failed"
        elif delete_ok and case["target_ids_remaining"]:
            case["deletion_outcome"] = "false_success_target_records_remain"
        elif delete_ok and case["checks"]["direct_state_after_exact_survivors"]:
            case["deletion_outcome"] = "success_matches_stored_state"
        elif ops["delete_all"].get("status") == "raised":
            case["deletion_outcome"] = (
                "exception_with_observed_records_unchanged"
                if snapshot_matches(after, records, records)
                else "exception_with_observed_records_changed"
            )
        else:
            case["deletion_outcome"] = "returned_unexpected_result_or_state"
        case["all_checks_passed"] = all(case["checks"].values())
    except Exception as exc:
        case["harness_error"] = {"stage": stage, **exception_record(exc)}
        case["all_checks_passed"] = False
    finally:
        case["model_method_calls"] = model_calls
        if memory is not None:
            case["close"] = await observe(memory.close)
            if not returned(case["close"]):
                case["all_checks_passed"] = False
        case["finished_at"] = utc_now()
    return case


def dependency_versions():
    packages = (
        "mem0ai", "chromadb", "langchain-chroma", "langchain-community", "langchain-core",
        "pydantic", "qdrant-client", "openai", "posthog", "numpy", "sqlalchemy",
    )
    result = {}
    for name in packages:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def load_runtime(repo):
    sys.path.insert(0, str(repo))
    import chromadb
    from chromadb.config import Settings
    from langchain_chroma import Chroma
    from mem0 import AsyncMemory, Memory
    main = importlib.import_module("mem0.memory.main")
    imported_sources = {}
    for module_name in (
        "mem0.memory.main", "mem0.memory.storage", "mem0.vector_stores.chroma", "mem0.vector_stores.langchain"
    ):
        module = importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        path.relative_to(repo)
        imported_sources[module_name] = str(path)
    if main.MEM0_TELEMETRY is not False:
        raise AssertionError("MEM0_TELEMETRY was not disabled before import")
    return {
        "chromadb": chromadb,
        "ChromaSettings": Settings,
        "LangchainChroma": Chroma,
        "Memory": Memory,
        "AsyncMemory": AsyncMemory,
        "main": main,
        "imported_sources": imported_sources,
    }


async def run_matrix(args, fixture_root, report):
    runtime = load_runtime(args.repo)
    report["imported_sources"] = runtime["imported_sources"]
    report["langchain_chroma_class"] = f"{runtime['LangchainChroma'].__module__}.{runtime['LangchainChroma'].__name__}"
    report["dependency_versions"] = dependency_versions()
    report["delete_all_batch_size"] = runtime["main"].DELETE_ALL_BATCH_SIZE
    for adapter in args.adapters:
        for api in args.apis:
            for scope_name in args.scopes:
                case_dir = fixture_root / f"{adapter}-{api}-{scope_name}"
                case_dir.mkdir()
                case = await run_case(runtime, adapter, api, scope_name, case_dir)
                report["cases"].append(case)
                print(json.dumps({
                    "adapter": adapter,
                    "api": api,
                    "scope_name": scope_name,
                    "listing_outcome": case.get("listing_outcome", "harness_error"),
                    "deletion_outcome": case.get("deletion_outcome", "harness_error"),
                    "all_checks_passed": case["all_checks_passed"],
                }), file=sys.stderr, flush=True)


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument("--label", required=True, help="Label only; actual source SHA and file hashes are recorded")
    parser.add_argument("--output", type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument(
        "--adapters", nargs="+", choices=("native-chroma", "langchain-chroma"),
        default=["native-chroma", "langchain-chroma"],
    )
    parser.add_argument("--apis", nargs="+", choices=("sync", "async"), default=["sync", "async"])
    parser.add_argument("--scopes", nargs="+", choices=tuple(SCOPES), default=list(SCOPES))
    parser.add_argument(
        "--expect", choices=("observe", "pass"), default="observe",
        help="Observe retains behavioral failures with exit 0; pass requires all behavioral checks to pass",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path to preserve every run")
    report = {
        "schema": "mem0-real-chroma-compound-identity-filters/v1",
        "label": args.label,
        "started_at": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_identity": source_identity(args.repo),
        "expected_case_count": len(args.adapters) * len(args.apis) * len(args.scopes),
        "scope": {
            "real": [
                "Memory/AsyncMemory.from_config constructors", "VectorStoreFactory",
                "Mem0 native Chroma and Langchain adapters", "maintained langchain_chroma.Chroma",
                "embedded ephemeral Chroma", "temporary SQLiteManager", "get/get_all/delete_all methods",
            ],
            "test_doubles": ["unused EmbedderFactory.create result", "unused LlmFactory.create result"],
            "disabled": ["Mem0 telemetry and its notice path", "Chroma anonymized telemetry", "LangSmith tracing"],
            "fixture_setup": (
                "Direct Chroma collection.add with explicit IDs, documents, metadata and precomputed 4-D vectors; "
                "two targets and three out-of-scope records per case; no Memory.add or adapter insert calls"
            ),
            "state_witness": (
                "Direct Chroma collection.get(ids=all_known_fixture_ids) and count, independent canonical $and "
                "equality queries, per-ID public get, and real SQLite history; list() is not ground truth"
            ),
            "controls": (
                "Native adapter and single-user get_all reads; two-field targets span runs so run_id cannot "
                "silently become an implicit condition. Raw flat Chroma queries are diagnostic observations."
            ),
            "list_contract": (
                "Original main nested [rows] return shape; no PR #7647 flat-list edits or consumer edits"
            ),
            "not_tested": [
                "model inference", "ingestion/extraction", "search", "FAISS", "other LangChain backends",
                "persistent/restart behavior", "entity store cleanup", "1000-item batching boundary",
                "arbitrary metadata operators", "unsupported enumeration/None returns", "full upstream suite",
            ],
        },
        "cases": [],
    }
    try:
        if not (args.repo / "mem0/memory/main.py").is_file():
            raise FileNotFoundError(f"Not a Mem0 source checkout: {args.repo}")
        with tempfile.TemporaryDirectory(prefix="mem0-compound-filter-fixtures-") as directory:
            fixture_root = Path(directory)
            os.environ["MEM0_DIR"] = str(fixture_root / "mem0-config")
            os.environ["MEM0_TELEMETRY"] = "false"
            os.environ["ANONYMIZED_TELEMETRY"] = "False"
            os.environ["LANGSMITH_TRACING"] = "false"
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            asyncio.run(run_matrix(args, fixture_root, report))
    except Exception as exc:
        report["bootstrap_or_cleanup_error"] = exception_record(exc)
    report["source_identity_after"] = source_identity(args.repo)
    report["source_unchanged_during_run"] = report["source_identity"] == report["source_identity_after"]
    report["finished_at"] = utc_now()
    report["summary"] = {
        "case_count": len(report["cases"]),
        "passed_cases": sum(case.get("all_checks_passed", False) for case in report["cases"]),
        "failed_cases": sum(not case.get("all_checks_passed", False) for case in report["cases"]),
        "harness_error_cases": sum("harness_error" in case for case in report["cases"]),
        "false_empty_listing_cases": sum(
            case.get("listing_outcome") == "false_empty_target_records_present" for case in report["cases"]
        ),
        "false_success_deletion_cases": sum(
            case.get("deletion_outcome") == "false_success_target_records_remain" for case in report["cases"]
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids silently replacing observations, including during
    # an accidental repeated invocation with the same output destination.
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")
    print(json.dumps({"output": str(args.output), **report["summary"]}, ensure_ascii=False))
    if (
        "bootstrap_or_cleanup_error" in report
        or report["summary"]["harness_error_cases"]
        or not report["source_unchanged_during_run"]
        or report["summary"]["case_count"] != report["expected_case_count"]
    ):
        return 2
    if args.expect == "pass" and report["summary"]["failed_cases"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
