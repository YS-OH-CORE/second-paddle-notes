"""Exercise the frozen upstream scheduler; retain failures and one control."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


HEAD = "365706a27300453ba9218c1585a64a1f44b54254"
TEST = Path("tests/v1/kv_connector/unit/test_remote_prefill_lifecycle.py")
SCHEDULER = Path("vllm/v1/core/sched/scheduler.py")
RECEIPT = Path(os.environ["RUNNER_TEMP"]) / "vllm-abort-receipt"
SUPPORT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(name, value):
    (RECEIPT / name).write_text(json.dumps(value, indent=2) + "\n")


def run_case(name, selector=None):
    command = [sys.executable, "-m", "pytest", str(TEST), "-v", "--tb=short",
               f"--junitxml={RECEIPT / (name + '.xml')}"]
    if selector:
        command += ["-k", selector]
    start = time.monotonic()
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=360)
        code, log, timeout = result.returncode, result.stdout, False
    except subprocess.TimeoutExpired as exc:
        code, log, timeout = None, exc.stdout or "", True
        if isinstance(log, bytes):
            log = log.decode("utf-8", errors="replace")
    (RECEIPT / (name + ".log")).write_text(log)
    print(log, flush=True)
    cases = []
    xml = RECEIPT / (name + ".xml")
    if xml.exists():
        for case in ET.parse(xml).iter("testcase"):
            status = next((kind for kind in ("error", "failure", "skipped")
                           if case.find(kind) is not None), "passed")
            cases.append({"name": case.attrib.get("name"), "status": status})
    value = {"command": command, "exit_code": code, "timeout": timeout,
             "elapsed_seconds": time.monotonic() - start, "cases": cases}
    write_json(name + ".json", value)
    return value


def main():
    RECEIPT.mkdir(exist_ok=True)
    assert git("rev-parse", "HEAD") == HEAD
    assert not git("diff", "--name-only"), "Tracked sources changed during setup"
    source_paths = [SCHEDULER, TEST,
                    Path("tests/v1/kv_connector/unit/utils.py"),
                    Path("tests/v1/kv_connector/unit/conftest.py"),
                    Path("tests/conftest.py"),
                    Path("vllm/v1/core/kv_cache_manager.py"),
                    Path("vllm/v1/core/block_pool.py")]
    original_hashes = {str(p): digest(p) for p in source_paths}
    original_test = TEST.read_bytes()
    original_scheduler = SCHEDULER.read_bytes()
    addition = (SUPPORT / "test_addition.py").read_bytes()
    TEST.write_bytes(original_test + addition)
    (RECEIPT / "test_addition.py").write_bytes(addition)
    (RECEIPT / "test.patch").write_text(git("diff", "--", str(TEST)) + "\n")
    import torch
    import vllm.v1.core.sched.scheduler as scheduler_module

    assert Path(scheduler_module.__file__).resolve() == SCHEDULER.resolve()
    assert torch.version.cuda is None, "Expected a CPU-only torch build"
    write_json("inputs.json", {
        "upstream_head": HEAD, "upstream_tree": git("rev-parse", "HEAD^{tree}"),
        "source_sha256": original_hashes,
        "modified_test_sha256": digest(TEST), "addition_sha256": digest(SUPPORT / "test_addition.py"),
        "workflow_sha": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "scheduler_module_path": str(Path(scheduler_module.__file__).relative_to(Path.cwd())),
        "python": sys.version, "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p)
                     for p in ("vllm", "torch", "transformers", "pytest", "pytest-asyncio")},
        "scope": "Actual Scheduler, KV block pool and Nixl scheduler; existing synthetic runner completion signals. No model inference or device transfer.",
    })
    original = run_case("candidate")
    negative = None
    marker = b"            self.deferred_waiting.difference_update(waiting_requests_to_remove)\n"
    try:
        if original["exit_code"] == 0:
            assert original_scheduler.count(marker) == 1
            SCHEDULER.write_bytes(original_scheduler.replace(marker, b"", 1))
            negative = run_case("removed_deferred_cleanup", "test_aborted_remote_load_releases_capacity_after_receive")
    finally:
        SCHEDULER.write_bytes(original_scheduler)
    new_cases = [c for c in original["cases"]
                 if c["name"].startswith("test_aborted_remote_load_releases_capacity_after_receive[")]
    negative_valid = bool(negative and negative["exit_code"] == 1
                          and len(negative["cases"]) == 2
                          and all(c["status"] == "failure" for c in negative["cases"]))
    success = (original["exit_code"] == 0 and len(new_cases) == 2
               and all(c["status"] == "passed" for c in new_cases)
               and negative_valid)
    write_json("SUMMARY.json", {"candidate": original, "negative_control": negative,
                               "new_cases": new_cases, "expected_comparison_observed": success,
                               "restored_scheduler_sha256": digest(SCHEDULER),
                               "production_diff_after": git("diff", "--name-only", "--", "vllm")})
    assert SCHEDULER.read_bytes() == original_scheduler
    assert not git("diff", "--name-only", "--", "vllm")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
