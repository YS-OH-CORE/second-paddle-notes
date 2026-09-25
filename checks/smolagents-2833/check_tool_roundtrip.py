"""Supplemental smolagents #2833 serialization-boundary check.

Use a disposable checkout at REF. The coordinator temporarily changes one source
line and restores its bytes. Real tool decorator, to_dict/from_dict and save/load
are used. Only locally authored, inert fixture code is loaded; no Hub/model call.
Original diagnosis and removal proposal: BlueX888. Fixture and execution: Zero,
an AI collaborator with Youngseok Oh (@YS-OH-CORE).
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

REF = "227ef5e49ddd82339295939072f0223249aa8d38"
REL = "src/smolagents/tools.py"
BLOB = "931acfeccb6f2663b6c073bfa0fd8f0088c01eac"
LINE = '            forward_source_code = forward_source_code.replace(self.name, "forward")\n'
FIXTURES = '''from smolagents import Tool, tool

@tool
def search(query: str) -> str:
    """Build an inert demonstration address, without sending a request.

    Args:
        query: Input text.
    """
    return f"https://example.invalid/search?q={query}"

@tool
def label(label_value: str) -> str:
    """Return the supplied value.

    Args:
        label_value: Input text.
    """
    return label_value

@tool
def ward(value: str) -> str:
    """Return the supplied value.

    Args:
        value: Input text.
    """
    return value

@tool
def plain(value: str) -> str:
    """Return the supplied value.

    Args:
        value: Input text.
    """
    return value

class ClassControl(Tool):
    name = "search"
    description = "Build an inert demonstration address."
    inputs = {"query": {"type": "string", "description": "Input text."}}
    output_type = "string"

    def forward(self, query: str) -> str:
        return f"https://example.invalid/search?q={query}"
'''


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_local_module(path: Path):
    spec = importlib.util.spec_from_file_location("zero_inert_tool_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the authored fixture")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def code_shape(code: str) -> dict:
    tree = ast.parse(code)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    return {n.name: [a.arg for a in n.args.args] for n in classes[0].body if isinstance(n, ast.FunctionDef)}


def child(repo: Path, out: Path, mode: str) -> int:
    def no_network(*args, **kwargs):
        raise RuntimeError("No network belongs in these inert tool fixtures")
    socket.socket.connect = socket.socket.connect_ex = no_network
    sys.path.insert(0, str(repo / "src"))
    from smolagents import Tool
    import smolagents.tools as tools_module
    assert Path(inspect.getfile(tools_module)).resolve() == repo / REL
    folder = out / mode
    folder.mkdir()
    fixture_file = folder / "inert_fixtures.py"
    fixture_file.write_text(FIXTURES, encoding="utf-8")
    fixture = load_local_module(fixture_file)
    specs = [
        ("body_url", fixture.search, {"query": "cats"}, "https://example.invalid/search?q=cats"),
        ("keyword_parameter", fixture.label, {"label_value": "kept"}, "kept"),
        ("method_name_substring", fixture.ward, {"value": "kept"}, "kept"),
        ("decorated_control", fixture.plain, {"value": "kept"}, "kept"),
        ("subclass_control", fixture.ClassControl(), {"query": "cats"}, "https://example.invalid/search?q=cats"),
    ]
    report = {"mode": mode, "source_commit": REF, "started_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "smolagents": importlib.metadata.version("smolagents"),
              "source_sha256": sha((repo / REL).read_bytes()), "cases": [], "success": False,
              "network_requests": 0, "model_calls": 0, "live_hub_upload": False}

    def restore(loader, kwargs):
        try:
            restored = loader()
        except Exception as exc:
            return {"stage": "load", "error_type": type(exc).__name__, "error": str(exc)}
        try:
            return {"stage": "call", "value": restored(**kwargs)}
        except Exception as exc:
            return {"stage": "call", "error_type": type(exc).__name__, "error": str(exc)}

    try:
        for name, tool, kwargs, expected in specs:
            original = tool(**kwargs)
            assert original == expected
            before = deepcopy(tool.inputs)
            payload = tool.to_dict()
            path = folder / name
            path.mkdir()
            (path / "tool.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tool.save(path, make_gradio_app=False)
            saved = (path / "tool.py").read_text(encoding="utf-8")
            assert saved == payload["code"], "The two persistence paths produced different code"
            shape = code_shape(saved)
            outcomes = {"from_dict": restore(lambda: Tool.from_dict(payload), kwargs),
                        "saved_code": restore(lambda: Tool.from_code(saved), kwargs)}
            for observation in outcomes.values():
                if name == "keyword_parameter" and mode != "remove":
                    assert shape["forward"] == ["self", "forward_value"]
                    assert "error_type" in observation, observation
                elif name == "method_name_substring" and mode != "remove":
                    assert "forforward" in shape and "forward" not in shape
                    assert "error_type" in observation, observation
                elif name == "body_url" and mode != "remove":
                    assert observation == {"stage": "call", "value": "https://example.invalid/forward?q=cats"}
                else:
                    assert observation == {"stage": "call", "value": expected}, observation
            assert tool(**kwargs) == expected and tool.inputs == before
            row = {"case": name, "name": tool.name, "inputs": list(before), "saved_methods": shape,
                   "original": original, "outcomes": outcomes,
                   "roundtrip_preserved": all(x.get("value") == expected and "error_type" not in x for x in outcomes.values()),
                   "original_object_unchanged": True}
            report["cases"].append(row)
            print("TOOL_CASE " + json.dumps(row), flush=True)
        preserved = sum(r["roundtrip_preserved"] for r in report["cases"])
        assert preserved == (5 if mode == "remove" else 2)
        report["preserved_cases"] = preserved
        if mode == "remove":
            # Loading under fixed code does not reverse a string already changed at export.
            old = out / "base" / "body_url" / "tool.json"
            old_bytes = old.read_bytes()
            retained = restore(lambda: Tool.from_dict(json.loads(old_bytes)), {"query": "cats"})
            assert retained == {"stage": "call", "value": "https://example.invalid/forward?q=cats"}
            assert old.read_bytes() == old_bytes
            report["load_previously_exported_payload"] = {"observation": retained, "sha256": sha(old_bytes),
                "old_payload_unchanged": True, "automatic_repair": False}
        report["success"] = True
    except Exception as exc:
        report["unexpected_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        (out / (mode + ".json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("TOOL_REPORT " + json.dumps(report), flush=True)
    return 0 if report["success"] else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mode", choices=["base", "count_one", "remove"])
    args = p.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    if args.mode:
        return child(repo, out, args.mode)
    out.mkdir(parents=True, exist_ok=False)
    source = repo / REL
    original = source.read_bytes()
    assert hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original).hexdigest() == BLOB
    text = original.decode()
    assert text.count(LINE) == 1
    variants = {"base": text,
                "count_one": text.replace(LINE, LINE.replace('(self.name, "forward")', '(self.name, "forward", 1)'), 1),
                "remove": text.replace(LINE, "", 1)}
    result = {"source_commit": REF, "success": False, "phases": {}, "scope": "inert local tools only; no Agent or Hub execution"}
    try:
        for mode, content in variants.items():
            source.write_text(content, encoding="utf-8")
            patch = "".join(difflib.unified_diff(text.splitlines(True), content.splitlines(True), fromfile="a/"+REL, tofile="b/"+REL))
            (out / (mode + ".patch")).write_text(patch, encoding="utf-8")
            home = out / (mode + "-home")
            home.mkdir()
            env = {"PATH": os.environ["PATH"], "HOME": str(home), "LANG": "C.UTF-8",
                   "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"}
            run = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--repo", str(repo), "--out", str(out),
                                  "--mode", mode], env=env, cwd=home, text=True, capture_output=True, timeout=30)
            (out / (mode + ".stdout.txt")).write_text(run.stdout, encoding="utf-8")
            (out / (mode + ".stderr.txt")).write_text(run.stderr, encoding="utf-8")
            result["phases"][mode] = {"exit": run.returncode}
            print(run.stdout + run.stderr, flush=True)
            run.check_returncode()
        result["success"] = True
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        source.write_bytes(original)
        result["source_restored"] = source.read_bytes() == original
        (out / "summary.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print("TOOL_SUMMARY " + json.dumps(result), flush=True)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
