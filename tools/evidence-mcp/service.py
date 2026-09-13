"""Bounded, read-only operations shared by the MCP entry and local tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 1_048_576
_IMPORT_LOCK = Lock()
EXPECTED = {
    'approval-trace-check/audit.js': '3bd85f4a1a0fa8131382755de845658b712966e1',
    'mcp-result-text/result_text.py': 'a795d0af7e86a27e779b05fd04ff0afb8e644096',
}


class InputProblem(ValueError):
    """A fixed diagnostic code, never a copy of supplied text."""


def source_identity() -> dict[str, str]:
    observed = {}
    for name, expected in EXPECTED.items():
        data = (ROOT / name).read_bytes()
        value = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if value != expected:
            raise RuntimeError('Bundled helper changed; review the source pin before starting.')
        observed[name] = value
    return observed


def _input(text: str) -> str:
    if not isinstance(text, str):
        raise InputProblem('EXPECTED_TEXT')
    try:
        size = len(text.encode('utf-8'))
    except UnicodeError:
        raise InputProblem('INVALID_UNICODE') from None
    if size > LIMIT:
        raise InputProblem('INPUT_TOO_LARGE')
    return text


def check_trace(text: str) -> dict[str, Any]:
    _input(text)
    node = shutil.which('node')
    if not node:
        raise InputProblem('NODE_UNAVAILABLE')
    env = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP') if k in os.environ}
    try:
        proc = subprocess.run(
            [node, str(Path(__file__).with_name('audit_bridge.cjs'))],
            input=text.encode('utf-8'), capture_output=True, timeout=3,
            env=env, check=False,
        )
    except subprocess.TimeoutExpired:
        raise InputProblem('CHECK_TIMEOUT') from None
    if proc.returncode != 0:
        raise InputProblem('CHECK_UNAVAILABLE')
    try:
        value = json.loads(proc.stdout)
    except (ValueError, UnicodeError):
        raise InputProblem('CHECK_UNAVAILABLE') from None
    if not isinstance(value, dict) or type(value.get('ok')) is not bool:
        raise InputProblem('CHECK_UNAVAILABLE')
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputProblem('DUPLICATE_JSON_MEMBER')
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise InputProblem('INVALID_JSON')


def parse_result(text: str) -> dict[str, Any]:
    try:
        data = json.loads(_input(text), object_pairs_hook=_pairs, parse_constant=_constant)
    except InputProblem:
        raise
    except (ValueError, RecursionError):
        raise InputProblem('INVALID_JSON') from None
    if not isinstance(data, dict):
        raise InputProblem('INVALID_RESULT')
    return data


# The MCP endpoint serializes its returned mapping into model-facing text.
# The lower-level helper is a local copy utility; it intentionally retains fields
# which must not be promoted into that text. Reject mixed envelopes, do not redact
# the caller's original or recursively strip ordinary keys from structured data.
_PUBLIC_BLOCK_FIELDS = {
    'text': {'type', 'text', 'annotations'},
    'image': {'type', 'data', 'mimeType', 'annotations'},
    'audio': {'type', 'data', 'mimeType', 'annotations'},
    'resource_link': {'type', 'uri', 'name', 'title', 'description', 'mimeType', 'size', 'annotations'},
    'resource': {'type', 'resource', 'annotations'},
}


def _public_projection_input(data: dict[str, Any]) -> None:
    """Allow only explicitly model-facing protocol fields at this endpoint.

    This does not classify secrets in ordinary text or structuredContent. The
    caller must select those before putting them in a model-visible argument.
    """
    def fields(value: Any, allowed: set[str]) -> None:
        if not isinstance(value, dict):
            raise InputProblem('INVALID_RESULT')
        if '_meta' in value:
            raise InputProblem('HOST_METADATA_NOT_PROJECTABLE')
        if set(value) - allowed:
            raise InputProblem('NON_CONTENT_FIELDS')

    fields(data, {'content', 'structuredContent', 'isError'})
    content = data.get('content')
    if not isinstance(content, list):
        raise InputProblem('INVALID_RESULT')
    for block in content:
        if not isinstance(block, dict) or not isinstance(block.get('type'), str):
            raise InputProblem('INVALID_RESULT')
        allowed = _PUBLIC_BLOCK_FIELDS.get(block['type'])
        if allowed is None:
            raise InputProblem('UNSUPPORTED_CONTENT_BLOCK')
        fields(block, allowed)
        annotations = block.get('annotations')
        if annotations is not None:
            fields(annotations, {'audience', 'priority', 'lastModified'})
            if 'audience' in annotations:
                audience = annotations['audience']
                if not isinstance(audience, list) or 'assistant' not in audience:
                    raise InputProblem('NON_MODEL_AUDIENCE')
        if block['type'] == 'resource':
            fields(block.get('resource'), {'uri', 'mimeType', 'text', 'blob'})


def project_result(data: dict[str, Any]) -> dict[str, Any]:
    _public_projection_input(data)
    # The server validates with the SDK before entering here. The original helper
    # remains byte-identical; this import uses a fixed repository path, not input.
    name = '_zero_result_text'
    # Concurrent first calls must not see a partially initialized module.
    with _IMPORT_LOCK:
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, ROOT / 'mcp-result-text/result_text.py')
            if spec is None or spec.loader is None:
                raise RuntimeError('Bundled helper unavailable.')
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
    try:
        view = sys.modules[name].add_structured_fallback(data)
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise InputProblem('INVALID_RESULT') from None
    return {'status': 'projected', 'source': view.source, 'result': view.result}
