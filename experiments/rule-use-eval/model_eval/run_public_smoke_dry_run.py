#!/usr/bin/env python3
"""Run or check the complete zero-cost public-smoke mock pipeline."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from build_bundle import DEFAULT_CASES, DEFAULT_GOLD, write_bundle
from common import jsonl_text, pretty_json, read_jsonl, write_text
from make_mock_responses import make_records
from parse_responses import parse_records
from score_model_eval import score_files


HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
RESULTS = HERE / "results"
FILENAMES = {
    "requests": "public-smoke.requests.jsonl",
    "mapping": "public-smoke.evaluator-mapping.jsonl",
    "manifest": "public-smoke.bundle-manifest.json",
    "raw": "public-smoke-mock.raw.jsonl",
    "parsed": "public-smoke-mock.parsed.jsonl",
    "metrics": "public-smoke-mock.metrics.json",
}


def paths_under(root: Path) -> dict[str, Path]:
    return {
        "requests": root / "artifacts" / FILENAMES["requests"],
        "mapping": root / "artifacts" / FILENAMES["mapping"],
        "manifest": root / "artifacts" / FILENAMES["manifest"],
        "raw": root / "results" / FILENAMES["raw"],
        "parsed": root / "results" / FILENAMES["parsed"],
        "metrics": root / "results" / FILENAMES["metrics"],
    }


def generate(root: Path) -> dict[str, Path]:
    paths = paths_under(root)
    write_bundle(
        DEFAULT_CASES,
        DEFAULT_GOLD,
        paths["requests"],
        paths["mapping"],
        paths["manifest"],
        repeats=2,
        order_seed=20260825,
        study_kind="public_smoke_mock_dry_run",
    )
    requests = read_jsonl(paths["requests"], "request")
    raw = make_records(requests)
    write_text(paths["raw"], jsonl_text(raw))
    parsed = parse_records(requests, raw)
    write_text(paths["parsed"], jsonl_text(parsed))
    metrics = score_files(
        paths["mapping"],
        paths["parsed"],
        paths["manifest"],
        bootstrap_resamples=10000,
        bootstrap_seed=20260825,
        delta=0.10,
    )
    write_text(paths["metrics"], pretty_json(metrics))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed dry-run artifacts byte-for-byte")
    args = parser.parse_args()
    committed = paths_under(HERE)
    if args.check:
        with tempfile.TemporaryDirectory(prefix="rule-use-model-eval-check-") as temp:
            generated = generate(Path(temp))
            stale = [
                key
                for key in FILENAMES
                if not committed[key].exists()
                or committed[key].read_bytes() != generated[key].read_bytes()
            ]
        if stale:
            raise SystemExit("stale or missing public mock dry-run artifacts: " + ", ".join(stale))
        print("public mock dry-run check passed: 6 artifacts, model calls=0, network=0, cost=0")
        return 0

    generated = generate(HERE)
    print(
        f"wrote {len(generated)} public mock dry-run artifacts; "
        "model calls=0, SDKs=0, network=0, cost=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
