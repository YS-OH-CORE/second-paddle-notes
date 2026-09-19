"""Check both sides of the port on the real GatewayRunner method.

The transport and model are fixture objects. No live model or account is used.
Prepared by Zero with Youngseok Oh's problem direction.
"""
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from gateway.config import Platform
from gateway.slash_commands_model import _ModelSwitchContext, ModelSwitchConfirmation

H = runpy.run_path(str(Path(__file__).with_name('test_model_command_reasoning_flag.py')))
M = runpy.run_path(str(Path(__file__).with_name('test_model_multiline_payload.py')))


@pytest.mark.asyncio
@pytest.mark.parametrize('effort,once,picker,persist,applies', [
    ('high', False, False, False, True),
    ('high', False, False, True, True),
    ('high', True, False, False, False),
    ('high', True, True, False, True),
    (None, False, False, False, False),
])
async def test_success_keeps_type_and_reasoning_scope(effort, once, picker, persist, applies):
    runner, calls = H['_runner']()
    runner._model_switch_confirmation = AsyncMock(return_value='모델 변경 완료')
    ctx = _ModelSwitchContext(session_key='telegram:c1', source=None, config_path=None,
                              persist_global=persist, one_turn=once, reasoning_effort=effort)
    source = SimpleNamespace(platform=Platform.TELEGRAM)
    result = SimpleNamespace(new_model='m', target_provider='nous')
    reply = await runner._commit_model_switch(result, ctx, source=source, picker=picker)
    assert isinstance(reply, ModelSwitchConfirmation), 'Final reply must retain the routing type after concatenation'
    assert str(reply) == '모델 변경 완료' + ('\neffort set' if applies else '')
    assert ('applied' in calls) is applies
    if applies:
        assert calls['applied'] == ('telegram:c1', 'telegram', effort, persist)
    runner._record_model_switch.assert_awaited_once()
    assert runner._record_model_switch.await_args.kwargs['one_turn'] is (False if picker else once)


@pytest.mark.asyncio
async def test_failed_switch_is_not_a_success_and_does_not_apply_reasoning():
    runner, calls = H['_runner']()
    runner._switch_cached_agent_model = lambda *args, **kwargs: 'switch rejected'
    ctx = _ModelSwitchContext(session_key='k', source=None, config_path=None,
                              persist_global=False, reasoning_effort='high')
    reply = await runner._commit_model_switch(SimpleNamespace(), ctx,
                                               source=SimpleNamespace(platform=Platform.TELEGRAM))
    assert reply == 'switch rejected'
    assert not isinstance(reply, ModelSwitchConfirmation)
    assert 'applied' not in calls
    runner._record_model_switch.assert_not_awaited()
    runner._model_switch_confirmation.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('guarded', [False, True])
async def test_inline_request_and_reasoning_arrive_together(tmp_path, monkeypatch, guarded):
    from tools import slash_confirm
    import hermes_cli.model_switch as model_switch
    M['_setup_isolated_home'](tmp_path, monkeypatch)
    M['_quiet_model_switch_guards'](monkeypatch)
    if guarded:
        M['_fire_selection_guard'](monkeypatch)
    M['_fake_switch_model'](monkeypatch, seen_raw_inputs=[])
    monkeypatch.setattr(model_switch, 'resolve_display_context_length_async', AsyncMock(return_value=0))
    runner, adapter = M['_make_runner']()
    runner._apply_reasoning_selection = MagicMock(return_value='reasoning high applied')
    event = M['_make_event']('/model candidate --reasoning high --session\n  요청을 그대로 전달\n')
    key = runner._session_key_for_source(event.source)
    slash_confirm.clear(key)
    try:
        result = await runner._handle_message(event)
        if guarded:
            runner._apply_reasoning_selection.assert_not_called()
            runner._handle_message_with_agent.assert_not_awaited()
            result = await runner._handle_message(M['_make_event']('!approve'))
        assert result == 'agent reply'
        runner._apply_reasoning_selection.assert_called_once_with(key, 'matrix', 'high', persist_global=False)
        runner._handle_message_with_agent.assert_awaited_once()
        assert runner._handle_message_with_agent.await_args.args[0].text == '  요청을 그대로 전달\n'
        assert 'reasoning high applied' in adapter.send.await_args.args[1]
    finally:
        slash_confirm.clear(key)
