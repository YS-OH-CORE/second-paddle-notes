"""Retain exact inputs and output from the repository's canonical test runner."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
parser.add_argument("--checkout", required=True)
parser.add_argument("runner_args", nargs=argparse.REMAINDER)
args = parser.parse_args()
checkout = Path(args.checkout).resolve()
out = Path(__file__).resolve().parent / args.label
out.mkdir()
python = "/workspace/scratch/860645c74e07/hermes125919/.venv/bin/python"
env = os.environ.copy()
env.update(HERMES_PYTHON=python, HERMES_TEST_WORKERS="1",
           HERMES_TEST_FILE_RETRIES="0", GIT_NO_LAZY_FETCH="1")
extra = args.runner_args[1:] if args.runner_args[:1] == ["--"] else args.runner_args
command = ["scripts/run_tests.sh", "--file-timeout", "360", *extra,
           "--basetemp=" + str(out / "pytest")]
digest = lambda data: hashlib.sha256(data).hexdigest()
git = lambda *parts: subprocess.check_output(
    ["git", "-c", "remote.origin.promisor=false", *parts],
    cwd=checkout, env=env, text=True)
paths = ["tools/mcp_tool_handlers.py", "tools/mcp_tool_errors.py",
         "tools/mcp_tool_transport.py", "tools/mcp_oauth_manager.py", "tools/mcp_tool.py",
         "tests/e2e/core/mcp_plugins/test_mcp_streamable_http.py",
         "tests/e2e/core/mcp_plugins/_helpers.py",
         "tests/e2e/core/mcp_plugins/mcp_fixture_server.py",
         "pyproject.toml", "uv.lock", "scripts/run_tests.sh"]
patch = git("diff", "--binary", "HEAD")
(out / "working-tree.patch").write_text(patch, encoding="utf-8")
record = {
    "label": args.label, "checkout": str(checkout), "head": git("rev-parse", "HEAD").strip(),
    "workingTreeStatus": git("status", "--porcelain=v1", "--untracked-files=all"),
    "workingTreePatchSha256": digest(patch.encode()), "command": command,
    "environmentOverrides": {k: env[k] for k in (
        "HERMES_PYTHON", "HERMES_TEST_WORKERS", "HERMES_TEST_FILE_RETRIES", "GIT_NO_LAZY_FETCH")},
    "inputSha256": {p: digest((checkout / p).read_bytes()) for p in paths},
    "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
metadata = out / "execution.json"
metadata.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
start = time.monotonic()
log = out / "runner.log"
with log.open("w", encoding="utf-8") as stream:
    result = subprocess.run(command, cwd=checkout, env=env, stdout=stream, stderr=subprocess.STDOUT)
record.update(exitCode=result.returncode, elapsedSeconds=round(time.monotonic() - start, 3),
              finishedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              logSha256=digest(log.read_bytes()))
metadata.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: record[k] for k in ("label", "head", "exitCode", "elapsedSeconds")}, indent=2))
print("\n".join(log.read_text(encoding="utf-8").splitlines()[-55:]))
raise SystemExit(result.returncode)
