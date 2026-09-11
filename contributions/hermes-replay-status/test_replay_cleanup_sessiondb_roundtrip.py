"""Persist, exit, reopen, and sanitize synthetic Hermes tool history.

Uses real SessionDB and replay helpers in separate Python processes. No model,
user account, gateway, source-function mocks, or live ~/.hermes is involved.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent.tool_dispatch_helpers import make_tool_result_message

CASES = [
    ("terminal_marker", "terminal", {"output": "Documentation quotes [Command interrupted].", "exit_code": 0}, "preserve"),
    ("terminal_code_text", "terminal", {"output": "The docs explain interrupt exit_code 130.", "exit_code": 0}, "preserve"),
    ("ordinary_failure", "terminal", {"output": "Documentation quotes [Command interrupted].", "exit_code": 7}, "preserve"),
    ("file_marker", "read_file", {"content": "Documentation quotes [Command interrupted]."}, "preserve"),
    ("plain_success", "terminal", {"output": "Finished reading the documentation.", "exit_code": 0}, "preserve"),
    ("real_interrupt", "terminal", {"output": "partial output\n[Command interrupted]", "exit_code": 130}, "unknown"),
    ("legacy_interrupt", "terminal", {"output": "operation interrupted", "exit_code": -1}, "unknown"),
    ("read_interrupt", "read_file", {"output": "[Command interrupted]", "exit_code": 130}, "drop_readonly"),
]


def _worker(mode: str, db_path: Path, input_path: Path, output_path: Path) -> None:
    import hermes_state
    import agent.replay_cleanup as replay
    from hermes_state import SessionDB

    db = SessionDB(db_path=db_path)
    try:
        if mode == "write":
            history = json.loads(input_path.read_text(encoding="utf-8"))
            db.create_session("roundtrip", source="cli")
            db.replace_messages("roundtrip", history)
            result = {"mode": mode, "pid": os.getpid(), "sessiondb_module": hermes_state.__file__}
        elif mode == "read":
            loaded = db.get_messages_as_conversation("roundtrip")
            before = copy.deepcopy(loaded)
            cleaned = replay.sanitize_replay_history(loaded)
            persisted_after = db.get_messages_as_conversation("roundtrip")
            result = {
                "mode": mode, "pid": os.getpid(), "before": before, "after": cleaned,
                "input_unchanged": loaded == before,
                "stored_history_unchanged": persisted_after == before,
                "sessiondb_module": hermes_state.__file__, "replay_module": replay.__file__,
            }
        else:
            raise ValueError("Unexpected worker mode")
    finally:
        db.close()
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


@pytest.mark.parametrize("case_id,name,payload,expected", CASES, ids=[case[0] for case in CASES])
def test_database_restart_keeps_correct_replay(tmp_path, case_id, name, payload, expected):
    # Both utterances are synthetic fixtures, not exported personal dialogue.
    latest = "앞의 결과를 설명해 줘. 명령은 다시 실행하지 마."
    text = json.dumps(payload, ensure_ascii=False)
    history = [
        {"role": "user", "content": "Read the documentation."},
        {"role": "assistant", "content": "", "tool_calls": [{
            "id": "c1", "type": "function", "function": {"name": name, "arguments": "{}"}
        }]},
        make_tool_result_message(name, text, "c1"),
        {"role": "user", "content": latest},
    ]
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path / "isolated-hermes")
    env["HERMES_TEST_ISOLATION"] = env["HERMES_HOME"]
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Run sequentially: writer must exit before a different process opens the DB.
    outputs = {}
    for mode in ("write", "read"):
        path = tmp_path / (mode + ".json")
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker", mode,
             str(tmp_path / "state.db"), str(input_path), str(path)],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        outputs[mode] = json.loads(path.read_text(encoding="utf-8"))
    write, read = outputs["write"], outputs["read"]
    original_tool = next(message for message in read["before"] if message["role"] == "tool")
    after_tools = [message for message in read["after"] if message["role"] == "tool"]
    actual = "preserve" if any(message.get("content") == text for message in after_tools) else (
        "unknown" if any(message.get("effect_disposition") == "unknown" for message in after_tools)
        else "drop_readonly" if not after_tools else "unexpected"
    )
    observation = {
        "case_id": case_id, "expected": expected, "actual": actual,
        "writer_pid": write["pid"], "reader_pid": read["pid"], "test_pid": os.getpid(),
        "before_rows": len(read["before"]), "after_rows": len(read["after"]),
        "persisted_tool_text_equal": original_tool["content"] == text,
        "latest_user_preserved": read["after"][-1]["content"] == latest,
        "input_unchanged": read["input_unchanged"],
        "stored_history_unchanged": read["stored_history_unchanged"],
        "sessiondb_module": read["sessiondb_module"], "replay_module": read["replay_module"],
    }
    evidence_path = os.environ.get("REPLAY_ROUNDTRIP_EVIDENCE")
    if evidence_path:
        # The verifier supplies a fresh evidence file; cases run sequentially.
        with Path(evidence_path).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(observation, ensure_ascii=False) + "\n")
    assert write["pid"] != read["pid"] != os.getpid()
    assert read["before"][-1]["content"] == latest
    assert original_tool["content"] == text
    assert read["input_unchanged"] and read["stored_history_unchanged"]
    assert read["after"][-1]["content"] == latest
    assert actual == expected
    assert len(read["after"]) == (2 if expected == "drop_readonly" else 4)


if __name__ == "__main__":
    if len(sys.argv) != 6 or sys.argv[1] != "--worker":
        raise SystemExit("Internal synthetic test worker only")
    _worker(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
