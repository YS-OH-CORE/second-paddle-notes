"""Selected outer-inbound integrations, not a live gateway/model qualification.

Real _handle_message / MoA handler / eviction / finalizer / SessionStore SQLite /
turn-lease helpers and asyncio locks. Admission, unrelated dispatch, capacity,
cache persistence, durable-active markers, platform delivery and agent work are
controlled fixtures. No production code or existing upstream test is modified.
"""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import gateway.run as run_module
from gateway.run import GatewayRunner, _AGENT_PENDING_SENTINEL
from gateway.config import GatewayConfig, Platform
from gateway.platforms.event import MessageEvent, MessageType
from gateway.session import SessionSource, SessionStore
from gateway.turn_lease import SessionTurnLeaseRegistry
from hermes_constants import set_hermes_home_override, reset_hermes_home_override

ROOT = Path(run_module.__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    'zero_original_reaped_fixture', ROOT / 'tests/gateway/test_reaped_session_recovery.py')
_original_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_original_fixture)


class CapacityLease:
    def __init__(self):
        self.release_count = 0

    def release(self):
        self.release_count += 1


class RecordingAgent:
    def __init__(self):
        self.interrupt_reasons = []

    def hard_interrupt(self, message=None, **kwargs):
        self.interrupt_reasons.append(message)

    def get_activity_summary(self):
        return {'seconds_since_activity': 0, 'last_activity_desc': 'fixture wait',
                'api_call_count': 0, 'max_iterations': 1}


def snapshot(gateway, key):
    return copy.deepcopy(gateway._session_state(key).conversation.model_override)


def emit(kind, **fields):
    path = os.environ.get('ZERO_OBSERVATIONS')
    if path:
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write(json.dumps({'kind': kind, **fields}, ensure_ascii=False) + '\n')


@pytest.fixture
def rig(tmp_path, monkeypatch):
    token = set_hermes_home_override(str(tmp_path / 'home'))
    store = None
    try:
        store = SessionStore(sessions_dir=tmp_path / 'sessions', config=GatewayConfig())
        gateway = _original_fixture._make_runner(store)
        gateway._turn_leases = SessionTurnLeaseRegistry()
        gateway._external_drain_active = False
        gateway._persist_active_agents = lambda: None
        gateway._evict_cached_agent = lambda key: None
        gateway._clear_durable_active_turn = AsyncMock()
        gateway._run_post_turn_hooks = AsyncMock()
        gateway._hm_admit_event = AsyncMock(side_effect=lambda event: (event, event.source, False))
        gateway._hm_estop_gate = lambda *args: None
        gateway._hm_pending_reply_intercepts = AsyncMock(return_value=None)
        gateway._is_telegram_topic_root_lobby = lambda source: False
        gateway._hm_rescue_orphaned_fifo = lambda event, source, internal, key: (event, source, internal)
        source = SessionSource(platform=Platform.TELEGRAM, chat_id='zero-fixture',
                               chat_type='dm', user_id='fixture')
        entry = store.get_or_create_session(source)
        key = store._generate_session_key(source)
        leases, before_dispatch = [], []

        def claim(*args):
            lease = CapacityLease()
            leases.append(lease)
            return lease, None

        gateway._claim_active_session_slot = claim

        async def dispatch(event, current_source, current_key):
            before_dispatch.append(snapshot(gateway, key))
            # Actual MoA command preparation; unrelated command/plugin discovery is excluded.
            return await gateway._hm_cmd_moa(event, current_source, current_key)

        gateway._hm_dispatch_idle_commands = dispatch
        monkeypatch.setattr('hermes_cli.config.load_config', lambda: {})
        yield SimpleNamespace(g=gateway, store=store, source=source, entry=entry, key=key,
                              leases=leases, before_dispatch=before_dispatch)
    finally:
        if store is not None:
            store.close_all_db_handles()
        reset_hermes_home_override(token)


def event(rig, label):
    return MessageEvent(text='/moa ' + label, message_type=MessageType.TEXT, source=rig.source)


def install_prior(rig, has_prior):
    prior = {'provider': 'fixture-provider', 'model': 'original-choice'} if has_prior else None
    rig.g._session_state(rig.key).conversation.model_override = copy.deepcopy(prior)
    return prior


