"""Create a reviewable two-module patch in an exact disposable PR checkout."""
from __future__ import annotations
import difflib
import hashlib
from pathlib import Path

BLOBS = {
    'gateway/run_inbound.py': '4a7e166c980264f38edbf836efa0d36a1961b93b',
    'gateway/slash_commands_model.py': '87e0668849bddada5c5c601bed23bf9387f77a21',
}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError('Expected exactly one inspected source anchor: ' + old[:80])
    return text.replace(old, new, 1)


def patch_sources(root: Path) -> str:
    originals = {}
    for name, expected in BLOBS.items():
        raw = (root/name).read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob != expected:
            raise ValueError('Inspected source changed: '+name)
        originals[name] = raw.decode('utf-8')
    inbound = originals['gateway/run_inbound.py']
    start = inbound.index('        _model_event, _inline_payload = self._split_inline_command_payload(event)\n',
                          inbound.index('    async def _hm_cmd_model('))
    end = inbound.index('        if not _inline_payload.strip():\n',
                        inbound.index('        # A successful switch supersedes', start))
    inbound = inbound[:start] + '''        _model_event, _inline_payload = self._split_inline_command_payload(event)
        # Keep this request's predecessor, not whichever request is current after an await.
        stash = self._model_inline_payload_stash()
        previous_payload = stash.get(_quick_key)
        _response = await self._handle_model_command(
            _model_event, inline_payload=_inline_payload,
        )
        if not isinstance(_response, ModelSwitchConfirmation):
            # The guard binds its own payload BEFORE publishing its confirmation. Do not
            # write it here: presentation can return after a newer request or a fast approval.
            return True, _response
        stash = self._model_inline_payload_stash()
        if previous_payload is not None and stash.get(_quick_key) is previous_payload:
            stash.pop(_quick_key, None)
''' + inbound[end:]
    model = originals['gateway/slash_commands_model.py']
    model = replace_once(model, '\n\nclass GatewayModelCommandsMixin:\n', '''

class _ModelInlinePayload(str):
    """Unique request-local token; text equality does not grant another callback ownership.

    The slash-confirm registry binds the callback to its confirm_id and lifetime.
    This token also lets the existing conversation-boundary cleanup revoke that callback.
    """

    __slots__ = ()


class GatewayModelCommandsMixin:
''')
    model = replace_once(model, '''        self, event: MessageEvent, ctx: _ModelSwitchContext, result
    ) -> tuple[bool, Optional[str]]:
''', '''        self, event: MessageEvent, ctx: _ModelSwitchContext, result, *, inline_payload: str = ""
    ) -> tuple[bool, Optional[str]]:
''')
    model = replace_once(model, '''        async def _on_cost_confirm(choice: str) -> str:
            # Pop-before-run: a stashed inline payload routes at most once, and cancel or a
            # failed switch drops it (slash_confirm.resolve already popped the confirm itself).
            stash_key = self._session_key_for_source(event.source)
            payload = self._model_inline_payload_stash().pop(stash_key, None)
''', '''        # Bind the exact request before registration can expose a button or text reply.
        # A fresh token is required even for empty/equal text: requests are not identified
        # by their wording. Expired/superseded confirm_ids cannot invoke this callback.
        stash_key = self._session_key_for_source(event.source)
        payload = _ModelInlinePayload(inline_payload)
        stash = self._model_inline_payload_stash()
        stash[stash_key] = payload

        async def _on_cost_confirm(choice: str) -> str:
            # Reset/supersession revokes ownership. Never consume a successor's payload.
            current_stash = self._model_inline_payload_stash()
            if current_stash.get(stash_key) is not payload:
                return "Model switch confirmation is no longer current."
            current_stash.pop(stash_key, None)
''')
    model = replace_once(model, '''            if payload and isinstance(reply, ModelSwitchConfirmation):
                return RoutedModelSwitchConfirmation(reply, payload)
''', '''            if payload.strip() and isinstance(reply, ModelSwitchConfirmation):
                return RoutedModelSwitchConfirmation(reply, str(payload))
''')
    model = replace_once(model, '''    async def _handle_model_command(self, event: MessageEvent) -> Optional[str]:
''', '''    async def _handle_model_command(
        self, event: MessageEvent, *, inline_payload: str = ""
    ) -> Optional[str]:
''')
    model = replace_once(model, '''        guard_fired, guard_reply = await self._model_selection_guard_reply(event, ctx, result)
''', '''        guard_fired, guard_reply = await self._model_selection_guard_reply(
            event, ctx, result, inline_payload=inline_payload,
        )
''')
    modified = {'gateway/run_inbound.py': inbound, 'gateway/slash_commands_model.py': model}
    diff = ''
    for name, text in modified.items():
        compile(text, name, 'exec')
        diff += ''.join(difflib.unified_diff(originals[name].splitlines(True), text.splitlines(True),
                                           fromfile='a/'+name, tofile='b/'+name))
        (root/name).write_text(text, encoding='utf-8')
    return diff
