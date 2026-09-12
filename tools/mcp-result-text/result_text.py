"""Opt-in text fallback for validated MCP result mappings. Standard library only.

Keep the server response separately. This produces a consumer view, not a new
server response, a signature-preserving transform, or evidence about the world.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Literal


@dataclass(frozen=True)
class Projection:
    """An independent result copy and the source of its content blocks."""
    result: dict[str, Any]
    source: Literal['existing_content', 'structured_content', 'absent']


def add_structured_fallback(
    result: Mapping[str, Any], *, max_text_bytes: int = 1_048_576
) -> Projection:
    """Supply one JSON text block only for empty content with structured data.

    Input is a validated MCP CallToolResult in wire-field form: content,
    structuredContent and isError. For SDK objects use model_dump(mode='json',
    by_alias=True, exclude_none=True). Any existing block, including an empty
    text block or an image, is retained. Falsey structured values are not lost.
    Other fields and error flags are kept. No input is mutated, no tool is run,
    and no text is inferred when structured data is absent.

    Raises TypeError/ValueError for invalid arguments, non-JSON structure or a
    fallback exceeding the chosen byte limit. Never silently truncates output.
    """
    if not isinstance(result, Mapping):
        raise TypeError('Expected a validated result mapping.')
    if not isinstance(result.get('content'), list):
        raise TypeError('content must be a list.')
    if 'isError' in result and type(result['isError']) is not bool:
        raise TypeError('isError must be a boolean when present.')
    if type(max_text_bytes) is not int or max_text_bytes < 1:
        raise ValueError('max_text_bytes must be a positive integer.')
    structured = result.get('structuredContent')
    if structured is not None and not isinstance(structured, dict):
        raise TypeError('structuredContent must be an object or absent.')

    projected = deepcopy(dict(result))
    if projected['content']:
        return Projection(projected, 'existing_content')
    if structured is None:
        return Projection(projected, 'absent')

    try:
        text = json.dumps(structured, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':'))
        if json.loads(text) != structured:
            raise ValueError('Not a JSON-compatible object.')
        size = len(text.encode('utf-8'))
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        raise ValueError('structuredContent must be losslessly JSON-encodable.') from None
    if size > max_text_bytes:
        raise ValueError('Structured fallback exceeds max_text_bytes; nothing was truncated.')
    projected['content'] = [{'type': 'text', 'text': text}]
    return Projection(projected, 'structured_content')
