"""Supplemental PR107013 lifecycle checks; no live agent, transport or user data.

Real GatewayRunner state/restore/lease helpers and real asyncio locks. Persistence
and cache-eviction side effects are replaced with recording functions. The restore
call adapter follows each version's signature, without changing its implementation.
"""
from __future__ import annotations
import asyncio
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from gateway.run import GatewayRunner
from gateway.turn_lease import SessionTurnLeaseRegistry

KEY = 'fixture:displaced-owner'


def gateway():
    runner = object.__new__(GatewayRunner)
    runner._persist_active_agents = lambda: None
    runner._agent_cache_lock = None
    runner._agent_cache = {}
    evictions = []
    runner._evict_cached_agent = lambda key: evictions.append(key)
    return runner, runner._session_state(KEY), evictions


def call_restore(method, *args, generation):
    # The parent used an unguarded ABI; the follow-up adds the generation keyword.
    # This exercises the call shape each version's finalizer uses, not a fake guard.
    kwargs = {'run_generation': generation} if 'run_generation' in inspect.signature(method).parameters else {}
    method(*args, **kwargs)


def observe(case, **data):
    target = os.environ.get('LIFECYCLE_REVIEW_OBSERVATIONS')
    if target:
        import gateway.run_agent_cache as cache
        import gateway.run_inbound as inbound
        import gateway.turn_lease as lease
        data.update(case=case, source_modules={
            'cache': cache.__file__, 'inbound': inbound.__file__, 'lease': lease.__file__},
            model_calls=0, platform_messages=0)
        with Path(target).open('a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')


def test_stale_moa_restore_does_not_change_successor():
    runner, state, evictions = gateway()
    successor = {'provider': 'fixture', 'model': 'successor-choice'}
    state.persistent.run_generation = 3
    state.conversation.model_override = dict(successor)
    event = SimpleNamespace(_moa_disable_after_turn=True, _moa_run_generation=1,
                            _moa_restore_override={'model': 'old-choice'})
    call_restore(runner._restore_moa_one_shot, event, KEY, generation=1)
    observe('stale_moa', actual_model=state.conversation.model_override,
            expected_model=successor, cache_evictions=list(evictions),
            owner_generation=1, current_generation=3)
    assert state.conversation.model_override == successor, 'stale MoA cleanup changed the successor model'
    assert evictions == [], 'stale MoA cleanup evicted the successor cache'
    # Positive control: the owning generation can still restore its own choice.
    event._moa_run_generation = 3
    call_restore(runner._restore_moa_one_shot, event, KEY, generation=3)
    assert state.conversation.model_override == {'model': 'old-choice'}
    assert evictions == [KEY]


def test_stale_model_once_restore_preserves_successor_snapshot():
    runner, state, evictions = gateway()
    state.persistent.run_generation = 3
    state.conversation.model_override = {'model': 'successor-once'}
    snapshot = {'had_override': True, 'override': {'model': 'successor-prior'}, 'run_generation': 3}
    state.conversation.one_turn_restore = snapshot
    call_restore(runner._restore_pending_one_turn_model_override, KEY, generation=1)
    observe('stale_model_once', actual_model=state.conversation.model_override,
            snapshot_retained=state.conversation.one_turn_restore is snapshot,
            cache_evictions=list(evictions), owner_generation=1, current_generation=3)
    assert state.conversation.model_override == {'model': 'successor-once'}, 'stale cleanup restored the successor too early'
    assert state.conversation.one_turn_restore is snapshot, 'stale cleanup consumed another generation snapshot'
    assert evictions == []
    call_restore(runner._restore_pending_one_turn_model_override, KEY, generation=3)
    assert state.conversation.model_override == {'model': 'successor-prior'}
    assert state.conversation.one_turn_restore is None
    assert evictions == [KEY]


def install_token(state, token, generation):
    state.turn.lease_token = token
    state.turn.lease_generation = generation
    # Parent only had a current slot; follow-up has a map retaining displaced owners.
    if hasattr(state.turn, 'lease_tokens'):
        state.turn.lease_tokens[generation] = token


@pytest.mark.asyncio
async def test_displaced_owner_releases_old_lock_not_successor_lock():
    runner, state, _ = gateway()
    registry = SessionTurnLeaseRegistry()
    runner._turn_leases = registry
    old = await registry.acquire('old-transcript', owner_key=KEY, generation=1, timeout=1)
    new = await registry.acquire('new-transcript', owner_key=KEY, generation=3, timeout=1)
    try:
        install_token(state, old, 1)
        install_token(state, new, 3)
        state.persistent.run_generation = 3
        successor = object()
        state.turn.agent = successor
        slot_released = runner._release_running_agent_state(KEY, run_generation=1)
        old_released = runner._release_turn_lease(KEY, run_generation=1)
        observe('displaced_lease', old_release_result=old_released,
                old_locked=registry._leases['old-transcript'].lock.locked(),
                successor_locked=registry._leases['new-transcript'].lock.locked(),
                successor_token_current=state.turn.lease_token is new,
                successor_agent_current=state.turn.agent is successor,
                stale_slot_release_result=slot_released)
        assert not slot_released and state.turn.agent is successor
        assert old_released and old.released, 'displaced owner could not release its own retained lease'
        assert not registry._leases['old-transcript'].lock.locked(), 'old transcript stayed locked after its owner finished'
        assert registry._leases['new-transcript'].holder is new
        assert registry._leases['new-transcript'].lock.locked(), 'old cleanup unlocked the successor transcript'
        assert state.turn.lease_token is new and state.turn.lease_generation == 3
        # Old release is idempotent; successor's own release still works.
        assert runner._release_turn_lease(KEY, run_generation=1) is False
        assert runner._release_turn_lease(KEY, run_generation=3) is True
        assert not registry._leases['new-transcript'].lock.locked()
    finally:
        registry.release(old)
        registry.release(new)


@pytest.mark.asyncio
async def test_cancelled_waiter_preserves_alias_owner_and_future_progress():
    registry = SessionTurnLeaseRegistry(max_entries=1)
    owner = await registry.acquire('parent', owner_key='owner', generation=1, timeout=1)
    waiter = None
    resumed = None
    unrelated = None
    try:
        assert registry.rebind(owner, 'rotated')
        lease = registry._leases['parent']
        waiter = asyncio.create_task(registry.acquire('parent', owner_key='cancelled', generation=2, timeout=1))
        # Yield until the actual acquire reaches the lock; no monkeypatched lock/clock.
        async def pending():
            while lease.pending_acquires != 1:
                await asyncio.sleep(0)
        await asyncio.wait_for(pending(), timeout=1)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert lease.pending_acquires == 0 and lease.holder is owner and lease.lock.locked()
        unrelated = await registry.acquire('unrelated', owner_key='other', generation=1, timeout=1)
        assert registry._leases['parent'] is registry._leases['rotated'] is lease
        assert registry.release(owner)
        resumed = await registry.acquire('rotated', owner_key='resumed', generation=3, timeout=1)
        observe('cancelled_alias_waiter', cancelled_waiter_done=waiter.done(),
                resumed_owner=resumed.owner_key, old_token_released=owner.released,
                actual_lock_held=registry._leases['rotated'].lock.locked())
        assert resumed.owner_key == 'resumed'
        assert registry.release(owner) is False
        assert registry._leases['rotated'].holder is resumed
    finally:
        if waiter is not None and not waiter.done():
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
        registry.release(owner)
        registry.release(resumed)
        registry.release(unrelated)
