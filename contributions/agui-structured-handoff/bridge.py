"""Application-local metadata mapping, not an AG-UI or MCP schema change.

Only explicitly selected structured output and its error flag are carried.
MCP _meta and arbitrary extra fields are deliberately not copied.
"""
from __future__ import annotations
from copy import deepcopy
import json
from typing import Any

KEY = "example.mcp.result.v1"


def result_metadata(response: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a separate metadata object for a cooperating producer and host.

    Metadata is not a private channel: hosts may log or resend it in messages.
    Choose a namespace with the host, and select only data it may receive.
    """
    if not isinstance(response, dict) or (existing is not None and not isinstance(existing, dict)):
        raise TypeError("Expected result and metadata objects")
    if type(response.get("isError", False)) is not bool:
        raise ValueError("isError must be boolean")
    metadata = deepcopy(existing) if existing is not None else {}
    if KEY in metadata:
        raise ValueError("Application namespace already present")
    structured = response.get("structuredContent")
    if structured is None:
        return metadata
    if not isinstance(structured, dict):
        raise ValueError("structuredContent must be an object")
    encoded = json.dumps(structured, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode("utf-8")) > 1_048_576 or json.loads(encoded) != structured:
        raise ValueError("Structured value is too large or not losslessly JSON-encodable")
    metadata[KEY] = {"structuredContent": json.loads(encoded), "isError": response.get("isError", False)}
    return metadata
