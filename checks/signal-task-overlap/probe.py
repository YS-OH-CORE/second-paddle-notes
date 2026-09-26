# SPDX-License-Identifier: Apache-2.0
"""Overlap two synthetic profile scopes using ordinary Hermes imports.

Youngseok Oh x Zero. The submitted runtime is unchanged. This is not a
live Signal test, a concurrent gateway host, or a thread-safety benchmark.
"""
from __future__ import annotations
import argparse
import asyncio
from copy import deepcopy
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import AsyncMock

PIN = 'bb8f14060ae63968c5d34ca5024dbce7fea93001'
SIGNAL_BLOB = '3fa045195ab48f1ed2fc4987f9164123a70afc9e'
ACCOUNT = '+15550001111'


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', choices=('context_local', 'deliberately_global'), required=True)
    a = p.parse_args()
    repo, out = a.repo.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    attempts = []
    def deny(*args, **kwargs):
        attempts.append('socket_or_dns')
        raise RuntimeError('Network is outside this synthetic test')
    socket.socket.connect = socket.socket.connect_ex = deny
    socket.getaddrinfo = deny
    sys.path.insert(0, str(repo))
    from hermes_constants import (get_hermes_home, get_hermes_home_override,
                                  set_hermes_home_override, reset_hermes_home_override)
    from gateway.config import Platform, load_gateway_config
    from gateway.platforms.signal import SignalAdapter
    source = Path(inspect.getfile(SignalAdapter)).resolve()
    assert source == repo / 'gateway/platforms/signal.py'
    raw = source.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == SIGNAL_BLOB
    assert get_hermes_home_override() is None
    parent_env_home = os.environ['HERMES_HOME']
    parent_home = get_hermes_home()
    cases = []

    async def scenario(case_name, raw_false, order):
        root = out / case_name
        root.mkdir()
        homes = {name: root / name for name in ('A', 'B')}
        original_yaml = {}
        for name, home in homes.items():
            home.mkdir()
            text = ('signal:\n  enabled: true\n  account: "' + ACCOUNT + '"\n'
                    '  http_url: "http://127.0.0.1:9"\n')
            if name == 'A':
                text += '  note_to_self: ' + raw_false + '\n'
            (home / 'config.yaml').write_text(text, encoding='utf-8')
            original_yaml[name] = text.encode()
        barrier = asyncio.Barrier(2)
        events = []
        def home_label():
            seen = get_hermes_home().resolve()
            return next((name for name, home in homes.items() if home == seen), 'parent_or_other')
        async def wait(stage, name):
            events.append([name, stage])
            await asyncio.wait_for(barrier.wait(), timeout=10)
        async def task(name):
            token = None
            prior = get_hermes_home_override()
            if a.mode == 'context_local':
                token = set_hermes_home_override(homes[name])
            else:
                # Deliberately bad HOST behavior, not a mutation of Hermes code.
                # Both writes happen before either task reads config; last writer wins.
                os.environ['HERMES_HOME'] = str(homes[name])
            result = {'task': name, 'expected_enabled': name == 'B'}
            try:
                await wait('scope_set', name)
                result['home_before_load'] = home_label()
                config = load_gateway_config().platforms[Platform.SIGNAL]
                adapter = SignalAdapter(config)
                adapter.handle_message = AsyncMock()
                adapter._collect_attachments = AsyncMock(return_value=([], []))
                result['enabled'] = adapter.note_to_self
                await wait('adapter_constructed', name)
                message = {'envelope': {'sourceNumber': ACCOUNT, 'timestamp': 1234567,
                    'syncMessage': {'sentMessage': {'destinationNumber': ACCOUNT,
                       'timestamp': 1234567, 'message': 'synthetic personal note',
                       'attachments': [{'id': 'fixture-only', 'contentType': 'image/png'}]}}}}
                before_message = deepcopy(message)
                await adapter._handle_envelope(message)
                result['dispatches'] = adapter.handle_message.await_count
                result['attachment_collector_calls'] = adapter._collect_attachments.await_count
                result['client_never_connected'] = adapter.client is None
                result['input_message_unchanged'] = message == before_message
                await wait('envelope_handled', name)
                result['home_after_handle'] = home_label()
                result['contract_met'] = (
                    result['home_before_load'] == result['home_after_handle'] == name
                    and result['enabled'] == result['expected_enabled']
                    and result['dispatches'] == int(name == 'B')
                    and (name != 'A' or result['attachment_collector_calls'] == 0)
                    and result['client_never_connected']
                )
            finally:
                if token is not None:
                    reset_hermes_home_override(token)
                result['context_reset'] = get_hermes_home_override() == prior
            return result
        try:
            tasks = [asyncio.create_task(task(name), name=name) for name in order]
            outcomes = await asyncio.wait_for(asyncio.gather(*tasks), timeout=30)
        finally:
            os.environ['HERMES_HOME'] = parent_env_home
        assert all((home / 'config.yaml').read_bytes() == original_yaml[name] for name, home in homes.items())
        assert get_hermes_home() == parent_home and get_hermes_home_override() is None
        return {'case': case_name, 'raw_false': raw_false, 'start_order': order,
                'events': events, 'outcomes': sorted(outcomes, key=lambda r: r['task']),
                'both_contracts_met': all(r['contract_met'] for r in outcomes),
                'parent_context_restored': True, 'config_files_unchanged': True}

    report = {'candidate_commit': PIN, 'mode': a.mode, 'completed': False, 'cases': cases,
              'python': sys.version, 'model_calls': 0, 'live_signal_calls': 0,
              'source_blob': SIGNAL_BLOB, 'source_sha256': hashlib.sha256(raw).hexdigest(),
              'versions': {n: importlib.metadata.version(n) for n in ('pydantic', 'PyYAML', 'httpx')}}
    try:
        for raw_false in ('false', '"false"'):
            for order in (['A', 'B'], ['B', 'A']):
                label = ('quoted' if raw_false.startswith('"') else 'boolean') + '_' + ''.join(order)
                row = asyncio.run(scenario(label, raw_false, order))
                cases.append(row)
                print('CASE ' + json.dumps(row), flush=True)
        expected = a.mode == 'context_local'
        assert len(cases) == 4
        assert all(row['both_contracts_met'] == expected for row in cases)
        assert all(r['context_reset'] for row in cases for r in row['outcomes'])
        assert not attempts
        report['completed'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        report['network_attempts'] = attempts
        report['both_profiles_correct'] = sum(r['both_contracts_met'] for r in cases)
        save(out / 'RESULT.json', report)
        print('RESULT ' + json.dumps(report), flush=True)
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