@pytest.mark.asyncio
@pytest.mark.parametrize('reason', ['ws_orphan_reap', 'idle'])
@pytest.mark.parametrize('has_prior', [False, True])
async def test_reaped_replacement_and_delayed_outer_finalizer(rig, reason, has_prior):
    g, key, store = rig.g, rig.key, rig.store
    prior = install_prior(rig, has_prior)
    old_ready, allow_old_exit = asyncio.Event(), asyncio.Event()
    agent = RecordingAgent()
    tokens, observed = {}, {}
    old_task = None

    async def work(ev, source, routing_key, generation):
        entry = store.get_or_create_session(source)
        if ev.text == 'OLD':
            await g._hmwa_acquire_turn_lease(routing_key, generation, entry, None)
            tokens['old'] = g._turn_leases._leases[entry.session_id].holder
            g._session_state(key).turn.agent = agent
            old_ready.set()
            await allow_old_exit.wait()
            return 'old fixture finished'
        observed['old_session_id'] = rig.entry.session_id
        observed['new_session_id'] = entry.session_id
        # Same-ID reattachment waits for the old transcript lock. Different IDs
        # permit two simultaneous real locks before the old outer finalizer runs.
        if entry.session_id == rig.entry.session_id:
            allow_old_exit.set()
        await g._hmwa_acquire_turn_lease(routing_key, generation, entry, None)
        tokens['new'] = g._turn_leases._leases[entry.session_id].holder
        allow_old_exit.set()
        await old_task
        turn = g._session_state(key).turn
        observed.update(
            prior_seen_before_new_moa=rig.before_dispatch[1],
            model_after_old_finalizer=snapshot(g, key),
            replacement_slot_survived=turn.agent is _AGENT_PENDING_SENTINEL,
            replacement_capacity_survived=turn.lease is rig.leases[1] and rig.leases[1].release_count == 0,
            old_transcript_token_released=tokens['old'].released,
            replacement_transcript_token_held=g._turn_leases._leases[entry.session_id].holder is tokens['new'],
        )
        return 'new fixture finished'

    g._handle_message_with_agent = work
    old_task = asyncio.create_task(g._handle_message(event(rig, 'OLD')))
    try:
        await asyncio.wait_for(old_ready.wait(), 4)
        store._db.end_session(rig.entry.session_id, reason)
        assert store._is_session_ended_in_db(rig.entry.session_id) is True
        reply = await asyncio.wait_for(g._handle_message(event(rig, 'NEW')), 6)
        await old_task
        observed.update(final_model=snapshot(g, key), running_after_b=g._is_session_running(key),
                        replacement_token_released=tokens['new'].released,
                        interrupt_reasons=agent.interrupt_reasons, reply=reply)
        emit('reaped_replacement', reason=reason, has_prior=has_prior, expected_prior=prior, **observed)
        assert observed['prior_seen_before_new_moa'] == prior, 'base_not_restored_before_successor_snapshot'
        assert observed['model_after_old_finalizer']['provider'] == 'moa', 'old_finalizer_changed_successor_choice'
        assert observed['replacement_slot_survived'], 'old_finalizer_released_successor_slot'
        assert observed['replacement_capacity_survived'], 'old_finalizer_released_successor_capacity'
        assert observed['old_transcript_token_released'], 'old_transcript_lock_leaked'
        assert observed['replacement_transcript_token_held'], 'successor_transcript_unlocked_too_early'
        assert observed['replacement_token_released'] and not observed['running_after_b']
        assert observed['final_model'] == prior, 'successor_restored_stale_one_shot'
        assert agent.interrupt_reasons and reply == 'new fixture finished'
        if reason == 'idle':
            assert observed['old_session_id'] != observed['new_session_id'], 'fresh_id_branch_not_exercised'
        else:
            assert observed['old_session_id'] == observed['new_session_id'], 'same_id_branch_not_exercised'
    finally:
        allow_old_exit.set()
        if not old_task.done():
            await asyncio.wait_for(old_task, 4)
        for token in tokens.values():
            g._turn_leases.release(token)


@pytest.mark.asyncio
@pytest.mark.parametrize('has_prior', [False, True])
async def test_stop_core_settles_without_successor_before_old_finalizer(rig, has_prior):
    g, key = rig.g, rig.key
    prior = install_prior(rig, has_prior)
    ready, finish = asyncio.Event(), asyncio.Event()
    agent = RecordingAgent()

    async def work(ev, source, routing_key, generation):
        g._session_state(key).turn.agent = agent
        ready.set()
        await finish.wait()
        return 'stopped fixture finished'

    g._handle_message_with_agent = work
    task = asyncio.create_task(g._handle_message(event(rig, 'ONLY')))
    try:
        await asyncio.wait_for(ready.wait(), 4)
        await g._interrupt_and_clear_session(key, rig.source,
            interrupt_reason='Stop requested', invalidation_reason='fixture_stop')
        at_stop = snapshot(g, key)
        clear_at_stop = not g._is_session_running(key)
        finish.set()
        await asyncio.wait_for(task, 4)
        emit('stop_without_successor', has_prior=has_prior, expected_prior=prior,
             at_stop=at_stop, after_finalizer=snapshot(g, key), slot_clear_at_stop=clear_at_stop,
             slot_clear_after_finalizer=not g._is_session_running(key), interrupts=agent.interrupt_reasons)
        assert at_stop == prior, 'stop_not_settled_before_finalizer'
        assert snapshot(g, key) == prior
        assert clear_at_stop and not g._is_session_running(key)
        assert agent.interrupt_reasons == ['Stop requested']
    finally:
        finish.set()
        if not task.done():
            await asyncio.wait_for(task, 4)


@pytest.mark.asyncio
@pytest.mark.parametrize('has_prior', [False, True])
async def test_normal_outer_finalizer_still_restores_own_choice(rig, has_prior):
    g, key = rig.g, rig.key
    prior = install_prior(rig, has_prior)
    inside = []

    async def work(*args):
        inside.append(snapshot(g, key))
        return 'normal fixture finished'

    g._handle_message_with_agent = work
    reply = await g._handle_message(event(rig, 'NORMAL'))
    emit('normal_control', has_prior=has_prior, expected_prior=prior, inside=inside,
         after_finalizer=snapshot(g, key), slot_clear=not g._is_session_running(key), reply=reply)
    assert inside[0]['provider'] == 'moa'
    assert snapshot(g, key) == prior and not g._is_session_running(key)
    assert reply == 'normal fixture finished'
