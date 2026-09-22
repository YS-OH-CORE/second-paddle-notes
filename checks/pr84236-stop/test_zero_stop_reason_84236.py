"""Regression for explicit user_stop with a non-empty diagnostic message.

Uses PR #84236's own agent fixture and the complete imported finalize_turn.
No live model, terminal command, platform delivery or user records are used.
"""
from pathlib import Path
import runpy
import pytest

H = runpy.run_path(str(Path(__file__).with_name('test_turn_finalizer_interrupted_fallback.py')))

@pytest.mark.parametrize('kind,message,prior,expectation', [
    ('user_stop', 'keyboard interrupt', None, 'stopped'),
    ('user_stop', 'Stop requested by user', None, 'stopped'),
    ('user_stop', None, None, 'stopped'),
    ('user_stop', '', None, 'stopped'),
    ('client_disconnect', 'SSE client disconnected', None, 'disconnect'),
    (None, 'Please work on the next question', None, 'silent'),
    (None, None, None, 'interrupt'),
    ('user_stop', 'keyboard interrupt', 'partial streamed answer', 'preserve'),
], ids=['explicit-keyboard-reason','explicit-stop-reason','explicit-no-message',
        'explicit-empty-message','disconnect-reason','genuine-redirect',
        'legacy-stop','partial-text'])
def test_explicit_stop_is_not_redirect(kind, message, prior, expectation):
    agent = H['_StubAgent'](stop_kind=kind)
    agent._interrupt_message = message
    result = H['_finalize'](agent, H['_killed_tool_transcript'](), final_response=prior)
    actual = result['final_response']
    print({'stop_kind': kind, 'message': message, 'final_response': actual})
    assert result['interrupted'] is True
    assert result['completed'] is False
    if expectation == 'silent':
        assert not actual
    elif expectation == 'preserve':
        assert actual == prior
    else:
        assert isinstance(actual, str) and expectation in actual.lower()
