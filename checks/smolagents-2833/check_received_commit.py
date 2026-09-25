"""Check BlueX888's exact smolagents #2833 commit, without editing its source.

Run against either of two disposable source worktrees with the same dependency
installation. Reuses the earlier inert fixtures byte-for-byte, adds a literal
`forward` name control, and runs the author's added test from its unchanged file.
No Hub, Agent, model or real endpoint. Zero with Youngseok Oh (@YS-OH-CORE).
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import socket
import sys
import xml.etree.ElementTree as ET

BASE = "227ef5e49ddd82339295939072f0223249aa8d38"
HEAD = "e643060410cf98bfcea022295e1b83ae65c2a17b"
BLOBS = {"base": "931acfeccb6f2663b6c073bfa0fd8f0088c01eac",
         "candidate": "f576d1b571251ffd3514c961d5474b18e8ecf03d"}
PRIOR_SHA256 = "62dd6a8a4f255817b3c9c198d75726b04d99a073ea00bc0d3b974bff4646f766"
TEST_BLOB = "eaf025863f4cb2126c3e7fabfde2f00f73ad741f"
TEST_NAME = "test_from_dict_roundtrip_preserves_tool_name_in_function_body"
EXTRA = '''
@tool
def forward(value: str) -> str:
    """Return an input unchanged.

    Args:
        value: Input text.
    """
    return value
'''


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import the authored fixture")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--prior-checker", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=["base", "candidate"], required=True)
    args = parser.parse_args()
    repo, candidate_repo = args.repo.resolve(), args.candidate_repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = repo / "src/smolagents/tools.py"
    original = source.read_bytes()
    assert blob(original) == BLOBS[args.mode]
    prior = args.prior_checker.read_bytes()
    assert sha(prior) == PRIOR_SHA256
    # Only retrieve the literal fixture text, not execute the previous runner.
    assignments = [node for node in ast.parse(prior).body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "FIXTURES" for t in node.targets)]
    assert len(assignments) == 1
    fixtures = ast.literal_eval(assignments[0].value)
    assert isinstance(fixtures, str)
    fixture_path = out / "inert_fixtures.py"
    fixture_path.write_text(fixtures + EXTRA, encoding="utf-8")
    sys.path.insert(0, str(repo / "src"))
    network_attempts: list[str] = []

    def deny_network(*_args, **_kwargs):
        network_attempts.append("socket connect attempted")
        raise RuntimeError("No network is permitted in this local tool check")

    socket.socket.connect = socket.socket.connect_ex = deny_network
    from smolagents import Tool
    import smolagents.tools as tools_module
    import pytest
    assert Path(inspect.getfile(tools_module)).resolve() == source
    fixture = load_module(fixture_path, "zero_received_fixture")
    specs = [
        ("body_url", fixture.search, {"query": "cats"}, "https://example.invalid/search?q=cats"),
        ("keyword_parameter", fixture.label, {"label_value": "kept"}, "kept"),
        ("method_name_substring", fixture.ward, {"value": "kept"}, "kept"),
        ("decorated_control", fixture.plain, {"value": "kept"}, "kept"),
        ("subclass_control", fixture.ClassControl(), {"query": "cats"}, "https://example.invalid/search?q=cats"),
        ("forward_name_control", fixture.forward, {"value": "kept"}, "kept"),
    ]
    report = {"source_commit": BASE if args.mode == "base" else HEAD, "mode": args.mode,
              "source_blob": blob(original), "started_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "prior_checker_sha256": sha(prior), "cases": [], "success": False,
              "scope": "real local tool serialization; exact author commit; no Agent, Hub or model",
              "old_export_recovery_retested": False}

    def restored_result(loader, kwargs):
        try:
            restored = loader()
        except Exception as exc:
            return {"stage": "load", "error_type": type(exc).__name__, "error": str(exc)}
        try:
            return {"stage": "call", "value": restored(**kwargs)}
        except Exception as exc:
            return {"stage": "call", "error_type": type(exc).__name__, "error": str(exc)}

    try:
        for name, instance, kwargs, expected in specs:
            before = deepcopy(instance.inputs)
            assert instance(**kwargs) == expected
            payload = instance.to_dict()
            folder = out / name
            folder.mkdir()
            (folder / "tool.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            instance.save(folder, make_gradio_app=False)
            saved = (folder / "tool.py").read_text(encoding="utf-8")
            assert saved == payload["code"]
            outcomes = {"from_dict": restored_result(lambda: Tool.from_dict(payload), kwargs),
                        "saved_code": restored_result(lambda: Tool.from_code(saved), kwargs)}
            preserved = all(o == {"stage": "call", "value": expected} for o in outcomes.values())
            should_preserve = args.mode == "candidate" or name in {
                "decorated_control", "subclass_control", "forward_name_control"}
            assert preserved == should_preserve, (name, outcomes)
            if args.mode == "base" and name == "body_url":
                assert all(o == {"stage": "call", "value": "https://example.invalid/forward?q=cats"}
                           for o in outcomes.values())
            if args.mode == "base" and name in {"keyword_parameter", "method_name_substring"}:
                assert all(o.get("stage") == "load" and o.get("error_type") == "Exception"
                           for o in outcomes.values()), outcomes
            assert instance.inputs == before and instance(**kwargs) == expected
            row = {"case": name, "preserved": preserved, "outcomes": outcomes,
                   "original_object_unchanged": True}
            report["cases"].append(row)
            print("EXACT_TOOL_CASE " + json.dumps(row), flush=True)

        test_file = candidate_repo / "tests/test_tools.py"
        test_bytes = test_file.read_bytes()
        assert blob(test_bytes) == TEST_BLOB
        classes = [c.name for c in ast.parse(test_bytes).body if isinstance(c, ast.ClassDef)
                   and any(isinstance(f, ast.FunctionDef) and f.name == TEST_NAME for f in c.body)]
        assert len(classes) == 1
        xml_file = out / "author_test.xml"
        # Select the unchanged author test; deliberately exclude repository conftest.
        # It needs no external fixture, provider or model. Imports were reviewed.
        exit_code = pytest.main(["-q", "--noconftest", "-o", "addopts=", "-o", "cache_dir=" + str(out / "pytest-cache"),
                                "--junitxml=" + str(xml_file),
                                f"{test_file}::{classes[0]}::{TEST_NAME}"])
        tree = ET.parse(xml_file)
        cases = tree.findall(".//testcase")
        errors = tree.findall(".//error")
        failures = tree.findall(".//failure")
        assert len(cases) == 1 and not errors and not tree.findall(".//skipped")
        assert int(exit_code) == (1 if args.mode == "base" else 0)
        assert len(failures) == (1 if args.mode == "base" else 0)
        if failures:
            assert "https://api.example.com/search?q={query}" in (failures[0].text or "")
        assert test_file.read_bytes() == test_bytes and source.read_bytes() == original
        assert not network_attempts
        report.update(author_test={"file_blob": TEST_BLOB, "method": TEST_NAME, "exit": int(exit_code),
                                   "failures": len(failures), "errors": 0, "conftest_loaded": False},
                      source_unchanged=True, network_connect_attempts=0,
                      preserved_cases=sum(c["preserved"] for c in report["cases"]), success=True)
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("EXACT_TOOL_REPORT " + json.dumps(report), flush=True)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
