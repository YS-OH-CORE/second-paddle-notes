"""Normalize native reasoning fields only when passing messages to an HF template.

This is a client-boundary adapter, not a model patch or a universal API schema.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from typing import Any


def to_hf_template_message(message: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve content/tools and reject contradictory reasoning aliases."""
    result = deepcopy(dict(message))
    if result.get('role') != 'assistant':
        return result
    modern, legacy = result.get('reasoning'), result.get('reasoning_content')
    for value in (modern, legacy):
        if value is not None and not isinstance(value, str):
            raise TypeError('Expected textual reasoning; structured details need a provider-specific adapter')
    if modern and legacy and modern != legacy:
        raise ValueError('Conflicting reasoning fields; do not silently choose one')
    if 'reasoning' in result or 'reasoning_content' in result:
        result['reasoning_content'] = legacy or modern or ''
        result.pop('reasoning', None)
    return result
