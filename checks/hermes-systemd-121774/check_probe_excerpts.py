"""Scope-routing check using unmodified helper excerpts from GitHub readbacks.

The subprocess and duration parser are test doubles. This tests routing, not
live systemd, duration parsing, the whole module, or PR integration. Sources:
- main d350422b15863fc4c0b7962b122b625a0271516c
- kokhlo's existing PR #103086, 6bfd9e112677e398b36ebc73dfb240a0319255fc
The excerpts came from connector reads, not a successful full-source download.
Original issue and fix retain their authorship. Check: Zero for Youngseok Oh.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from typing import Optional

BASE = '''def _systemd_timeout_stop_us(unit_name: str) -> Optional[int]:
    """``TimeoutStopUSec`` of ``unit_name`` in microseconds; ``--user`` first (hermes' usual)."""
    for flag in (["--user"], []):
        try:
            result = subprocess.run(
                ["systemctl", *flag, "show", unit_name, "--property=TimeoutStopUSec"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2.0,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        # Output: "TimeoutStopUSec=1min 30s" or "TimeoutStopUSec=90000000"
        for line in result.stdout.splitlines() if result.returncode == 0 else ():
            if line.startswith("TimeoutStopUSec="):
                value = line.split("=", 1)[1].strip()
                timeout_us = int(value) if value.isdigit() else parse_systemd_duration_to_us(value)
                if timeout_us is not None:
                    return timeout_us
    return None
'''
CANDIDATE = '''def _systemd_timeout_stop_us(unit_name: str) -> Optional[int]:
    """``TimeoutStopUSec`` of ``unit_name`` in microseconds; ``--user`` first (hermes' usual)."""
    for flag in (["--user"], []):
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    *flag,
                    "show",
                    unit_name,
                    "--property=TimeoutStopUSec,LoadState",
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=2.0,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        # Output: "TimeoutStopUSec=1min 30s" or "TimeoutStopUSec=90000000" (plus "LoadState=...")
        lines = result.stdout.splitlines() if result.returncode == 0 else ()
        # systemctl answers with systemd's default timeout (exit 0) for a unit that does not
        # exist in this scope (LoadState=not-found): probe the other scope instead of
        # mistaking the 90s default for the unit's configured value.
        if "LoadState=not-found" in lines:
            continue
        for line in lines:
            if line.startswith("TimeoutStopUSec="):
                value = line.split("=", 1)[1].strip()
                timeout_us = int(value) if value.isdigit() else parse_systemd_duration_to_us(value)
                if timeout_us is not None:
                    return timeout_us
    return None
'''
MISSING = {'LoadState': 'not-found', 'TimeoutStopUSec': '1min 30s'}
SYSTEM = {'LoadState': 'loaded', 'TimeoutStopUSec': '3min 30s'}
USER = {'LoadState': 'loaded', 'TimeoutStopUSec': '4min'}
SHORT = {'LoadState': 'loaded', 'TimeoutStopUSec': '1min 30s'}
CASES = [
    ('missing_user_loaded_system', MISSING, SYSTEM, 210000000),
    ('missing_both', MISSING, MISSING, None),
    ('loaded_user_control', USER, SYSTEM, 240000000),
    ('failed_user_query_control', 'nonzero', SYSTEM, 210000000),
    ('timed_out_user_query_control', 'timeout', SYSTEM, 210000000),
    ('genuinely_short_loaded_user', SHORT, SYSTEM, 90000000),
]
# Parsing is explicitly OUTSIDE the test. Routing receives fixed known durations.
DURATIONS = {'1min 30s': 90000000, '3min 30s': 210000000, '4min': 240000000}


def main() -> None:
    rows = []
    for phase, excerpt in [('current_main_excerpt', BASE), ('existing_PR_103086_excerpt', CANDIDATE)]:
        for name, user, system, expected in CASES:
            calls = []
            def fake_run(args, **kwargs):
                scope = 'user' if '--user' in args else 'system'
                calls.append(scope)
                fixture = user if scope == 'user' else system
                assert args[0] == 'systemctl' and 'show' in args
                assert kwargs.get('timeout') == 2.0
                if fixture == 'timeout':
                    raise subprocess.TimeoutExpired(args, 2.0)
                if fixture == 'nonzero':
                    return subprocess.CompletedProcess(args, 1, stdout='', stderr='fixture: unavailable')
                requested = next(a.split('=', 1)[1].split(',') for a in args if a.startswith('--property='))
                stdout = ''.join(k + '=' + fixture[k] + '\n' for k in requested if k in fixture)
                return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr='')
            ns = {'Optional': Optional,
                  'subprocess': SimpleNamespace(run=fake_run, TimeoutExpired=subprocess.TimeoutExpired),
                  'parse_systemd_duration_to_us': lambda value: DURATIONS.get(value)}
            exec(compile(excerpt, phase, 'exec'), ns)
            observed = ns['_systemd_timeout_stop_us']('hermes-gateway.service')
            rows.append({'phase': phase, 'case': name, 'observed_us': observed,
                         'expected_us': expected, 'matches_expected': observed == expected,
                         'scopes_queried': calls})
    base, candidate = rows[:6], rows[6:]
    assert [r['observed_us'] for r in base] == [90000000,90000000,240000000,210000000,210000000,90000000]
    assert all(r['matches_expected'] for r in candidate)
    assert candidate[0]['scopes_queried'] == ['user', 'system']
    assert candidate[1]['scopes_queried'] == ['user', 'system']
    assert candidate[2]['scopes_queried'] == ['user']
    report = {
        'status': 'EXCERPT_ROUTING_CHECK_COMPLETED',
        'scope': 'Copied upstream helper excerpts, subprocess fixtures and duration-parser stub; no real systemctl or whole-module import',
        'original_failure_preserved': 'Container raw download failed DNS; PC raw download returned HTTP 429 before executing either source. No immediate download retries.',
        'cases': 6, 'helper_evaluations': 12,
        'current_matches': sum(r['matches_expected'] for r in base),
        'candidate_matches': sum(r['matches_expected'] for r in candidate),
        'sources': {
            'base': 'https://github.com/NousResearch/hermes-agent/blob/d350422b15863fc4c0b7962b122b625a0271516c/gateway/shutdown_forensics.py',
            'candidate': 'https://github.com/kokhlo/hermes-agent/blob/6bfd9e112677e398b36ebc73dfb240a0319255fc/gateway/shutdown_forensics.py'},
        'excerpt_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k,v in [('base',BASE),('candidate',CANDIDATE)]},
        'rows': rows,
        'limits': ['no host reproduction','no real duration parser','no service changes','not full PR test suite',
                   'does not establish running process owner with loaded same-name units in both scopes'],
    }
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
