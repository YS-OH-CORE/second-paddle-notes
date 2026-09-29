"""Synthetic public-API deletion review. Zero x Youngseok Oh.

Run seed and probe in separate processes. Only LLM and embedding providers
are fixtures; SDK, prompt construction, SQLite and local Qdrant are real.
"""
import argparse
import asyncio
import copy
import hashlib
import importlib.metadata as metadata
import inspect
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import patch

P = argparse.ArgumentParser()
P.add_argument("--phase", choices=["seed", "probe"], required=True)
P.add_argument("--mode", choices=["sync", "async"], required=True)
P.add_argument("--out", type=Path, required=True)
P.add_argument("--case", default="all")
ARGS = P.parse_args()
ARGS.out.mkdir(parents=True, exist_ok=True)
os.environ["MEM0_TELEMETRY"] = "false"
os.environ["MEM0_DIR"] = str(ARGS.out / "profile")
OUTBOUND = []

def audit(event, arguments):
    if event == "socket.connect":
        sock, address = arguments
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in ("127.0.0.1", "::1"):
            OUTBOUND.append({"event": event, "destination": str(address)})
            raise RuntimeError("Review fixture forbids external network connections")

sys.addaudithook(audit)
from mem0 import Memory, AsyncMemory
from mem0.memory import main as runtime

USER = "review+u%26&=_영"
SCOPES = [
    {"user_id": USER, "agent_id": "a1", "run_id": "r1"},
    {"user_id": USER, "agent_id": "a1", "run_id": "r2"},
    {"user_id": USER, "agent_id": "a2", "run_id": "r1"},
    {"user_id": USER + "-other", "agent_id": "a1", "run_id": "r1"},
    {"user_id": "review-b", "agent_id": "a2", "run_id": "r2"},
]
CASES = {
    "user": {"user_id": USER},
    "user-run": {"user_id": USER, "run_id": "r1"},
    "user-agent": {"user_id": USER, "agent_id": "a1"},
    "exact": dict(SCOPES[0]),
    "agent": {"agent_id": "a1"},
    "run": {"run_id": "r1"},
    "agent-run": {"agent_id": "a1", "run_id": "r1"},
    "unmatched": {"user_id": "absent-user"},
    "empty-rejected": {},
    "raw-only": {"user_id": USER},
}

class RecordingLLM:
    def __init__(self):
        self.calls = []
        self.fact = None

    def generate_response(self, messages, **kwargs):
        self.calls.append(copy.deepcopy(messages))
        return json.dumps({"memory": [] if self.fact is None else [
            {"id": "0", "text": self.fact, "attributed_to": "user"}
        ]})

class SyntheticEmbeddings:
    config = SimpleNamespace(embedding_dims=8)

    def embed(self, text, *args, **kwargs):
        raw = hashlib.sha256(text.encode()).digest()
        return [(x + 1) / 256 for x in raw[:8]]

    def embed_batch(self, texts, *args, **kwargs):
        return [self.embed(text) for text in texts]

