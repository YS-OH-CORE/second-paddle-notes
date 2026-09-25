"""Run an unchanged upstream ToolNode test module and a portable regression pack."""
import argparse
import ast
import difflib
import email.utils
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

PIN = "7daa3ab49d678a5da75edb08baa87db4a2be52c3"
TOOL_BLOB = "95e161b9078e3123afa1854247a5dfd132410a53"
TEST_BLOB = "47ebdcae0d936167649c0d33103650388d290a9a"
CANDIDATE_SHA = "be4a47872cfd4764a3fcc3ae0e093295706a87f3b5d9960ab6dd6ebb8645ab8c"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def nonimport_ast(text):
    tree = ast.parse(text)
    tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    return ast.dump(tree, include_attributes=False)


def download(url, target):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Zero-regression-pack"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read(100_000_001)
            assert len(data) <= 100_000_000
            target.write_bytes(data)
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
            if delay > 60:
                raise RuntimeError("Server retry interval exceeds this bounded run") from exc
            time.sleep(delay)
    raise AssertionError("unreachable")


def parse_junit(path):
    cases = []
    for element in ET.parse(path).getroot().iter("testcase"):
        failure, error, skipped = element.find("failure"), element.find("error"), element.find("skipped")
        status = "error" if error is not None else "failed" if failure is not None else "skipped" if skipped is not None else "passed"
        item = {"id": element.attrib.get("classname", "") + "::" + element.attrib["name"], "status": status}
        problem = error if error is not None else failure
        if problem is not None:
            item.update(message=problem.attrib.get("message"), detail=problem.text)
        cases.append(item)
    return {"count": len(cases), "passed": sum(c["status"] == "passed" for c in cases),
            "failed": sum(c["status"] == "failed" for c in cases),
            "errors": sum(c["status"] == "error" for c in cases),
            "skipped": sum(c["status"] == "skipped" for c in cases), "tests": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    root, bundle = args.root.resolve(), args.bundle.resolve()
    root.mkdir(exist_ok=False)
    out = root / "output"
    out.mkdir()
    report = {"completed": False, "pin": PIN, "run_id": os.environ.get("GITHUB_RUN_ID"),
              "workflow_commit": os.environ.get("GITHUB_SHA"), "runs": []}
    source, original = None, None

    def call(argv, logfile, cwd=root, env=None, timeout=180, required=True):
        p = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        logfile.write_text("COMMAND " + str(argv) + "\n" + p.stdout + "\nSTDERR\n" + p.stderr, encoding="utf-8")
        print(p.stdout[-2200:] + p.stderr[-2200:], flush=True)
        if required:
            p.check_returncode()
        return p

    try:
        for name in ("test_parent_command_handoff.py", "offline_guard.py", "run_pack.py", "PROTOCOL.md", "MANIFEST.json"):
            shutil.copy2(bundle / name, out / name)
        manifest = json.loads((bundle / "MANIFEST.json").read_text())
        for name, expected in manifest.items():
            assert sha((bundle / name).read_bytes()) == expected, name
        report["bundle_hashes"] = manifest
        archive = root / "upstream.zip"
        report["archive_sha256"] = sha(download(f"https://codeload.github.com/langchain-ai/langgraph/zip/{PIN}", archive))
        with zipfile.ZipFile(archive) as z:
            assert all((root / n).resolve().is_relative_to(root) for n in z.namelist())
            z.extractall(root)
        repo = root / ("langgraph-" + PIN)
        lib = repo / "libs/prebuilt"
        source = lib / "langgraph/prebuilt/tool_node.py"
        upstream_test = lib / "tests/test_tool_node.py"
        assert blob(source.read_bytes()) == TOOL_BLOB
        assert blob(upstream_test.read_bytes()) == TEST_BLOB
        original = source.read_text()
        shutil.copy2(source, out / "tool_node.original.py")
        shutil.copy2(upstream_test, out / "test_tool_node.upstream.py")
        shutil.copy2(repo / "LICENSE", out / "LICENSE.upstream")
        call([sys.executable, "-m", "venv", root / "venv"], out / "venv.log", timeout=30)
        py = root / "venv/bin/python"
        libs = [repo / "libs" / n for n in ("checkpoint", "sdk-py", "prebuilt", "langgraph", "checkpoint-sqlite", "checkpoint-postgres")]
        call([py, "-m", "pip", "install", "--disable-pip-version-check", *libs,
              "langchain-core==1.6.5", "pytest==8.4.2", "pytest-asyncio", "pytest-mock", "syrupy",
              "psycopg[binary]", "ruff==0.14.10"], out / "installation.log", timeout=240)
        frozen = call([py, "-m", "pip", "freeze", "--all"], out / "freeze.log")
        (out / "environment.txt").write_text(frozen.stdout, encoding="utf-8")
        new_test = lib / "tests/test_parent_command_handoff.py"
        assert not new_test.exists()
        raw_test = (bundle / new_test.name).read_text()
        new_test.write_text(raw_test, encoding="utf-8")
        call([py, "-m", "ruff", "check", "--select", "I", "--fix", new_test], out / "imports.log", cwd=lib)
        call([py, "-m", "ruff", "format", new_test], out / "format.log", cwd=lib)
        tested_text = new_test.read_text()
        assert nonimport_ast(raw_test) == nonimport_ast(tested_text), "Formatting changed non-import AST"
        call([py, "-m", "ruff", "check", new_test], out / "lint.log", cwd=lib)
        shutil.copy2(new_test, out / new_test.name)
        report["tested_test_sha256"] = sha(new_test.read_bytes())
        report["formatting_only_nonimport_ast_unchanged"] = True
        relative = "libs/prebuilt/tests/" + new_test.name
        (out / "regression_tests.patch").write_text(
            f"diff --git a/{relative} b/{relative}\nnew file mode 100644\n" +
            "".join(difflib.unified_diff([], tested_text.splitlines(True), fromfile="/dev/null", tofile="b/" + relative)), encoding="utf-8")
        first = "parent_command = Command(graph=Command.PARENT, goto=output.goto)"
        goto = 'goto=cast("list[Send]", parent_command.goto) + output.goto,'
        assert original.count(first) == original.count(goto) == 1
        candidate = original.replace(first, "parent_command = output").replace(
            goto, goto + "\n                            update=list(parent_command._update_as_tuples()) + list(output._update_as_tuples()),")
        assert sha(candidate.encode()) == CANDIDATE_SHA
        (out / "experimental_runtime.patch").write_text("".join(difflib.unified_diff(
            original.splitlines(True), candidate.splitlines(True),
            fromfile="a/libs/prebuilt/langgraph/prebuilt/tool_node.py",
            tofile="b/libs/prebuilt/langgraph/prebuilt/tool_node.py")), encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, [bundle, *libs])),
                   PYTHONDONTWRITEBYTECODE="1", LANGGRAPH_TEST_FAST="true",
                   LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false", ZERO_REPO_ROOT=str(repo))
        for key in list(env):
            if key.endswith("API_KEY"):
                env.pop(key, None)
        for variant, text in (("base", original), ("normalized_candidate", candidate)):
            source.write_text(text, encoding="utf-8")
            target = out / variant
            target.mkdir()
            shutil.copy2(source, target / "tool_node.py")
            env.update(ZERO_EXPECTED_SOURCE=str(source), ZERO_EXPECTED_SHA=sha(text.encode()))
            for group, path in (("upstream", upstream_test), ("regression", new_test)):
                env["ZERO_GUARD_LOG"] = str(target / (group + "_guard.json"))
                junit = target / (group + ".xml")
                result = call([py, "-B", "-m", "pytest", "-p", "offline_guard", "-p", "no:cacheprovider",
                               "-q", "-o", "addopts=", path, "--junitxml", junit],
                              target / (group + ".log"), cwd=lib, env=env, timeout=180, required=False)
                stats = parse_junit(junit)
                guard = json.loads(Path(env["ZERO_GUARD_LOG"]).read_text())
                stats.update(variant=variant, group=group, returncode=result.returncode, guard=guard)
                report["runs"].append(stats)
                assert result.returncode in (0, 1), "Pytest setup/collection failed"
                assert stats["errors"] == 0 and stats["count"] > 0
                assert not guard["blocked_network_attempts"], "A test attempted external networking"
                if group == "regression":
                    assert stats["count"] == 24 and stats["skipped"] == 0
                assert blob(upstream_test.read_bytes()) == TEST_BLOB
        report["completed"] = True
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if original is not None:
            source.write_text(original, encoding="utf-8")
        (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed": report["completed"], "error": report.get("error"),
                      "runs": [{k: r[k] for k in ("variant", "group", "count", "passed", "failed", "errors", "skipped")} for r in report["runs"]]}))
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
