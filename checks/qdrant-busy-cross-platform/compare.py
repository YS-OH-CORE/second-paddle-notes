"""Run pinned Qdrant deletion regressions without hiding pre-existing failures.

Zero × Youngseok Oh. This runner compares software behavior, not human review
or upstream acceptance. Source checkouts and dependency installation are external.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET

AUTHOR = "560d8c0d3b826bf2a8e3943fca27724332086500"
CANDIDATE = "01ed8bec882f1ee084a757d17f21069e4fe29700"
REGRESSION = "tests/test_local_busy_delete.py"
TEST_SHA256 = "8c4773bbc08b20bf411b150c5d61965482191c5f8876093567bc9305b3c5d703"
TEST_FILES = [REGRESSION, "tests/test_local_persistence.py", "tests/test_in_memory.py"]
EXPECTED_CASES = {
    f"test_busy_delete_does_not_commit_with_an_unrelated_write[{prefix}-{selector}-{client}]"
    for prefix in ("first-point", "committed-prefix")
    for selector in ("ids", "filter")
    for client in ("sync", "async")
}


def normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def clean_environment() -> dict[str, str]:
    allowed = {
        "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "TMPDIR", "APPDATA", "LOCALAPPDATA", "COMSPEC", "PATHEXT", "LD_LIBRARY_PATH",
    }
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONHASHSEED="0")
    return env


def parse_report(path: Path) -> dict:
    tests = ET.parse(path).findall(".//testcase")
    parsed = {}
    for case in tests:
        name = case.attrib["name"]
        key = case.attrib.get("classname", "") + "::" + name
        if key in parsed:
            raise ValueError(f"Duplicate test identity: {key}")
        failure = case.find("failure")
        error = case.find("error")
        status = "passed"
        text = ""
        if failure is not None:
            status, text = "failed", failure.text or ""
        if error is not None:
            status, text = "error", error.text or ""
        if case.find("skipped") is not None:
            status = "skipped"
        parsed[key] = {
            "name": name, "status": status,
            "observed_busy_state_mismatch": "pending_after_failure" in text,
        }
    return parsed


def verdict(before: dict, after: dict) -> dict:
    old_new = {k: v for k, v in before.items() if v["name"] in EXPECTED_CASES}
    new_new = {k: v for k, v in after.items() if v["name"] in EXPECTED_CASES}
    old_neighbors = {k: v["status"] for k, v in before.items() if k not in old_new}
    new_neighbors = {k: v["status"] for k, v in after.items() if k not in new_new}
    identities_match = set(before) == set(after)
    negative_control = (
        {v["name"] for v in old_new.values()} == EXPECTED_CASES
        and all(v["status"] == "failed" and v["observed_busy_state_mismatch"]
                for v in old_new.values())
    )
    repaired = (
        {v["name"] for v in new_new.values()} == EXPECTED_CASES
        and all(v["status"] == "passed" for v in new_new.values())
    )
    # No exclusion or xfail is added to pytest. Compare its actual outcomes.
    neighbors_preserved = old_neighbors == new_neighbors and bool(old_neighbors)
    return {
        "comparison_passed": identities_match and negative_control and repaired and neighbors_preserved,
        "same_test_identities": identities_match,
        "baseline_exposes_all_eight_state_mismatches": negative_control,
        "candidate_passes_all_eight": repaired,
        "neighbor_outcomes_unchanged": neighbors_preserved,
        "all_candidate_selected_tests_passed": bool(after) and all(v["status"] == "passed" for v in after.values()),
        "full_repository_suite_run": False,
        "candidate_remaining_nonpassing_tests": {
            k: v["status"] for k, v in after.items() if v["status"] != "passed"
        },
    }


def self_test() -> None:
    before = {n: {"name": n, "status": "failed", "observed_busy_state_mismatch": True} for n in EXPECTED_CASES}
    after = {n: {"name": n, "status": "passed", "observed_busy_state_mismatch": False} for n in EXPECTED_CASES}
    before["neighbor"] = after["neighbor"] = {"name": "neighbor", "status": "failed"}
    assert verdict(before, after)["comparison_passed"]
    assert not verdict(before, after)["all_candidate_selected_tests_passed"]
    missing = dict(after)
    missing.pop(next(iter(EXPECTED_CASES)))
    assert not verdict(before, missing)["comparison_passed"]
    changed = dict(after)
    changed["neighbor"] = {"name": "neighbor", "status": "error"}
    assert not verdict(before, changed)["comparison_passed"]
    wrong_failure = dict(before)
    name = next(iter(EXPECTED_CASES))
    wrong_failure[name] = {"name": name, "status": "failed", "observed_busy_state_mismatch": False}
    assert not verdict(wrong_failure, after)["comparison_passed"]
    print("Comparator self-tests passed: missing cases, new failures and unrelated red controls rejected.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.author is None or args.candidate is None or args.out is None:
        parser.error("--author, --candidate and --out are required")
    source = {"author": args.author.resolve(), "candidate": args.candidate.resolve()}
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    test = source["candidate"] / REGRESSION
    assert hashlib.sha256(normalized_bytes(test)).hexdigest() == TEST_SHA256
    for label, commit in (("author", AUTHOR), ("candidate", CANDIDATE)):
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source[label], text=True).strip()
        assert actual == commit, (label, actual)
        subprocess.run(["git", "diff", "--exit-code"], cwd=source[label], check=True)
    assert not (source["author"] / REGRESSION).exists()
    shutil.copyfile(test, source["author"] / REGRESSION)
    parsed, runs = {}, {}
    for label, folder in source.items():
        imported = subprocess.check_output(
            [sys.executable, "-c", "import qdrant_client;print(qdrant_client.__file__)"],
            cwd=folder, env=clean_environment(), text=True, timeout=30,
        ).strip()
        assert Path(imported).resolve().is_relative_to(folder), imported
        xml = out / f"{label}.xml"
        command = [sys.executable, "-m", "pytest", *TEST_FILES, "-q", "--tb=short",
                   "--timeout=30", f"--junitxml={xml}"]
        result = subprocess.run(command, cwd=folder, env=clean_environment(),
                                capture_output=True, text=True, encoding="utf-8", timeout=240)
        (out / f"{label}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        assert result.returncode in (0, 1), (label, result.returncode)
        parsed[label] = parse_report(xml)
        runs[label] = {"exit_code": result.returncode, "tests": len(parsed[label]),
                       "passed": sum(v["status"] == "passed" for v in parsed[label].values())}
        subprocess.run(["git", "diff", "--exit-code"], cwd=folder, check=True)
        assert hashlib.sha256(normalized_bytes(folder / REGRESSION)).hexdigest() == TEST_SHA256
    result = verdict(parsed["author"], parsed["candidate"])
    receipt = {
        "author_commit": AUTHOR, "candidate_commit": CANDIDATE,
        "regression_sha256_lf": TEST_SHA256, "platform": platform.platform(),
        "python": sys.version, "sqlite": sqlite3.sqlite_version,
        "runs": runs, **result,
        "meaning": "A green comparison requires eight real failures repaired and unchanged neighbor outcomes. It does not imply all selected tests passed or upstream approval.",
    }
    text = json.dumps(receipt, ensure_ascii=False, indent=2)
    (out / "receipt.json").write_text(text + "\n", encoding="utf-8")
    freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True, timeout=30)
    freeze = "\n".join(line for line in freeze.splitlines() if not line.startswith("qdrant-client @"))
    (out / "environment.txt").write_text(freeze + "\n", encoding="utf-8")
    print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## Qdrant deletion: differential result, not a universal suite pass\n\n```json\n" + text + "\n```\n")
    return 0 if result["comparison_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
