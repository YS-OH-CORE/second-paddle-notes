"""A new single-line model approval must not inherit an older inline request.

Reuses this PR's own gateway fixture. Routing and slash-confirm code are real;
model resolution, warning policy, adapter delivery and the final agent are fakes.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

H = runpy.run_path(str(Path(__file__).with_name('test_model_multiline_payload.py')))


@pytest.mark.parametrize('expire_first', [False, True], ids=['superseded', 'expired_then_replaced'])
def test_new_model_approval_does_not_route_old_payload(tmp_path, monkeypatch, expire_first):
    async def scenario():
        from tools import slash_confirm
        import gateway.run_inbound as inbound
        import gateway.slash_commands_model as model_commands

        H['_setup_isolated_home'](tmp_path, monkeypatch)
        H['_quiet_model_switch_guards'](monkeypatch)
        H['_fire_selection_guard'](monkeypatch)
        seen = []
        H['_fake_switch_model'](monkeypatch, seen_raw_inputs=seen)
        runner, adapter = H['_make_runner']()
        make_event = lambda text: H['_make_event'](text, thread_id='thread-replacement')
        key = runner._session_key_for_source(make_event('').source)
        slash_confirm.clear(key)
        clock = [1000.0]
        monkeypatch.setattr(slash_confirm, 'time', SimpleNamespace(time=lambda: clock[0]))
        try:
            first = await runner._handle_message(make_event('/model old-proposal\nReply only OLD-REQUEST.'))
            assert 'Cost guard' in first
            old = slash_confirm.get_pending(key)
            assert old and old['command'] == 'model'
            assert runner._model_inline_payload_stash()[key] == 'Reply only OLD-REQUEST.'
            runner._handle_message_with_agent.assert_not_awaited()
            expired = False
            if expire_first:
                clock[0] += slash_confirm.DEFAULT_TIMEOUT_SECONDS + 1
                # Exercise the real timeout check; no sleep and no permission setting change.
                expired = slash_confirm.clear_if_stale(key)
                assert expired and slash_confirm.get_pending(key) is None
            second = await runner._handle_message(make_event('/model new-proposal'))
            assert 'Cost guard' in second
            new = slash_confirm.get_pending(key)
            assert new and new['confirm_id'] != old['confirm_id']
            # This approval names the NEW pending model switch. It has no inline task.
            reply = await runner._handle_message(make_event('!approve'))
            routed = [call.args[0].text for call in runner._handle_message_with_agent.await_args_list]
            observation = {
                'case': 'expired_then_replaced' if expire_first else 'superseded',
                'old_confirm_id': old['confirm_id'], 'new_confirm_id': new['confirm_id'],
                'old_confirm_expired': expired, 'new_request': '/model new-proposal',
                'selected_model': runner._session_model_overrides[key]['model'],
                'agent_boundary_payloads': routed, 'reply': str(reply),
                'stash_after': dict(runner._model_inline_payload_stash()),
                'imports': {'inbound': inbound.__file__, 'model_commands': model_commands.__file__,
                            'confirmation': slash_confirm.__file__},
                'real_model_calls': 0, 'real_messages_sent': 0,
            }
            path = os.environ.get('MODEL_CONFIRM_OBSERVATIONS')
            if path:
                with open(path, 'a', encoding='utf-8') as out:
                    out.write(json.dumps(observation, ensure_ascii=False) + '\n')
            assert observation['selected_model'] == 'new-proposal'
            assert routed == [], 'A new single-line approval routed an old inline request: ' + repr(routed)
        finally:
            slash_confirm.clear(key)
    asyncio.run(scenario())
