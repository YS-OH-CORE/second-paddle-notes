"""Template-only review controls for vLLM RFC 58647, item 8.

Youngseok Oh x Zero, AI collaboration partners.
No model inference, vLLM converter execution, tokenization or network request.
Use the exact official Qwen3.8-27B template specified below.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path

from jinja2 import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment

TEMPLATE_SHA256 = "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041"
REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
OLD = "OLD_TRACE_SENTINEL: A previous task used its own plan."
CURRENT = "CURRENT_TRACE_SENTINEL: The current task needs this tool result."
REMINDER = "REMINDER_SENTINEL: Keep the report concise."
CORRECTION = "CORRECTION_SENTINEL: Stop the old task and report the current status."


def fixtures() -> dict[str, list[dict]]:
    # All text and reasoning fields are synthetic. These are already-converted
    # message shapes, not observations from a vLLM server.
    base = [
        {"role": "system", "content": "This is a fictional input-construction check."},
        {"role": "user", "content": "Previous task: list a fictional document."},
        {"role": "assistant", "content": "Previous task complete.", "reasoning_content": OLD},
        {"role": "user", "content": "Current task: inspect the fictional ledger."},
        {"role": "assistant", "content": "", "reasoning_content": CURRENT,
         "tool_calls": [{"id": "call_status", "type": "function", "function": {
             "name": "read_status", "arguments": {}}}]},
        {"role": "tool", "tool_call_id": "call_status", "content": "TOOL_RESULT_SENTINEL: PRIVATE"},
    ]
    return {
        "tool_result_only": base,
        "trailing_user_reminder": base + [{"role": "user", "content": REMINDER}],
        "genuine_new_user_turn": base + [{"role": "user", "content": CORRECTION}],
    }


def fail(message: str) -> None:
    raise TemplateError(message)


def run(template_path: Path, output: Path) -> dict:
    raw = template_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == TEMPLATE_SHA256, "Wrong template snapshot"
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    env.globals["raise_exception"] = fail
    template = env.from_string(raw.decode("utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for shape, original in fixtures().items():
        for preserve in (None, False, True):
            messages = copy.deepcopy(original)
            args = {"messages": messages, "add_generation_prompt": True, "enable_thinking": False}
            if preserve is not None:
                args["preserve_thinking"] = preserve
            rendered = template.render(**args)
            old, current = OLD in rendered, CURRENT in rendered
            assert old == (preserve is not False)
            assert current == (preserve is not False or shape == "tool_result_only")
            assert messages == original, "Input fixture mutated"
            for message in messages:
                if message.get("content"):
                    assert rendered.count(message["content"]) == 1, "Visible text lost or duplicated"
            row = {"shape": shape, "preserve_thinking": preserve,
                   "old_trace_retained": old, "current_trace_retained": current,
                   "visible_contents_once": True,
                   "render_sha256": hashlib.sha256(rendered.encode()).hexdigest()}
            rows.append(row)
            (output / f'{shape}_{preserve}.txt').write_text(rendered, encoding="utf-8")
    for shape in fixtures():
        a, b = [r for r in rows if r["shape"] == shape and r["preserve_thinking"] is not False]
        assert a["render_sha256"] == b["render_sha256"], "Default and True differ"
    report = {"kind": "local_jinja_template_only", "model_asset": "Qwen/Qwen3.8-27B",
              "revision": REVISION, "template_sha256": TEMPLATE_SHA256,
              "jinja2": importlib.metadata.version("jinja2"), "renders": len(rows),
              "model_calls": 0, "vllm_converter_executions": 0, "tokenizer_executions": 0,
              "rows": rows}
    (output / "OBSERVATIONS.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.template, args.out)
