#!/usr/bin/env python3
"""Install a built wheel offline into a fresh venv and use its actual CLI.

Only public repository fixtures are read. No model or external account is called.
The output directory must be new. A finished run verifies packaging/integration,
not semantic fidelity or language-model performance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv
import zipfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(wheel: Path, out: Path, repo: Path) -> dict:
    if os.name != "posix":
        raise RuntimeError("The tool supports POSIX; this integration is tested on Linux")
    wheel, repo = wheel.resolve(strict=True), repo.resolve(strict=True)
    package = repo / "tools/process-receipt"
    harness = repo / "experiments/rule-use-eval"
    source_files = [package / "process_receipt.py", harness / "run_baseline.py",
                    harness / "score.py", harness / "data/cases.jsonl",
                    harness / "data/gold.jsonl",
                    harness / "results/link-following.predictions.jsonl",
                    harness / "results/link-following.metrics.json"]
    before = {str(p.relative_to(repo)): digest(p.read_bytes()) for p in source_files}
    # Include only the module plus package metadata, not unrelated repository data.
    with zipfile.ZipFile(wheel) as archive:
        if archive.testzip() is not None:
            raise ValueError("Wheel CRC failure")
        if archive.read("process_receipt.py") != source_files[0].read_bytes():
            raise ValueError("Packaged module differs from checked-out source")
        modules = [n for n in archive.namelist() if n.endswith(".py")]
        if modules != ["process_receipt.py"]:
            raise ValueError("Unexpected Python modules in wheel")
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work = out / "outside-source"; work.mkdir()
    results = out / "results"; results.mkdir()
    environment = out / "clean-venv"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None); env.pop("PYTHONHOME", None)
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    py = environment / "bin/python"
    cli = environment / "bin/process-receipt"
    transcript = []

    def command(args: list[str], expected: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run([str(x) for x in args], cwd=work, env=env,
                                capture_output=True, text=True, timeout=30, check=False)
        transcript.append({"args": [str(x) for x in args], "returncode": result.returncode,
                           "stdout": result.stdout, "stderr": result.stderr})
        (results / "commands.json").write_text(json.dumps(transcript, indent=2) + "\n")
        if result.returncode != expected:
            raise RuntimeError(f"Command returned {result.returncode}, expected {expected}; see commands.json")
        return result

    command([py, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "install",
             "--no-index", "--no-deps", "--no-cache-dir", wheel])
    info = json.loads(command([py, "-I", "-c",
        "import importlib.metadata as m,json,process_receipt,sys; "
        "print(json.dumps({'module':process_receipt.__file__,"
        "'version':m.version('second-paddle-process-receipt'),"
        "'requires':m.requires('second-paddle-process-receipt') or [],"
        "'python':sys.version,'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"]).stdout)
    installed_module = Path(info["module"]).resolve()
    if (info["version"] != "0.1.0" or info["requires"] or
        not installed_module.is_relative_to(environment.resolve()) or
        info["prefix"] == info["base_prefix"]):
        raise AssertionError("Import did not come from the fresh dependency-free installation")
    if digest(installed_module.read_bytes()) != before["tools/process-receipt/process_receipt.py"]:
        raise AssertionError("Installed code differs from source")
    command([cli, "--help"])
    command([py, "-I", "-m", "process_receipt", "--help"])

    # Real use of the installed command on the repository's existing public software workload.
    predictions = results / "predictions.jsonl"
    metrics = results / "metrics.json"
    for name, job in [
        ("baseline", [py, "-I", harness / "run_baseline.py", "--baseline", "link-following", "--output", predictions]),
        ("scoring", [py, "-I", harness / "score.py", "--predictions", predictions, "--output", metrics]),
    ]:
        receipt_path = results / (name + ".receipt.json")
        command([cli, "--receipt", receipt_path, "--timeout", "10", "--", *job])
        receipt = json.loads(receipt_path.read_bytes())
        if not (receipt["status"] == "completed" and receipt["child_exit_code"] == 0 and
                receipt["direct_child_exit_observed"] and receipt.get("finished_at")):
            raise AssertionError("Missing completed direct-child receipt")
    for actual, reference in [(predictions, source_files[5]), (metrics, source_files[6])]:
        if actual.read_bytes() != reference.read_bytes():
            raise AssertionError("Installed-command workload output differs from repository fixture")

    # Verify that installing did not turn old stop/failure conditions into success.
    stop = results / "STOP"; stop.write_text("installation check; do not start")
    marker = results / "must-not-exist"
    stopped_receipt = results / "pre-stopped.receipt.json"
    command([cli, "--receipt", stopped_receipt, "--stop-file", stop, "--", py, "-I", "-c",
             f"from pathlib import Path; Path({str(marker)!r}).touch()"], expected=2)
    stopped = json.loads(stopped_receipt.read_bytes())
    if stopped["task_started"] or stopped["status"] != "not_started" or marker.exists():
        raise AssertionError("A pre-stopped installed command executed")
    failed_receipt = results / "failed.receipt.json"
    command([cli, "--receipt", failed_receipt, "--", py, "-I", "-c", "raise SystemExit(7)"], expected=2)
    failed = json.loads(failed_receipt.read_bytes())
    if failed["status"] != "failed" or failed["child_exit_code"] != 7:
        raise AssertionError("Failed child was not preserved by installed entrypoint")
    before_receipt = stopped_receipt.read_bytes()
    command([cli, "--receipt", stopped_receipt, "--", py, "-I", "-c",
             f"from pathlib import Path; Path({str(marker)!r}).touch()"], expected=2)
    if stopped_receipt.read_bytes() != before_receipt or marker.exists():
        raise AssertionError("Existing receipt was overwritten or a blocked command ran")
    after = {str(p.relative_to(repo)): digest(p.read_bytes()) for p in source_files}
    if after != before:
        raise AssertionError("Existing source/fixture changed")
    summary = {"schema": "process-receipt-installed-integration-v1", "status": "verified",
        "observed_at": datetime.now(timezone.utc).isoformat(), "wheel": wheel.name,
        "wheel_bytes": wheel.stat().st_size, "wheel_sha256": digest(wheel.read_bytes()),
        "installation": info, "cli_entrypoint_used": True, "outside_source_directory": True,
        "wheel_source_and_installed_code_identical": True, "source_hashes": before,
        "source_unchanged_after_run": True, "cases_processed": len(predictions.read_text().splitlines()),
        "predictions_equal_committed_fixture": True, "metrics_equal_committed_fixture": True,
        "prestop_prevented_execution": True, "nonzero_exit_preserved": True,
        "existing_receipt_preserved": True,
        "output_hashes": {p.name: digest(p.read_bytes()) for p in results.iterdir() if p.is_file()},
        "limits": ["Author-run package integration, not external adoption or independent replication.",
                   "Existing deterministic software fixture, not a language-model evaluation.",
                   "Wheel install used --no-index --no-deps; network traffic was not separately monitored.",
                   "No general process isolation, instant cancellation or semantic fidelity claim."]}
    (results / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    verify(args.wheel, args.out, args.repo)