async def call(method, *args, **kwargs):
    result = method(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result

async def state_of(memory):
    vectors = []
    for uid in sorted({s["user_id"] for s in SCOPES}):
        result = await call(memory.get_all, filters={"user_id": uid}, top_k=100)
        vectors.extend(result["results"])
    raw = list(memory.db.connection.execute("SELECT session_scope, content FROM messages ORDER BY content"))
    return {"facts": sorted(v["memory"] for v in vectors), "raw": [list(r) for r in raw]}

async def run_case(name, filters):
    directory = ARGS.out / name
    if ARGS.phase == "seed":
        directory.mkdir(exist_ok=False)
    elif not (directory / "seed.json").exists():
        raise RuntimeError("A completed seed phase is required")
    llm = RecordingLLM()
    config = {
        "vector_store": {"provider": "qdrant", "config": {
            "path": str(directory / "vectors"), "collection_name": "synthetic_review",
            "embedding_model_dims": 8}},
        "history_db_path": str(directory / "history.db"),
    }
    cls = AsyncMemory if ARGS.mode == "async" else Memory
    with patch.object(runtime.LlmFactory, "create", return_value=llm), patch.object(
        runtime.EmbedderFactory, "create", return_value=SyntheticEmbeddings()
    ):
        memory = cls.from_config(config)
    result = {"case": name, "mode": ARGS.mode, "phase": ARGS.phase, "pid": os.getpid(),
              "filters": filters, "scopes": SCOPES, "observations": {}}
    markers = ["SYNTHETIC_OLD_%d_7452" % i for i in range(len(SCOPES))]
    expected_retained = [i for i, scope in enumerate(SCOPES)
                         if not filters or not all(scope.get(k) == v for k, v in filters.items())]
    try:
        if ARGS.phase == "seed":
            for i, scope in enumerate(SCOPES):
                llm.fact = None if name == "raw-only" else "synthetic_fact_%d" % i
                await call(memory.add, [{"role": "user", "content": markers[i]}], **scope)
            before = await state_of(memory)
            assert sorted(row[1] for row in before["raw"]) == sorted(markers)
            assert before["facts"] == ([] if name == "raw-only" else ["synthetic_fact_%d" % i for i in range(5)])
            rejected = False
            try:
                reply = await call(memory.delete_all, **filters)
            except ValueError as exc:
                if name != "empty-rejected":
                    raise
                rejected = True
                reply = {"exception": type(exc).__name__, "message": str(exc)}
            assert rejected == (name == "empty-rejected")
            after = await state_of(memory)
            result["observations"] = {"before": before, "after": after, "delete_reply": reply}
            result["checks"] = {
                "vector_retention": after["facts"] == ([] if name == "raw-only" else ["synthetic_fact_%d" % i for i in expected_retained]),
                "raw_retention": sorted(row[1] for row in after["raw"]) == sorted(markers[i] for i in expected_retained),
                "empty_filter_rejected": rejected == (name == "empty-rejected"),
            }
        else:
            seed = json.loads((directory / "seed.json").read_text(encoding="utf-8"))
            reopened = await state_of(memory)
            prompt_observations = []
            checks = {"new_process": seed["pid"] != os.getpid(),
                      "durable_state_matches": reopened == seed["observations"]["after"]}
            for i, scope in enumerate(SCOPES):
                llm.fact = "synthetic_new_fact_%d" % i
                before_calls = len(llm.calls)
                await call(memory.add, [{"role": "user", "content": "SYNTHETIC_FRESH_%d" % i}], **scope)
                assert len(llm.calls) == before_calls + 1
                prompt = json.dumps(llm.calls[-1], ensure_ascii=False)
                observed = [j for j, marker in enumerate(markers) if marker in prompt]
                expected = [i] if i in expected_retained else []
                checks["prompt_scope_%d" % i] = observed == expected
                prompt_observations.append({"scope": scope, "observed_old_marker_indices": observed,
                                            "expected_old_marker_indices": expected, "messages": llm.calls[-1]})
            after_new = await state_of(memory)
            checks["fresh_memories_stored"] = all("synthetic_new_fact_%d" % i in after_new["facts"] for i in range(5))
            result["observations"] = {"reopened": reopened, "prompts": prompt_observations, "after_new": after_new}
            result["checks"] = checks
        result["llm_fixture_call_count"] = len(llm.calls)
        result["passed"] = all(result["checks"].values())
    finally:
        # The SDK close() only closes SQLite at these pins; close Qdrant explicitly.
        for store in [memory.vector_store, getattr(memory, "_entity_store", None)]:
            if store is not None and hasattr(store, "client"):
                store.client.close()
        await call(memory.close)
    (directory / (ARGS.phase + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"case": name, "passed": result["passed"], "checks": result["checks"]}

async def main():
    rows = []
    for name, filters in CASES.items():
        if ARGS.case != "all" and name != ARGS.case:
            continue
        rows.append(await run_case(name, filters))
    assert not OUTBOUND, OUTBOUND
    report = {"phase": ARGS.phase, "mode": ARGS.mode, "pid": os.getpid(), "cases": rows,
              "outside_loopback_socket_attempts": OUTBOUND,
              "sdk_file": str(Path(runtime.__file__).resolve()),
              "packages": {n: metadata.version(n) for n in ["mem0ai", "qdrant-client", "pydantic", "openai", "httpx", "posthog"]}}
    (ARGS.out / (ARGS.phase + "-summary.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"phase": ARGS.phase, "mode": ARGS.mode, "passed": sum(r["passed"] for r in rows),
                      "failed": sum(not r["passed"] for r in rows), "cases": len(rows)}), flush=True)
    return 0 if all(r["passed"] for r in rows) else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
