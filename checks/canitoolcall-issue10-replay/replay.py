# SPDX-License-Identifier: Apache-2.0
"""Replay the nine cases requested in CanIToolCall issue 10.

Youngseok Oh x Zero. Uses the original vLLM adapter, worker and evaluator.
No model generation, real tools, private messages, parser changes or new fixtures.
Tokenizer/configuration loading is preparation; both measured passes block Python
socket/DNS calls. A completed run does not mean the cases passed conformance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import traceback

PIN = "5670805d5b140230a323536c5de9a89091ad02d2"
EXPECTED_WHEEL = "ef52ee58c410ead0b8afb190838fa4cbcb52075596f67862a03859d984966ac4"
IDS = (
    "deepseek/vllm-v3-malformed-missing-brace",
    "deepseek/vllm-v3-malformed-missing-call-tokens",
    "gpt-oss/vllm-malformed-headers",
    "gpt-oss/bug-garbled-channel-commentary-question",
    "mistral/vllm-v3-malformed-not-json",
    "mistral/v13think-stop-at-open-marker",
    "qwen3-hermes/bug-sglang-30480-truncated-at-opener",
    "qwen3-hermes/sglang-malformed-json-in-tags",
    "qwen3-hermes/truncated-after-open-tag",
)


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo / "src"))
    report = {"completed": False, "source_commit": PIN, "phase": "imports",
              "model_calls": 0, "tool_executions": 0, "requested_fixtures": list(IDS),
              "run_id": os.getenv("GITHUB_RUN_ID"), "workflow_commit": os.getenv("GITHUB_SHA"),
              "started_utc": datetime.now(timezone.utc).isoformat(), "passes": []}
    calls, attempts = 0, []
    try:
        from canitoolcall import checks, runner
        from canitoolcall.adapters.base import ReplayInput
        from canitoolcall.adapters.vllm import VllmAdapter
        from canitoolcall.adapters.worker import replay
        from canitoolcall.chunking import DEFAULT_STRATEGIES
        from canitoolcall.fixtures import load_family, load_fixtures, validate
        import vllm

        assert Path(inspect.getfile(checks)).resolve() == repo / "src/canitoolcall/checks.py"
        adapter = VllmAdapter()
        assert adapter.version() == "0.30.0"
        details = adapter.engine_details()
        assert details.get("wheel_sha256") == EXPECTED_WHEEL, details
        report.update(engine_version=adapter.version(), engine_details=details, python=sys.version,
                      strategies=[s.id for s in DEFAULT_STRATEGIES])
        assert len(DEFAULT_STRATEGIES) == 8
        assert validate([repo / "fixtures"]) == []
        all_fixtures = load_fixtures([repo / "fixtures"])
        selected = {f.id: f for f in all_fixtures if f.id in IDS}
        assert len(selected) == len(IDS)
        fixtures = [selected[i] for i in IDS]
        families = {f.family: load_family(f.family, repo / "fixtures") for f in fixtures}
        save(out / "FIXTURES.json", [f.to_dict() for f in fixtures])
        save(out / "FAMILIES.json", {k: v.to_dict() for k, v in families.items()})
        source_hashes = {str(f.relative_to(repo)): sha(f.read_bytes())
                         for f in (repo / "src/canitoolcall").rglob("*.py")}
        save(out / "ADAPTER_SOURCE_HASHES.json", source_hashes)

        # Populate only tokenizer, parser imports, request and prompt caches.
        # No parse(), parse_delta(), worker replay, model or tool execution here.
        report["phase"] = "tokenizer_and_parser_preparation"
        prepared = []
        for f in fixtures:
            raw = ReplayInput.from_fixture(f, families[f.family])
            assert adapter.supports(raw.family, raw.model)
            setup = adapter._setup(raw, list(f.tools))
            for stream in (False, True):
                request, parser = adapter._request_and_parser(setup, stream=stream)
                # Load the real incremental detokenizer as well; no parser fed.
                adapter._detokenize(setup, request, [adapter.units(raw)])
            cfg = adapter.parser_config(raw)
            prepared.append({"id": f.id, "parser_config": cfg})
            print("PREPARED " + f.id, flush=True)
        save(out / "PREPARATION.json", prepared)

        # Preserve the unmodified parser sources, not the large engine wheel.
        engine_dir = Path(vllm.__file__).resolve().parent
        target = out / "engine_source"
        target.mkdir()
        for name in ("parser", "tool_parsers", "reasoning"):
            source_dir = engine_dir / name
            for f in source_dir.rglob("*.py"):
                dest = target / f.relative_to(engine_dir)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        extra = engine_dir / "entrypoints/openai/parser/harmony_utils.py"
        if extra.is_file():
            dest = target / "harmony_utils.py"
            shutil.copy2(extra, dest)
        save(out / "ENGINE_SOURCE_HASHES.json", {str(f.relative_to(target)): sha(f.read_bytes())
             for f in target.rglob("*.py")})

        hf = Path(os.environ["HF_HOME"])
        downloaded = {str(f.relative_to(hf)): {"bytes": f.stat().st_size, "sha256": sha(f.read_bytes())}
                      for f in hf.glob("hub/models--*/snapshots/*/*") if f.is_file()}
        assert not any(n.endswith((".safetensors", ".bin")) for n in downloaded), "Unexpected weights"
        save(out / "TOKENIZER_ASSET_HASHES.json", downloaded)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        def deny(*unused, **kw):
            attempts.append("blocked_socket_or_dns")
            raise RuntimeError("Network disabled during replay")

        socket.socket.connect = socket.socket.connect_ex = socket.getaddrinfo = deny
        report["phase"] = "offline_replay"
        passes = []
        for iteration in range(2):
            rows = []
            for f in fixtures:
                reply = replay(adapter, f, families[f.family], DEFAULT_STRATEGIES)
                assert reply.get("ok") and reply.get("supported"), reply
                assert not reply.get("skipped"), reply.get("skipped")
                assert set(reply["streams"]) == {s.id for s in DEFAULT_STRATEGIES}
                calls += 1 + len(reply["streams"])
                evaluated = runner.evaluate(f, families[f.family], reply)
                row = {"fixture": f.id, "reply": reply, "evaluated": evaluated.to_dict()}
                rows.append(row)
                save(out / f"PASS_{iteration + 1}.json", rows)
                print("CASE " + json.dumps({"pass": iteration + 1, "fixture": f.id,
                      "status": evaluated.status.value, "nonstream": reply["nonstream"],
                      "streams": reply["streams"]}, ensure_ascii=False), flush=True)
            passes.append(rows)
            report["passes"].append({"cases": len(rows), "statuses": dict(Counter(
                r["evaluated"]["status"] for r in rows))})
        equality = [{"fixture": a["fixture"], "all_observations_equal": a == b}
                    for a, b in zip(passes[0], passes[1], strict=True)]
        save(out / "REPEAT_CHECK.json", equality)
        assert all(r["all_observations_equal"] for r in equality), "Repeat variability retained"
        assert source_hashes == {str(f.relative_to(repo)): sha(f.read_bytes())
                                 for f in (repo / "src/canitoolcall").rglob("*.py")}
        assert not attempts, attempts
        report.update(completed=True, phase="complete", fixture_count=9,
                      repetitions=2, parser_replay_sessions=calls,
                      model_generation=False, server_http_execution=False,
                      repeated_observations_identical=True, source_unmodified=True)
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        (out / "ERROR.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        report.update(parser_replay_sessions=calls, network_attempts_during_measurement=len(attempts),
                      finished_utc=datetime.now(timezone.utc).isoformat())
        save(out / "SUMMARY.json", report)
        print("SUMMARY " + json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
