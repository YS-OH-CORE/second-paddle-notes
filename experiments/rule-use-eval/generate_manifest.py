#!/usr/bin/env python3
"""Generate or check SHA-256 hashes for the rule-use smoke package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
OUTPUT = ROOT / "manifest.sha256.json"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rule-use-eval.yml"


def included_files() -> list[Path]:
    files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path != OUTPUT
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    ]
    if WORKFLOW.exists():
        files.append(WORKFLOW)
    return sorted(files, key=lambda path: path.relative_to(REPO_ROOT).as_posix())


def build_manifest() -> dict[str, Any]:
    entries = []
    for path in included_files():
        payload = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return {"schema_version": 1, "algorithm": "sha256", "files": entries}


def rendered_manifest() -> str:
    return json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = rendered_manifest()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("manifest is stale; run: python generate_manifest.py")
        print(f"manifest check passed: {len(build_manifest()['files'])} files")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

