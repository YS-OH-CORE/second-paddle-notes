"""Actual PR dispatch/confirmation code with the PR's model/transport doubles.

No provider, live profile, downstream task or platform message is used. The
interleaving tests control two coroutines at a method boundary, not a live server.
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

H = runpy.run_path(str(Path(__file__).with_name('test_model_multiline_payload.py')))
OLD = 'Reply only OLD-REQUEST.'
NEW = '  새 요청만 그대로 🧭\n  keep indent\n'


def setup(tmp_path, monkeypatch):
    from tools import slash_confirm as sc
    H['_setup_isolated_home'](tmp_path, monkeypatch)
    H['_quiet_model_switch_guards'](monkeypatch)
    H['_fire_selection_guard'](monkeypatch)
    H['_fake_switch_model'](monkeypatch, seen_raw_inputs=[])
    runner, adapter = H['_make_runner']()
    event = lambda text, thread='binding': H['_make_event'](text, thread_id=thread)
    key = lambda thread='binding': runner._session_key_for_source(event('', thread).source)
    sc.clear(key()); sc.clear(key('other'))
    clock = [1000.0]
    monkeypatch.setattr(sc, 'time', SimpleNamespace(time=lambda: clock[0]))
    return runner, adapter, event, key, sc, clock


def payloads(runner):
    return [call.args[0].text for call in runner._handle_message_with_agent.await_args_list]


def observe(case, runner, **extra):
    import gateway.run_inbound as inbound
    import gateway.slash_commands_model as model
    import tools.slash_confirm as confirmation
    row = dict(case=case, routed=payloads(runner), **extra,
        imports=dict(inbound=inbound.__file__, model=model.__file__, confirmation=confirmation.__file__),
        model_calls=0, platform_messages=0)
    destination = os.environ.get('MODEL_BINDING_OBSERVATIONS')
    if destination:
        with open(destination, 'a', encoding='utf-8') as out:
            out.write(json.dumps(row, ensure_ascii=False)+'\n')
    return row


@pytest.mark.parametrize('expired', [False, True])
@pytest.mark.parametrize('new_payload', ['', NEW], ids=['switch_only','exact_new_text'])
def test_replacement_belongs_to_new_confirmation(tmp_path, monkeypatch, expired, new_payload):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            old = sc.get_pending(key())
            if expired:
                clock[0] += 301
                assert sc.clear_if_stale(key())
            await r._handle_message(event('/model new-proposal'+('\n'+new_payload if new_payload else '')))
            new = sc.get_pending(key())
            assert old['confirm_id'] != new['confirm_id']
            await r._handle_message(event('!approve'))
            row = observe('replacement', r, expired=expired, expected=[new_payload] if new_payload else [],
                old_id=old['confirm_id'], new_id=new['confirm_id'], selected=r._session_model_overrides[key()]['model'])
            assert row['selected'] == 'new-proposal'
            assert row['routed'] == row['expected']
        finally:
            sc.clear(key())
    asyncio.run(run())


@pytest.mark.parametrize('retire', ['cancel','expiry','reset'])
def test_retired_confirmation_cannot_deliver_payload(tmp_path, monkeypatch, retire):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            old = sc.get_pending(key())
            if retire == 'cancel':
                await r._handle_message(event('!cancel'))
            elif retire == 'expiry':
                clock[0] += 301
                assert sc.clear_if_stale(key())
            else:
                r._clear_conversation_scope(key(), reason='test_reset')
            result = await sc.resolve(key(), old['confirm_id'], 'once')
            row = observe('retired_'+retire, r, callback_result=result)
            assert result is None and row['routed'] == []
            assert sc.get_pending(key()) is None
        finally:
            sc.clear(key())
    asyncio.run(run())


def test_wrong_id_does_not_consume_current_request(tmp_path, monkeypatch):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            pending = sc.get_pending(key())
            assert await sc.resolve(key(), 'not-this-confirmation', 'once') is None
            assert sc.get_pending(key())['confirm_id'] == pending['confirm_id']
            await r._handle_message(event('!approve'))
            assert observe('wrong_id_then_right', r)['routed'] == [OLD]
        finally:
            sc.clear(key())
    asyncio.run(run())


def test_duplicate_resolution_returns_payload_once(tmp_path, monkeypatch):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            p = sc.get_pending(key())
            results = await asyncio.gather(sc.resolve(key(), p['confirm_id'], 'once'),
                                            sc.resolve(key(), p['confirm_id'], 'once'))
            carried = [getattr(v, 'payload', None) for v in results if v is not None]
            observe('duplicate_callbacks', r, resolved_payloads=carried)
            assert carried == [OLD]
        finally:
            sc.clear(key())
    asyncio.run(run())


def test_other_session_does_not_borrow_payload(tmp_path, monkeypatch):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            await r._handle_message(event('/model new-proposal', 'other'))
            await r._handle_message(event('!approve', 'other'))
            assert payloads(r) == []
            await r._handle_message(event('!approve'))
            assert observe('other_session', r)['routed'] == [OLD]
        finally:
            sc.clear(key()); sc.clear(key('other'))
    asyncio.run(run())


def test_opening_model_help_does_not_discard_pending_task(tmp_path, monkeypatch):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            pending = sc.get_pending(key())
            r._model_listing_reply = AsyncMock(return_value='Model help, no change.')
            help_event = event('/model')
            await r._hm_cmd_model(help_event, help_event.source, key())
            assert sc.get_pending(key())['confirm_id'] == pending['confirm_id']
            await r._handle_message(event('!approve'))
            assert observe('help_then_approve', r)['routed'] == [OLD]
        finally:
            sc.clear(key())
    asyncio.run(run())


def test_direct_switch_retires_old_pending_model_confirmation(tmp_path, monkeypatch):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        try:
            await r._handle_message(event('/model old-proposal\n'+OLD))
            old = sc.get_pending(key())
            H['_quiet_model_switch_guards'](monkeypatch)
            await r._handle_message(event('/model new-proposal'))
            residual = sc.get_pending(key())
            observe('direct_switch', r, pending_id=residual['confirm_id'] if residual else None)
            assert residual is None
            assert await sc.resolve(key(), old['confirm_id'], 'once') is None
            assert payloads(r) == []
        finally:
            sc.clear(key())
    asyncio.run(run())


@pytest.mark.parametrize('new_payload', ['', 'Reply only NEW-REQUEST.'], ids=['new_switch_only','new_task'])
def test_late_old_handler_return_cannot_rebind_new_confirmation(tmp_path, monkeypatch, new_payload):
    async def run():
        r, a, event, key, sc, clock = setup(tmp_path, monkeypatch)
        registered = asyncio.Event(); release = asyncio.Event()
        original = r._handle_model_command
        async def delayed(ev, **kwargs):
            response = await original(ev, **kwargs)
            if 'old-proposal' in ev.text:
                registered.set()
                await asyncio.wait_for(release.wait(), 5)
            return response
        r._handle_model_command = delayed
        ev_a = event('/model old-proposal\n'+OLD)
        first = asyncio.create_task(r._hm_cmd_model(ev_a, ev_a.source, key()))
        try:
            await asyncio.wait_for(registered.wait(), 5)
            ev_b = event('/model new-proposal'+('\n'+new_payload if new_payload else ''))
            await r._hm_cmd_model(ev_b, ev_b.source, key())
            release.set(); await asyncio.wait_for(first, 5)
            await r._handle_message(event('!approve'))
            row = observe('late_old_return', r, expected=[new_payload] if new_payload else [])
            assert row['routed'] == row['expected']
        finally:
            release.set()
            await asyncio.wait_for(first, 5)
            sc.clear(key())
    asyncio.run(run())
