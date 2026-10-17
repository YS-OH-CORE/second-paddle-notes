"""PR73935 disk config -> real provider -> real manager; fake remote SDK only.
No live service, private profiles or patched config/parser/persistence methods.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize(
    'root_value,host_value,expected',
    [(False, None, False), (True, False, False), (False, True, True), (None, None, True)],
    ids=['root-false','host-false-over-root-true','host-true-over-root-false','legacy-default'],
)
def test_disk_config_controls_startup_content_upload(monkeypatch, tmp_path, root_value, host_value, expected):
    home = tmp_path / 'home'
    profile = home / 'synthetic-profile'
    memory = profile / 'memories'
    memory.mkdir(parents=True)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('HERMES_HOME', str(profile))
    for name in ('HONCHO_API_KEY','HONCHO_BASE_URL','HONCHO_ENVIRONMENT'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('HERMES_HONCHO_HOST', 'hermes')
    monkeypatch.chdir(profile)
    block = {'enabled': True, 'peerName': 'synthetic-owner', 'aiPeer': 'synthetic-agent',
             'workspace': 'synthetic-workspace', 'recallMode': 'tools',
             'initOnSessionStart': True, 'sessionStrategy': 'per-directory', 'writeFrequency': 'turn'}
    cfg = {'apiKey': 'synthetic-not-a-secret', 'hosts': {'hermes': block}}
    if root_value is not None:
        cfg['saveMessages'] = root_value
    if host_value is not None:
        block['saveMessages'] = host_value
    config_path = profile / 'honcho.json'
    config_path.write_text(json.dumps(cfg), encoding='utf-8')
    original_config = config_path.read_bytes()
    for name in ('MEMORY.md','USER.md','SOUL.md'):
        (memory/name).write_text('SYNTHETIC-'+name, encoding='utf-8')

    from plugins.memory.honcho import HonchoMemoryProvider
    from plugins.memory.honcho import client as client_module
    from plugins.memory.honcho import session as session_module

    peers, sessions, factory_values = {}, {}, []
    remote = MagicMock(name='remote-sdk-test-double')
    def peer(identifier):
        if identifier not in peers:
            value = MagicMock(name='remote-peer-'+identifier)
            value.id = identifier
            value.get_metadata.return_value = {}
            peers[identifier] = value
        return peers[identifier]
    def session(identifier):
        if identifier not in sessions:
            value = MagicMock(name='remote-session-'+identifier)
            value.id = identifier
            value.context.return_value = SimpleNamespace(messages=[])
            value.get_metadata.return_value = {}
            value.get_peer_configuration.return_value = SimpleNamespace(observe_me=None, observe_others=None)
            sessions[identifier] = value
        return sessions[identifier]
    remote.peer.side_effect = peer
    remote.session.side_effect = session
    def sdk_factory(config=None):
        if config is not None:
            # This value was loaded from disk by initialize(), not injected by the fixture.
            factory_values.append(config.save_messages)
        return remote
    monkeypatch.setattr(client_module, 'get_honcho_client', sdk_factory)
    monkeypatch.setattr(session_module, 'get_honcho_client', sdk_factory)
    import socket
    def deny_network(*args, **kwargs):
        raise AssertionError('Live network is outside this synthetic test')
    monkeypatch.setattr(socket.socket, 'connect', deny_network)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny_network)

    assert client_module.resolve_config_path() == config_path
    provider = HonchoMemoryProvider()
    try:
        provider.initialize('synthetic-session')
        assert provider._session_initialized is True, 'Inactive provider is not proof of suppression'
        assert isinstance(provider._manager, session_module.HonchoSessionManager)
        assert provider._config.save_messages is expected
        assert factory_values and all(value is expected for value in factory_values)
        # Real manager session construction and context read must occur in both arms.
        assert sessions and sum(s.context.call_count for s in sessions.values()) > 0
        uploads = [call for s in sessions.values() for call in s.upload_file.call_args_list]
        filenames = sorted(call.kwargs['file'][0] for call in uploads)
        if expected:
            assert filenames == ['agent_soul.md','consolidated_memory.md','user_profile.md']
            payload = b'\n'.join(call.kwargs['file'][1] for call in uploads)
            assert all(('SYNTHETIC-'+name).encode() in payload for name in ('MEMORY.md','USER.md','SOUL.md'))
        else:
            assert uploads == []
        assert config_path.read_bytes() == original_config
    finally:
        provider.shutdown()
