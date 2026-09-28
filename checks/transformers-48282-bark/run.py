# SPDX-License-Identifier: Apache-2.0
"""Run full source snapshots and one explicitly diagnostic two-line change."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


BASE = "2e703d6c7e81ec584c25edc39e8bd2f5a45b04bd"
HEAD = "f3e3ad778c38990d38100c44c74f2054b9b2aae6"
COMMON = "src/transformers/configuration_utils.py"
FILES = [COMMON, "src/transformers/models/bark/configuration_bark.py",
         "src/transformers/models/auto/configuration_auto.py",
         "src/transformers/models/auto/auto_mappings.py",
         "src/transformers/models/llava/configuration_llava.py"]


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def hashes(source):
    return {path: hashlib.sha256((source / path).read_bytes()).hexdigest() for path in FILES}


def run_phase(label, source, out):
    env = dict(os.environ, PYTHONPATH=str(source / "src"), CHECK_SOURCE=str(source),
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    script = Path(__file__).with_name("test_bark_config.py")
    with (out / f"{label}.stdout").open("w") as stdout, (out / f"{label}.stderr").open("w") as stderr:
        process = subprocess.run([sys.executable, str(script), str(out / f"{label}.json")],
                                 env=env, stdout=stdout, stderr=stderr, timeout=120, check=False)
    (out / f"{label}.exit-code.txt").write_text(str(process.returncode) + "\n")
    result = json.loads((out / f"{label}.json").read_text())
    result["exit_code"] = process.returncode
    result["source_hashes"] = hashes(source)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base, head, out = args.base.resolve(), args.head.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert git(base, "rev-parse", "HEAD") == BASE
    assert git(head, "rev-parse", "HEAD") == HEAD
    assert not git(base, "status", "--porcelain")
    assert not git(head, "status", "--porcelain")
    provenance = {"baseline_commit": BASE, "candidate_commit": HEAD,
                  "baseline_hashes": hashes(base), "candidate_hashes": hashes(head)}
    (out / "source-manifest.json").write_text(json.dumps(provenance, indent=2) + "\n")
    phases = {}
    phases["baseline"] = run_phase("baseline", base, out)
    phases["candidate"] = run_phase("candidate", head, out)
    target = head / COMMON
    original = target.read_bytes()
    anchor = "    def get_config_class(self, model_type: str | None = None):\n"
    addition = ("        if issubclass(self.config_class, PreTrainedConfig) and model_type == self.config_class.model_type:\n"
                "            return self.config_class\n")
    source_text = original.decode()
    assert source_text.count(anchor) == 1
    patched = source_text.replace(anchor, anchor + addition, 1)
    patch = "".join(difflib.unified_diff(source_text.splitlines(keepends=True), patched.splitlines(keepends=True),
                                       fromfile="a/" + COMMON, tofile="b/" + COMMON))
    (out / "diagnostic.patch").write_text(patch)
    try:
        target.write_text(patched)
        phases["diagnostic_patch"] = run_phase("diagnostic_patch", head, out)
    finally:
        target.write_bytes(original)
    assert target.read_bytes() == original
    assert not git(head, "status", "--porcelain")
    assert not git(base, "status", "--porcelain")
    summary = {**provenance, "phases": phases, "source_restored": True,
               "restored_candidate_hashes": hashes(head),
               "method": "Same environment; complete frozen checkouts via PYTHONPATH; fresh process for each phase",
               "diagnostic_patch_status": "Mechanism check only; not a validated fix for all 313 PR files"}
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    for label, result in phases.items():
        print(label, {key: result[key] for key in ("tests_run", "passed", "errors", "failures", "skipped", "exit_code")})
    for label in ("baseline", "diagnostic_patch"):
        result = phases[label]
        assert (result["tests_run"], result["passed"], result["errors"], result["failures"], result["skipped"], result["exit_code"]) == (12, 12, 0, 0, 0, 0)
    candidate = phases["candidate"]
    assert (candidate["tests_run"], candidate["passed"], candidate["errors"], candidate["failures"], candidate["skipped"], candidate["exit_code"]) == (12, 3, 9, 0, 0, 1)
    for test in candidate["tests"]:
        if test["status"] == "error":
            assert test["exception"] == "ValueError"
            assert test["message_prefix"].startswith("Unrecognized model type for subconfig: ")
    print("Expected configuration regression matrix observed; this is not the upstream PR CI result.")


if __name__ == "__main__":
    main()
