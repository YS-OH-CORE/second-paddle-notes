# SPDX-License-Identifier: Apache-2.0
"""Discussion-only, candidate-independent time scaling. Zero × Youngseok Oh.

Not an upstream patch: callers must choose the time horizon and timestamp meaning.
The score is a ranking preference, never a truth/conflict-resolution decision.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any


def rank(scoring: Any, rows: list[dict], bm25: dict, entities: dict,
         threshold: float, top_k: int, *, as_of: datetime,
         half_life_days: float = 180.0, weight: float = 0.1,
         explain: bool = False) -> list[dict]:
    """Reuse the candidate's non-temporal scoring with a fixed-clock time feature.

    Assumptions: unique IDs, finite baseline scores, and fixed active signal maps.
    Nonpositive finite weight disables this feature. Missing dates have zero boost;
    if all dates are missing, non-temporal scores are retained unchanged. Future
    dates saturate at 1 rather than receiving more than the configured weight.
    """
    if isinstance(weight, bool) or not math.isfinite(weight):
        raise ValueError('weight must be finite')
    if weight <= 0:
        return scoring.score_and_rank(rows, bm25, entities, threshold, top_k, explain, 0.0)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError('as_of must be a timezone-aware datetime')
    if isinstance(half_life_days, bool) or not math.isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError('half_life_days must be finite and positive')
    anchor = as_of.timestamp()
    base = scoring.score_and_rank(rows, bm25, entities, threshold, len(rows), True, 0.0)
    timed = []
    for row in base:
        stamp = None
        for field in ('updated_at', 'created_at'):
            try:
                stamp = scoring._parse_timestamp((row['payload'] or {}).get(field))
                if stamp is not None and not math.isfinite(stamp):
                    stamp = None
            except (ValueError, TypeError, OverflowError, OSError):
                stamp = None
            if stamp is not None:
                break
        timed.append((row, stamp))
    active = any(stamp is not None for _, stamp in timed)
    result = []
    for row, stamp in timed:
        details = dict(row['score_details'])
        age_days = max(0.0, (anchor - stamp) / 86400.0) if stamp is not None else math.inf
        recency = math.exp(-math.log(2.0) * (age_days / half_life_days))
        raw = details['raw_score'] + (weight * recency if active else 0.0)
        divisor = details['max_possible_score'] + (weight if active else 0.0)
        score = min(raw / divisor, 1.0)
        out = {'id': row['id'], 'score': score, 'payload': row['payload']}
        if explain:
            details.update(raw_score=raw, max_possible_score=divisor, final_score=score)
            if active:
                details.update(recency_score=recency, recency_weight=weight,
                               recency_as_of=as_of.isoformat(), half_life_days=half_life_days)
            out['score_details'] = details
        result.append(out)
    result.sort(key=lambda item: item['score'], reverse=True)
    return result[:top_k]
