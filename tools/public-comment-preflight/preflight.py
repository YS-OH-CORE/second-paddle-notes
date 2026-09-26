# SPDX-License-Identifier: Apache-2.0
"""Read-only preflight for known public-comment disclosure patterns.

Youngseok Oh x Zero. This is NOT a general secret scanner or a sending tool.
Passing means only that the listed patterns were not found. The sender must
inspect the complete outgoing payload, including anything its mail tool adds.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

MAX_BYTES = 256_000
RULES = (
    ("notification_token", re.compile(r"(?:[?&]|\b)email_token\s*=", re.I)),
    ("notification_unsubscribe", re.compile(r"github\.com/notifications/unsubscribe-auth/", re.I)),
    ("notification_reply_address", re.compile(r"reply\+[^\s<>\"']+@reply\.github\.com", re.I)),
    ("credential_query", re.compile(r"[?&](?:access_token|refresh_token|api_key|x-amz-signature|x-goog-signature|sig)\s*=", re.I)),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("private_key", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("authorization_header", re.compile(r"\bauthorization\s*:\s*(?:bearer|basic)\s+\S+", re.I)),
    ("email_reply_chain", re.compile(r"(?:^|\n)\s*>?\s*On\b[^\n]{0,220}\bwrote:\s*(?:\n|$)", re.I)),
    ("email_original_separator", re.compile(r"[-_]{2,}\s*(?:original message|forwarded message)\s*[-_]{2,}", re.I)),
    ("email_header", re.compile(r"(?:^|\n)\s*>?\s*(?:From|To|Cc|Bcc|Reply-To|Message-ID|In-Reply-To)\s*:", re.I)),
)


def findings(text: str) -> list[str]:
    """Return rule names only; never echo matched text, addresses or tokens."""
    if not isinstance(text, str):
        raise TypeError("Expected decoded UTF-8 text")
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Body exceeds the bounded check size")
    variants = [text]
    for _ in range(3):
        normalized = unquote(html.unescape(variants[-1]))
        if normalized == variants[-1]:
            break
        variants.append(normalized)
    # Folding is only for detecting wrapped reply headers, not modifying input.
    unfolded = re.sub(r"\r?\n[ \t]+", " ", variants[-1])
    variants.append(unfolded)
    return sorted({name for name, pattern in RULES if any(pattern.search(v) for v in variants)})


def self_test() -> dict:
    """All credential-looking values below are deliberately synthetic."""
    clean = (
        "Review evidence: https://github.com/example/project/issues/1#issuecomment-2\nZero x Youngseok Oh.",
        "The unsupported case raises NotImplementedError; return [[]] is not success.",
        "도구의 성공 응답과 실제 저장 상태는 따로 확인합니다.",
    )
    blocked = (
        ("https://github.com/example/project/issues/1?email_token=DEMO_ONLY", "notification_token"),
        ("https://github.com/example/project/issues/1?a=1&amp;email_token=DEMO_ONLY", "notification_token"),
        ("https%3A%2F%2Fgithub.com%2Fx%3Femail_token%3DDEMO_ONLY", "notification_token"),
        ("https%253A%252F%252Fgithub.com%252Fx%253Femail_token%253DDEMO_ONLY", "notification_token"),
        ("https://github.com/notifications/unsubscribe-auth/DEMO_ONLY", "notification_unsubscribe"),
        ("reply+DEMO_ONLY@reply.github.com", "notification_reply_address"),
        ("https://example.invalid/file?sig=DEMO_ONLY&se=tomorrow", "credential_query"),
        ("https://example.invalid/file?X-Amz-Signature=DEMO_ONLY", "credential_query"),
        ("ghp_" + "SYNTHETIC" * 4, "github_token"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private_key"),
        ("Authorization: Bearer DEMO_ONLY", "authorization_header"),
        ("On Friday, a fictional sender wrote:\nold mail", "email_reply_chain"),
        ("-----Original Message-----", "email_original_separator"),
        ("Review text\n> Reply-To: demo@example.invalid", "email_header"),
    )
    for text in clean:
        assert findings(text) == []
    for text, reason in blocked:
        result = findings(text)
        assert reason in result, reason
        assert all(item in dict(RULES) for item in result)
        assert "DEMO_ONLY" not in json.dumps(result)
    try:
        findings("x" * (MAX_BYTES + 1))
    except ValueError:
        pass
    else:
        raise AssertionError("Oversized input was not rejected")
    return {"clean_examples": len(clean), "flagged_examples": len(blocked),
            "oversized_input_rejected": True, "all_checks_passed": True,
            "network_requests": 0, "outgoing_messages": 0,
            "scope": "Synthetic local detector checks, not live email-tool validation"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--body", type=Path, help="Complete intended outgoing body; read only")
    source.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, sort_keys=True))
        return 0
    try:
        with args.body.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Body too large")
        codes = findings(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, ValueError):
        # No path, excerpt, credential, or raw exception string in reports.
        print(json.dumps({"status": "CHECK_ERROR", "send_authorized": False}))
        return 2
    print(json.dumps({"status": "REVIEW_REQUIRED" if codes else "NO_LISTED_PATTERN_FOUND",
                      "rule_codes": codes, "send_authorized": False}, sort_keys=True))
    return 1 if codes else 0


if __name__ == "__main__":
    raise SystemExit(main())
