"""Build a review patch only in a verified, disposable PR checkout."""
from __future__ import annotations
import difflib
from pathlib import Path


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError('Expected exactly one source anchor: ' + old[:100])
    return text.replace(old, new, 1)


def apply(root: Path, test_source: Path) -> bytes:
    originals = {}
    def load(name):
        text = (root/name).read_text(encoding='utf-8')
        originals[name] = text
        return text
    def save(name, text):
        compile(text, name, 'exec')
        (root/name).write_text(text, encoding='utf-8')

    name = 'gateway/run_inbound.py'
    text = load(name)
    start = text.index('        _model_event, _inline_payload = self._split_inline_command_payload(event)', text.index('    async def _hm_cmd_model('))
    end = text.index('        if not _inline_payload.strip():', start)
    text = text[:start] + '''        from tools import slash_confirm

        previous = slash_confirm.get_pending(_quick_key)
        _model_event, _inline_payload = self._split_inline_command_payload(event)
        _response = await self._handle_model_command(
            _model_event, inline_payload=_inline_payload,
        )
        if not isinstance(_response, ModelSwitchConfirmation):
            return True, _response
        # A successful direct switch supersedes an older model confirmation,
        # but must not clear a different confirmation registered meanwhile.
        if previous and previous.get("command") == "model":
            slash_confirm.clear(_quick_key, confirm_id=previous["confirm_id"])
''' + text[end:]
    save(name, text)

    name = 'gateway/slash_commands_model.py'
    text = load(name)
    start = text.index('    def _model_inline_payload_stash(')
    end = text.index('    async def _perform_model_switch(', start)
    text = text[:start] + text[end:]
    text = replace_once(text, '        self, event: MessageEvent, ctx: _ModelSwitchContext, result\n',
                              '        self, event: MessageEvent, ctx: _ModelSwitchContext, result,\n        *, inline_payload: str = "",\n')
    text = replace_once(text, '''            # Pop-before-run: a stashed inline payload routes at most once, and cancel or a
            # failed switch drops it (slash_confirm.resolve already popped the confirm itself).
            stash_key = self._session_key_for_source(event.source)
            payload = self._model_inline_payload_stash().pop(stash_key, None)
''', '''            # This callback captures only this request's immutable payload. The
            # registry binds the callback to its confirm_id and retires both on
            # replacement, expiry, cancellation or a conversation reset.
''')
    text = replace_once(text, '''            if payload and isinstance(reply, ModelSwitchConfirmation):
                return RoutedModelSwitchConfirmation(reply, payload)
''', '''            if inline_payload.strip() and isinstance(reply, ModelSwitchConfirmation):
                return RoutedModelSwitchConfirmation(reply, inline_payload)
''')
    text = replace_once(text, '    async def _handle_model_command(self, event: MessageEvent) -> Optional[str]:',
        '    async def _handle_model_command(\n        self, event: MessageEvent, *, inline_payload: str = "",\n    ) -> Optional[str]:')
    text = replace_once(text, '        guard_fired, guard_reply = await self._model_selection_guard_reply(event, ctx, result)',
        '        guard_fired, guard_reply = await self._model_selection_guard_reply(\n            event, ctx, result, inline_payload=inline_payload,\n        )')
    save(name, text)

    name = 'gateway/run.py'
    text = load(name)
    text = replace_once(text, '''    "_pending_turn_sidecar_notes",
    # Inline /model payloads retained across a pending selection-guard confirmation (routed once
    # after /approve); also dropped by cancel, a failed switch, or the next successful switch.
    "_pending_model_inline_payloads")''', '    "_pending_turn_sidecar_notes")')
    save(name, text)

    name = 'tools/slash_confirm.py'
    text = load(name)
    text = replace_once(text, '''def clear(session_key: str) -> None:
    """Drop the pending confirm for ``session_key`` without running it."""
    with _lock:
        _pending.pop(session_key, None)
''', '''def clear(session_key: str, *, confirm_id: Optional[str] = None) -> None:
    """Drop pending state; an optional ID prevents clearing a replacement."""
    with _lock:
        entry = _pending.get(session_key)
        if confirm_id is None or (entry and entry.get("confirm_id") == confirm_id):
            _pending.pop(session_key, None)
''')
    save(name, text)

    name = 'tests/gateway/test_model_multiline_payload.py'
    text = load(name)
    text = replace_once(text, '    assert runner._model_inline_payload_stash() == {session_key: "payload body"}',
                              '    assert not hasattr(runner, "_pending_model_inline_payloads")')
    text = text.replace('    assert runner._model_inline_payload_stash() == {}',
                        '    assert slash_confirm_mod.get_pending(session_key) is None')
    start = text.index('async def test_new_clears_staged_model_inline_payload():')
    # The existing last test checked only a manually filled shadow dictionary.
    text = text[:start] + '''async def test_new_clears_staged_model_inline_payload():
    """Reset retires the real pending callback, including its captured payload."""
    from tools import slash_confirm

    runner, _adapter = _make_runner()
    session_key = runner._session_key_for_source(_make_source())
    session_entry = _session_entry()
    runner.session_store._entries = {session_key: session_entry}
    runner.session_store.reset_session.return_value = session_entry
    runner.session_store._generate_session_key.return_value = session_key
    runner._async_session_store = None
    runner._session_db = None
    callback = AsyncMock(return_value="stale payload")
    other_callback = AsyncMock(return_value="other payload")
    slash_confirm.register(session_key, "reset-old", "model", callback)
    slash_confirm.register("other_key", "reset-other", "model", other_callback)
    try:
        await runner._handle_reset_command(_make_event("/new"))
        assert slash_confirm.get_pending(session_key) is None
        assert slash_confirm.get_pending("other_key")["confirm_id"] == "reset-other"
        assert await slash_confirm.resolve(session_key, "reset-old", "once") is None
        callback.assert_not_awaited()
        other_callback.assert_not_awaited()
    finally:
        slash_confirm.clear(session_key)
        slash_confirm.clear("other_key")
'''
    save(name, text)

    name = 'tests/gateway/test_model_confirmation_binding.py'
    if (root/name).exists():
        raise ValueError('New regression file already exists')
    originals[name] = ''
    save(name, test_source.read_text(encoding='utf-8'))
    patch = ''.join(''.join(difflib.unified_diff(old.splitlines(True),
        (root/name).read_text(encoding='utf-8').splitlines(True),
        fromfile='a/'+name if old else '/dev/null', tofile='b/'+name))
        for name, old in originals.items())
    return patch.encode('utf-8')
