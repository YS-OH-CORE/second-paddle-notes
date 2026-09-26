# SPDX-License-Identifier: Apache-2.0
"""Prospective acceptance controls for CanIToolCall issue 9.

Youngseok Oh x Zero. Actual unchanged worker/scorer imports, synthetic adapter
and reply objects. No engine, real stream, model or proposed finish schema runs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import socket
import sys

PIN = "9edf62cfd4c493749ca76bc8816db86a5bc8f91d"
BLOBS = {
    "src/canitoolcall/checks.py": "2d89ddc661920bc08c686b3edd7aeba9e73f4b13",
    "src/canitoolcall/runner.py": "7328607c655f7146982bfe5d87e303ce706d1cc0",
    "src/canitoolcall/adapters/worker.py": "79b54c08d41ca747f8d1547d9ecf379e76a55ea8",
    "src/canitoolcall/adapters/base.py": "b954278f18faa88e1686fe5bf0b08dded6655902",
    "src/canitoolcall/results.py": "1998509c71d1dcd1e91547a2aa508a8d47cfb288",
}
FIXTURE_IDS = ("gpt-oss/vllm-sequential-calls", "gpt-oss/vllm-call-then-final")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name, expected in BLOBS.items():
        data = (repo / name).read_bytes()
        observed = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if observed != expected:
            raise ValueError(f"Source identity changed: {name}")
    sys.path.insert(0, str(repo / "src"))
    from canitoolcall import checks, runner
    from canitoolcall.adapters import worker
    from canitoolcall.adapters.base import Adapter, Support
    from canitoolcall.fixtures import load_family, load_fixtures, validate
    from canitoolcall.results import CheckResult, ParseResult, Status

    assert Path(inspect.getfile(runner)).resolve() == repo / "src/canitoolcall/runner.py"
    attempts: list[str] = []

    def deny(*args, **kwargs):
        attempts.append("socket_or_dns")
        raise RuntimeError("No network in this boundary control")

    socket.socket.connect = socket.socket.connect_ex = socket.getaddrinfo = deny
    # This invokes the original validator; it does not prove the proposed new
    # fields are backward compatible, because no new fields are implemented here.
    validation = validate([repo / "fixtures"])
    assert validation == [], [str(v) for v in validation]
    corpus = load_fixtures([repo / "fixtures"])
    selected = {f.id: f for f in corpus if f.id in FIXTURE_IDS}
    assert set(selected) == set(FIXTURE_IDS)
    family = load_family("gpt-oss", repo / "fixtures")
    rows = []

    class UnsupportedObserver:
        """An explicit test double: every replay-stage call is forbidden."""
        def __init__(self) -> None:
            self.calls: list[str] = []

        def supports(self, family: str, model: str):
            self.calls.append("supports")
            return Support(False, "SYNTHETIC: stop-token assumption not supported")

        def __getattr__(self, name: str):
            self.calls.append(name)
            raise AssertionError(f"Replay stage reached after unsupported: {name}")

    for identifier in FIXTURE_IDS:
        fixture = selected[identifier]
        assert fixture.expected is not None and fixture.expected.tool_calls
        stub = UnsupportedObserver()
        reply = worker.replay(stub, fixture, family, [])
        excluded = runner.evaluate(fixture, family, reply)
        assert stub.calls == ["supports"]
        assert excluded.status is Status.UNSUPPORTED and not excluded.checks
        assert excluded.reason == "SYNTHETIC: stop-token assumption not supported"
        assert not any(k in reply for k in ("nonstream", "streams", "parser_config"))
        good_reply = {
            "ok": True, "fixture_id": identifier, "supported": True,
            "nonstream": checks.expected_as_result(fixture.expected).to_dict(),
            "streams": {},
        }
        good = runner.evaluate(fixture, family, good_reply)
        assert good.status is Status.PASS
        bad_reply = {**good_reply, "nonstream": ParseResult().to_dict()}
        bad = runner.evaluate(fixture, family, bad_reply)
        assert bad.status is Status.FAIL
        rows.append({
            "fixture": identifier,
            "unsupported_worker_reply": reply,
            "unsupported_case": asdict(excluded),
            "observer_calls": stub.calls,
            "supported_reference_status": good.status.value,
            "supported_empty_parse_status": bad.status.value,
        })
    # Deliberate wrong-level integration probe. The existing scorer does not
    # use unsupported check rows; its documented worker-level route is above.
    misplaced = checks.case_status([
        CheckResult("synthetic_future_applicability", "nonstream", Status.UNSUPPORTED,
                    "SYNTHETIC proposal control, not an existing registered check")
    ])
    assert misplaced is Status.PASS
    report = {
        "source_commit": PIN,
        "validated_fixture_records": len(corpus),
        "current_schema_validation_issues": 0,
        "selected_issue9_fixture_records": len(rows),
        "runner_evaluations": 6,
        "worker_calls_with_synthetic_adapter": 2,
        "rows": rows,
        "wrong_level_synthetic_check_row_aggregates_to": misplaced.value,
        "current_supports_parameters": list(inspect.signature(Adapter.supports).parameters),
        "source_blobs": BLOBS,
        "network_attempts": len(attempts),
        "engine_parser_calls": 0,
        "model_calls": 0,
        "finish_or_assumes_fields_implemented": False,
        "scope": "Existing worker and runner acceptance behavior using synthetic doubles, not implemented fixture-specific applicability or a new engine defect",
    }
    (out / "RESULTS.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
