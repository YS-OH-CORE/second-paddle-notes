"""Reproduce issue 9072 using an isolated full LangGraph checkout and venv."""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

PIN = "7daa3ab49d678a5da75edb08baa87db4a2be52c3"
TOOL_BLOB = "95e161b9078e3123afa1854247a5dfd132410a53"
PROBE_SHA = "86b4a500e79568eae246894d70b6b59893e7a714477f800119627b99319b68c1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(url, dest, limit=100_000_000):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Zero-scoped-regression"})
            with urllib.request.urlopen(req, timeout=40) as response:
                data = response.read(limit + 1)
            assert len(data) <= limit
            dest.write_bytes(data)
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 502, 503) or attempt == 2:
                raise
            retry = exc.headers.get("Retry-After", "")
            wait = max(20 * (attempt + 1), float(retry)) if retry.isdecimal() else 30 * (attempt + 1)
            if wait > 90:
                raise RuntimeError("Server requests a wait beyond this bounded run") from exc
            time.sleep(wait)
    raise AssertionError("unreachable")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(exist_ok=False)
    out = root / "output"
    out.mkdir()
    probe = args.probe.resolve()
    assert digest(probe.read_bytes()) == PROBE_SHA
    (out / "probe.py").write_bytes(probe.read_bytes())
    (out / "run.py").write_bytes(Path(__file__).read_bytes())
    summary = {"completed": False, "upstream_commit": PIN, "probe_sha256": PROBE_SHA,
               "run_id": os.environ.get("GITHUB_RUN_ID"), "workflow_commit": os.environ.get("GITHUB_SHA"),
               "variants": [], "model_calls": 0}

    def call(argv, *, env=None, timeout=180, required=True):
        p = subprocess.run(list(map(str, argv)), cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
        with (out / "execution.log").open("a", encoding="utf-8") as f:
            f.write("COMMAND " + str(argv) + "\n" + p.stdout + "\nSTDERR\n" + p.stderr + "\n")
        print(p.stdout[-6000:] + p.stderr[-2000:], flush=True)
        if required:
            p.check_returncode()
        return p

    source_module = None
    original = None
    try:
        archive = root / "source.zip"
        data = download(f"https://codeload.github.com/langchain-ai/langgraph/zip/{PIN}", archive)
        summary["source_archive_sha256"] = digest(data)
        with zipfile.ZipFile(archive) as z:
            assert all((root / n).resolve().is_relative_to(root) for n in z.namelist())
            z.extractall(root)
        repo = root / ("langgraph-" + PIN)
        source_module = repo / "libs/prebuilt/langgraph/prebuilt/tool_node.py"
        raw = source_module.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert blob == TOOL_BLOB
        original = raw.decode("utf-8")
        (out / "tool_node.original.py").write_bytes(raw)
        (out / "LICENSE.upstream").write_bytes((repo / "LICENSE").read_bytes())
        call([sys.executable, "-m", "venv", root / "venv"], timeout=30)
        py = root / "venv/bin/python"
        libs = [repo / "libs" / name for name in ("checkpoint", "sdk-py", "prebuilt", "langgraph")]
        call([py, "-m", "pip", "install", "--disable-pip-version-check", *libs], timeout=240)
        (out / "environment.txt").write_text(call([py, "-m", "pip", "freeze", "--all"]).stdout, encoding="utf-8")
        fresh = "parent_command = Command(graph=Command.PARENT, goto=output.goto)"
        goto = 'goto=cast("list[Send]", parent_command.goto) + output.goto,'
        check = "output.graph is Command.PARENT"
        assert all(original.count(s) == 1 for s in (fresh, goto, check))
        first = original.replace(fresh, "parent_command = output")
        helper = '''\n\ndef _zero_structural_merge(left, right):\n    merged = dict(left or {})\n    for key, value in (right or {}).items():\n        old = merged.get(key)\n        merged[key] = old + value if isinstance(old, list) and isinstance(value, list) else value\n    return merged\n'''
        variants = {
            "base": original,
            "first_only": first,
            "separate_commands": original.replace(check, "False and " + check),
            "structural_merge": first.replace(goto, goto + "\n                            update=_zero_structural_merge(parent_command.update, output.update),") + helper,
            "ordered_writes": first.replace(goto, goto + "\n                            update=parent_command._update_as_tuples() + output._update_as_tuples(),"),
        }
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, libs)), PYTHONDONTWRITEBYTECODE="1",
                   LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false")
        for key in list(env):
            if key.endswith("API_KEY") or key in ("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"):
                env.pop(key, None)
        for name, text in variants.items():
            ast.parse(text)
            target = out / name
            target.mkdir()
            source_module.write_text(text, encoding="utf-8")
            (target / "tool_node.py").write_text(text, encoding="utf-8")
            (target / "experimental.diff").write_text("".join(difflib.unified_diff(
                original.splitlines(True), text.splitlines(True), fromfile="base/tool_node.py", tofile=name + "/tool_node.py"
            )), encoding="utf-8")
            result = call([py, "-B", probe, "--variant", name, "--source-module", source_module,
                           "--out", target / "report.json"], env=env, timeout=90, required=False)
            (target / "execution.log").write_text(result.stdout + "\nSTDERR\n" + result.stderr, encoding="utf-8")
            if (target / "report.json").exists():
                report = json.loads((target / "report.json").read_text())
                assert report["source_sha256"] == digest(text.encode("utf-8"))
                summary["variants"].append(report)
            result.check_returncode()
        summary.update(completed=True, count=sum(v["count"] for v in summary["variants"]),
                       note="Preservation failures are intentional observations; no upstream fix is claimed.")
    except Exception as exc:
        summary["setup_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if source_module is not None and original is not None:
            source_module.write_text(original, encoding="utf-8")
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print("SUMMARY " + json.dumps(summary), flush=True)
    return 0 if summary["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
