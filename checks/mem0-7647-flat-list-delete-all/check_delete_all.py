#!/usr/bin/env python3
"""Observe Mem0 PR #7647 through real constructors, adapters, Chroma and SQLite.

This script does not install dependencies, patch Mem0 methods, or change a checkout.
Run it in a fresh Python process for each checkout. See README.md for scope.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.metadata
import inspect
import json
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


SCENARIOS = {
    "empty_store": (0, 0),
    "no_alice": (0, 1),
    "single_alice": (1, 1),
    "populated": (3, 1),
}
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
    raise TypeError(f"Cannot serialize observed value of type {type(value).__module__}.{type(value).__name__}")


def exception_record(exc):
    return {
        "type": f"{type(exc).__module__}.{type(exc).__name__}",
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    }


async def observe(function):
    started = time.perf_counter()
    try:
        result = function()
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        return {
            "status": "raised",
            "exception": exception_record(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    try:
        value = json_value(result)
    except Exception as exc:
        return {
            "status": "serialization_error",
            "returned_type": qualified_class(result),
            "exception": exception_record(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    return {
        "status": "returned",
        "value": value,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def returned(operation):
    return operation.get("status") == "returned"


def qualified_class(instance):
    return f"{type(instance).__module__}.{type(instance).__name__}"


def git_observation(repo, *arguments):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
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
    """A constructor dependency that fails if the tested operations use a model."""

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


def fixture_records(alice_count, bob_count):
    records = {}
    for owner, count in (("alice", alice_count), ("bob", bob_count)):
        for index in range(count):
            memory_id = f"{owner}-{index}"
            document = f"Controlled fixture {memory_id}; owner {owner}."
            records[memory_id] = {
                "document": document,
                "metadata": {
                    "user_id": owner,
                    "data": document,
                    "hash": hashlib.md5(document.encode("utf-8")).hexdigest(),
                    "created_at": "2026-10-18T00:00:00+00:00",
                    "updated_at": "2026-10-18T00:00:00+00:00",
                    "fixture": "mem0-pr7647",
                },
                "embedding": [float(index + 1), 0.5, 0.25, 1.0],
            }
    return records


def seed_collection(collection, records):
    """Seed real Chroma directly; ingestion/model extraction is outside this check."""
    ids = sorted(records)
    if ids:
        collection.add(
            ids=ids,
            embeddings=[records[memory_id]["embedding"] for memory_id in ids],
            documents=[records[memory_id]["document"] for memory_id in ids],
            metadatas=[records[memory_id]["metadata"] for memory_id in ids],
        )


def known_id_snapshot(collection, records):
    """Read fixture IDs directly from Chroma, never via the list() being tested."""
    ids = sorted(records)
    kwargs = {"ids": ids} if ids else {}
    raw = collection.get(include=["documents", "metadatas"], **kwargs)
    found = {}
    for index, memory_id in enumerate(raw["ids"]):
        found[memory_id] = {
            "document": raw["documents"][index],
            "metadata": raw["metadatas"][index],
        }
    return {
        "collection_count": collection.count(),
        "records": found,
        "present_ids": sorted(found),
        "absent_known_ids": sorted(set(records) - set(found)),
        "alice_present": sorted(memory_id for memory_id in found if memory_id.startswith("alice-")),
        "bob_present": sorted(memory_id for memory_id in found if memory_id.startswith("bob-")),
    }


def snapshot_matches(snapshot, expected_ids, records):
    if not returned(snapshot):
        return False
    value = snapshot["value"]
    if value["present_ids"] != sorted(expected_ids) or value["collection_count"] != len(expected_ids):
        return False
    return all(
        value["records"][memory_id]
        == {"document": records[memory_id]["document"], "metadata": records[memory_id]["metadata"]}
        for memory_id in expected_ids
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
    if sorted(row.get("id", "") for row in rows) != sorted(expected_ids):
        return False
    return all(
        row.get("memory") == records[row["id"]]["document"]
        and row.get("user_id") == records[row["id"]]["metadata"]["user_id"]
        for row in rows
    )


async def read_known_ids(memory, records):
    return {
        memory_id: await observe(lambda memory_id=memory_id: memory.get(memory_id))
        for memory_id in sorted(records)
    }


def public_id_reads_match(operations, present_ids, records):
    for memory_id, operation in operations.items():
        if not returned(operation):
            return False
        value = operation["value"]
        if memory_id not in present_ids:
            if value is not None:
                return False
        elif not isinstance(value, dict) or any(
            (
                value.get("id") != memory_id,
                value.get("memory") != records[memory_id]["document"],
                value.get("user_id") != records[memory_id]["metadata"]["user_id"],
            )
        ):
            return False
    return True


def history_snapshot(memory):
    rows = memory.db.connection.execute(
        "SELECT memory_id, event, is_deleted FROM history ORDER BY memory_id, id"
    ).fetchall()
    return [{"memory_id": row[0], "event": row[1], "is_deleted": row[2]} for row in rows]


async def run_case(runtime, adapter, api, scenario, case_dir):
    alice_count, bob_count = SCENARIOS[scenario]
    records = fixture_records(alice_count, bob_count)
    alice_ids = sorted(memory_id for memory_id in records if memory_id.startswith("alice-"))
    bob_ids = sorted(memory_id for memory_id in records if memory_id.startswith("bob-"))
    collection_name = f"pr7647-{adapter}-{api}-{uuid.uuid4().hex[:12]}"
    case = {
        "adapter": adapter,
        "api": api,
        "scenario": scenario,
        "fixture_counts": {"alice": alice_count, "bob": bob_count},
        "collection_name": collection_name,
        "history_path": str(case_dir / "history.sqlite3"),
        "started_at": utc_now(),
        "operations": {},
    }
    memory = None
    model_calls = []
    stage = "constructor"
    try:
        client = runtime["chromadb"].EphemeralClient(
            settings=runtime["ChromaSettings"](anonymized_telemetry=False)
        )
        if adapter == "native-chroma":
            vector_config = {
                "provider": "chroma",
                "config": {
                    "client": client,
                    # ChromaDbConfig requires a path even when an existing client wins.
                    "path": str(case_dir / "unused-native-path"),
                    "collection_name": collection_name,
                },
            }
        else:
            lc_client = runtime["LangchainChroma"](
                client=client,
                collection_name=collection_name,
                embedding_function=None,
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
        ops["direct_chroma_before"] = await observe(lambda: known_id_snapshot(collection, records))
        if not snapshot_matches(ops["direct_chroma_before"], records, records):
            raise AssertionError("The fixture was not initialized exactly; this case cannot test deletion")
        case["fixture_valid"] = True
        stage = "observations"
        ops["adapter_list_before"] = await observe(
            lambda: memory.vector_store.list(filters={"user_id": "alice"}, top_k=20)
        )
        ops["get_all_before"] = await observe(lambda: memory.get_all(filters={"user_id": "alice"}, top_k=20))
        ops["get_known_ids_before"] = await read_known_ids(memory, records)
        ops["delete_all"] = await observe(lambda: memory.delete_all(user_id="alice"))
        ops["direct_chroma_after"] = await observe(lambda: known_id_snapshot(collection, records))
        ops["get_known_ids_after"] = await read_known_ids(memory, records)
        ops["get_all_after"] = await observe(lambda: memory.get_all(filters={"user_id": "alice"}, top_k=20))
        ops["get_all_bob_after"] = await observe(lambda: memory.get_all(filters={"user_id": "bob"}, top_k=20))
        ops["sqlite_history_after"] = await observe(lambda: history_snapshot(memory))

        delete_ok = (
            returned(ops["delete_all"])
            and ops["delete_all"]["value"] == {"message": "Memories deleted successfully!"}
        )
        raw_after = ops["direct_chroma_after"]
        after_value = raw_after.get("value", {})
        expected_history = [
            {"memory_id": memory_id, "event": "DELETE", "is_deleted": 1} for memory_id in alice_ids
        ]
        case["checks"] = {
            "real_sqlite_created": case["constructor"]["history_file_created"],
            "embedded_ephemeral_chroma": case["constructor"]["chroma_is_persistent"] is False,
            "get_all_before_exact_alice": get_all_matches(ops["get_all_before"], alice_ids, records),
            "public_known_id_reads_before_exact": public_id_reads_match(ops["get_known_ids_before"], records, records),
            "delete_all_returned_success": delete_ok,
            "direct_state_after_exact_bob_only": snapshot_matches(raw_after, bob_ids, records),
            "public_known_id_reads_after_exact": public_id_reads_match(ops["get_known_ids_after"], bob_ids, records),
            "get_all_after_empty_alice": get_all_matches(ops["get_all_after"], [], records),
            "get_all_after_exact_bob": get_all_matches(ops["get_all_bob_after"], bob_ids, records),
            "real_delete_history_exact": (
                returned(ops["sqlite_history_after"])
                and ops["sqlite_history_after"]["value"] == expected_history
            ),
            "no_model_calls": not model_calls,
        }
        if not returned(raw_after):
            case["outcome"] = "state_observation_failed"
        elif delete_ok and after_value.get("alice_present"):
            case["outcome"] = "false_success_target_records_remain"
        elif delete_ok and case["checks"]["direct_state_after_exact_bob_only"]:
            case["outcome"] = "success_matches_stored_state"
        elif ops["delete_all"].get("status") == "raised":
            case["outcome"] = (
                "exception_with_vector_state_unchanged"
                if snapshot_matches(raw_after, records, records)
                else "exception_with_vector_state_changed"
            )
        else:
            case["outcome"] = "returned_unexpected_result_or_state"
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
            for scenario in args.scenarios:
                case_dir = fixture_root / f"{adapter}-{api}-{scenario}"
                case_dir.mkdir()
                case = await run_case(runtime, adapter, api, scenario, case_dir)
                report["cases"].append(case)
                progress = {
                    "adapter": adapter,
                    "api": api,
                    "scenario": scenario,
                    "outcome": case.get("outcome", "harness_error"),
                    "checks_passed": case["all_checks_passed"],
                }
                print(json.dumps(progress), file=sys.stderr, flush=True)


def main():
    # Import the selected source without leaving __pycache__ files in its checkout.
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument(
        "--label", required=True, help="Human label only; actual Git SHA and file hashes are recorded"
    )
    parser.add_argument("--output", type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument(
        "--adapters", nargs="+", choices=("native-chroma", "langchain-chroma"),
        default=["native-chroma", "langchain-chroma"],
    )
    parser.add_argument("--apis", nargs="+", choices=("sync", "async"), default=["sync", "async"])
    parser.add_argument("--scenarios", nargs="+", choices=tuple(SCENARIOS), default=list(SCENARIOS))
    parser.add_argument(
        "--expect", choices=("observe", "pass"), default="observe",
        help="Observe records regressions without exit 1; pass requires every behavioral check to pass",
    )
    args = parser.parse_args()
    report = {
        "schema": "mem0-pr7647-real-chroma-delete-all/v1",
        "label": args.label,
        "started_at": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_identity": source_identity(args.repo),
        "scope": {
            "real": [
                "Memory/AsyncMemory.from_config constructors", "VectorStoreFactory",
                "Mem0 native Chroma and Langchain adapters", "embedded ephemeral Chroma",
                "temporary SQLiteManager", "get/get_all/delete_all methods",
            ],
            "test_doubles": ["unused EmbedderFactory.create result", "unused LlmFactory.create result"],
            "disabled": ["Mem0 telemetry and its notice path", "Chroma anonymized telemetry", "LangSmith tracing"],
            "fixture_setup": (
                "Direct Chroma collection.add with explicit IDs, document text, metadata and precomputed vectors; "
                "Memory.add and adapter insert are not tested"
            ),
            "state_witness": (
                "Chroma collection.get(ids=known_fixture_ids) plus collection.count; "
                "no list() fallback used for ground truth"
            ),
            "not_tested": [
                "model inference", "ingestion/extraction", "FAISS", "Elasticsearch",
                "entity store cleanup", "batch boundary above 1000", "full upstream suite",
                "unsupported enumeration/None returns and backend listing failures",
            ],
        },
        "cases": [],
    }
    try:
        if not (args.repo / "mem0/memory/main.py").is_file():
            raise FileNotFoundError(f"Not a Mem0 source checkout: {args.repo}")
        with tempfile.TemporaryDirectory(prefix="mem0-pr7647-fixtures-") as directory:
            fixture_root = Path(directory)
            os.environ["MEM0_DIR"] = str(fixture_root / "mem0-config")
            os.environ["MEM0_TELEMETRY"] = "false"
            os.environ["ANONYMIZED_TELEMETRY"] = "False"
            os.environ["LANGSMITH_TRACING"] = "false"
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            asyncio.run(run_matrix(args, fixture_root, report))
    except Exception as exc:
        report["bootstrap_or_cleanup_error"] = exception_record(exc)
    report["finished_at"] = utc_now()
    report["summary"] = {
        "case_count": len(report["cases"]),
        "passed_cases": sum(case.get("all_checks_passed", False) for case in report["cases"]),
        "failed_cases": sum(not case.get("all_checks_passed", False) for case in report["cases"]),
        "harness_error_cases": sum("harness_error" in case for case in report["cases"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_name(args.output.name + ".tmp")
    temporary_output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary_output.replace(args.output)
    print(json.dumps({"output": str(args.output), **report["summary"]}, ensure_ascii=False))
    if "bootstrap_or_cleanup_error" in report or report["summary"]["harness_error_cases"]:
        return 2
    if args.expect == "pass" and report["summary"]["failed_cases"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
