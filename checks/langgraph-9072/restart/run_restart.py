"""Run bounded, separate-process checkpoint continuation experiments."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import email.utils
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

PIN = "7daa3ab49d678a5da75edb08baa87db4a2be52c3"
BLOB = "95e161b9078e3123afa1854247a5dfd132410a53"
CANDIDATE = "9051ab2c778e2f511257b13b7ed66d05e90dda07c5e7e69daaa34d1b88f14bfd"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def download(url, path):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Zero-checkpoint-regression"})
            with urllib.request.urlopen(req, timeout=40) as response:
                data = response.read(100_000_001)
            assert len(data) <= 100_000_000
            path.write_bytes(data)
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 502, 503) or attempt == 2:
                raise
            delay = 20 * (attempt + 1)
            retry = exc.headers.get("Retry-After")
            if retry:
                try:
                    delay = max(delay, float(retry))
                except ValueError:
                    delay = max(delay, (email.utils.parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds())
            if delay > 90:
                raise RuntimeError("Requested wait exceeds the bounded run budget") from exc
            time.sleep(delay)
    raise AssertionError("unreachable")


def assess(phase_reports, order, stage):
    seed, resume, inspect = phase_reports
    all_events = seed["events"] + resume["events"] + inspect["events"]
    tools = Counter(e["job"] for e in all_events if e["kind"] == "tool")
    completed = Counter(e["job"] for e in all_events if e["kind"] == "worker_complete")
    final = inspect["after"]["values"]
    expected = {"total": 5, "best": ["b", "c"], "visited": ["alpha", "beta"],
                "tool_ids": ["call-" + n for n in order],
                "message_ids": ["request"] + ["msg-" + n for n in order]}
    checks = {
        "three_distinct_processes": len({p["pid"] for p in phase_reports}) == 3,
        "seed_paused": len(seed["after"]["interrupts"]) == (1 if stage == "before" else 2),
        "reopened_pause_equals_saved_pause": resume["before"] == seed["after"],
        "inspector_equals_completed_checkpoint": inspect["before"] == resume["after"] == inspect["after"],
        "completed_with_no_pending_work": not inspect["after"]["next"] and not inspect["after"]["interrupts"],
        "all_handoff_tools_called_once": tools == Counter({"alpha": 1, "beta": 1}),
        "all_workers_complete_once": completed == Counter({"alpha": 1, "beta": 1}),
        "inspection_executes_no_nodes": not inspect["events"],
        "phase_boundary_handoff_counts": sum(e["kind"] == "tool" for e in seed["events"]) == (0 if stage == "before" else 2)
            and sum(e["kind"] == "tool" for e in resume["events"]) == (2 if stage == "before" else 0),
        "no_network_attempts": not any(p["network_attempts"] for p in phase_reports),
        "final_parent_contract": final == expected,
    }
    if stage == "after":
        paused = dict(seed["after"]["values"])
        paused["visited"] = final["visited"]
        checks["resume_does_not_reapply_handoff_updates"] = paused == final
    return {"checks": checks, "contract_met": all(checks.values()), "expected_final": expected,
            "actual_final": final, "pids": [p["pid"] for p in phase_reports],
            "tool_calls": dict(tools), "worker_completions": dict(completed)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    root, bundle = args.root.resolve(), args.bundle.resolve()
    root.mkdir(exist_ok=False)
    out = root / "output"
    out.mkdir()
    report = {"completed": False, "upstream_commit": PIN, "candidate_sha256": CANDIDATE,
              "run_id": os.environ.get("GITHUB_RUN_ID"), "workflow_commit": os.environ.get("GITHUB_SHA"),
              "cases": [], "model_calls": 0, "setup_network_only": True}
    source, original = None, None

    def call(argv, log, *, cwd=root, env=None, timeout=180):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        log.write_text("COMMAND " + repr(argv) + "\n" + result.stdout + "\nSTDERR\n" + result.stderr, encoding="utf-8")
        if result.returncode:
            print(result.stdout[-2000:] + result.stderr[-4000:], flush=True)
        result.check_returncode()
        return result

    try:
        manifest = json.loads((bundle / "MANIFEST.json").read_text())
        for name, digest in manifest.items():
            assert sha((bundle / name).read_bytes()) == digest, name
            shutil.copy2(bundle / name, out / name)
        shutil.copy2(bundle / "MANIFEST.json", out / "MANIFEST.json")
        report["manifest"] = manifest
        archive = root / "source.zip"
        report["source_archive_sha256"] = sha(download(f"https://codeload.github.com/langchain-ai/langgraph/zip/{PIN}", archive))
        with zipfile.ZipFile(archive) as z:
            assert all((root / n).resolve().is_relative_to(root) for n in z.namelist())
            z.extractall(root)
        repo = root / ("langgraph-" + PIN)
        source = repo / "libs/prebuilt/langgraph/prebuilt/tool_node.py"
        original = source.read_bytes()
        assert hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original).hexdigest() == BLOB
        call(["git", "apply", "--check", out / "compatibility_runtime.patch"], out / "patch_check.log", cwd=repo)
        call(["git", "apply", out / "compatibility_runtime.patch"], out / "patch_apply.log", cwd=repo)
        candidate = source.read_bytes()
        assert sha(candidate) == CANDIDATE
        shutil.copy2(repo / "LICENSE", out / "LICENSE.upstream")
        call([sys.executable, "-m", "venv", root / "venv"], out / "venv.log", timeout=30)
        py = root / "venv/bin/python"
        libs = [repo / "libs" / n for n in ("checkpoint", "sdk-py", "prebuilt", "langgraph", "checkpoint-sqlite")]
        call([py, "-m", "pip", "install", "--disable-pip-version-check", *libs,
              "langchain-core==1.6.5", "pydantic==2.13.5"], out / "installation.log", timeout=240)
        freeze = call([py, "-m", "pip", "freeze", "--all"], out / "freeze.log")
        (out / "environment.txt").write_text(freeze.stdout, encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, libs)), PYTHONDONTWRITEBYTECODE="1",
                   LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false")
        for key in list(env):
            if key.endswith("API_KEY"):
                env.pop(key, None)
        for variant, data in (("base", original), ("compatibility_candidate", candidate)):
            source.write_bytes(data)
            variant_dir = out / variant
            variant_dir.mkdir()
            (variant_dir / "tool_node.py").write_bytes(data)
            for stage in ("before", "after"):
                for api in ("sync", "async"):
                    for order in ("alpha,beta", "beta,alpha"):
                        case_id = f"{stage}_{api}_{order.replace(',', '_')}"
                        directory = variant_dir / case_id
                        directory.mkdir()
                        home = directory / "home"
                        home.mkdir()
                        phase_reports = []
                        for phase in ("seed", "resume", "inspect"):
                            path = directory / (phase + ".json")
                            call([py, "-B", out / "restart_probe.py", "--db", directory / "state.sqlite",
                                  "--phase", phase, "--stage", stage, "--api", api, "--order", order,
                                  "--source-module", source, "--source-sha256", sha(data), "--out", path],
                                 directory / (phase + ".log"), env={**env, "HOME": str(home)}, timeout=45)
                            phase_reports.append(json.loads(path.read_text()))
                        row = {"variant": variant, "case": case_id, "stage": stage, "api": api,
                               "order": order.split(","), **assess(phase_reports, order.split(","), stage)}
                        db = directory / "state.sqlite"
                        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection:
                            row["db_integrity"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
                            row["checkpoint_rows"] = connection.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
                        row.update(db_sha256=sha(db.read_bytes()), db_bytes=db.stat().st_size)
                        assert db.read_bytes()[:16] == b"SQLite format 3\0" and row["db_integrity"] == "ok"
                        report["cases"].append(row)
                        print(json.dumps(row), flush=True)
        assert len(report["cases"]) == 16
        report["completed"] = True
        report["scenario_count"] = 16
        report["graph_invocations"] = 32
        report["fresh_processes"] = 48
        report["observed_matrix_matches_expected"] = all(
            row["contract_met"] == (row["variant"] == "compatibility_candidate")
            and all(v for k, v in row["checks"].items() if k != "final_parent_contract")
            for row in report["cases"]
        )
    except Exception as exc:
        report["setup_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if original is not None:
            source.write_bytes(original)
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed": report["completed"], "matrix_matches": report.get("observed_matrix_matches_expected"),
                      "cases": len(report["cases"]), "error": report.get("setup_error")}))
    return 0 if report["completed"] and report["observed_matrix_matches_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
