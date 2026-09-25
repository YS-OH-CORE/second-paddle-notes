"""Source-selected Honcho write-boundary probe, not a live provider test.

Youngseok Oh x Zero (AI collaboration partners).
Exact upstream methods; fake manager/SDK and deterministic thread scheduling.
No agent, LLM, credentials, hosted service, or real user-memory access.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
import logging
import socket
import sys
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace as NS

PIN = '7b761da2de4979e424510ca7022bf9527aa65b68'
BLOBS = {
    'provider.py': '14255ce5a1143e1a78c4b3c6e28c48c3512f8871',
    'migration.py': '9fd2ca17b4936ceafb391f58529c645dac222218',
}
METHODS = ('_do_session_init', '_session_ready', '_writes_enabled',
           '_ready_or_kick_init', '_chunk_message', 'sync_turn',
           '_bot_turn_write_refusal', '_spawn_write', 'on_memory_write',
           'on_session_end', '_tool_profile', '_tool_conclude', 'handle_tool_call')


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


class InlineThread:
    """Fixture scheduler: executes synchronously; no concurrency claims."""
    def __init__(self, target, **kwargs): self.target = target
    def start(self): self.target()
    def join(self, timeout=None): pass
    def is_alive(self): return False


class AuthError(Exception): pass


def error(text): return json.dumps({'error': text})


def selected_class(path, class_name, selected, namespace):
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text, filename=str(path))
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    found = [n for n in original.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and (selected is None or n.name in selected)]
    if selected is not None:
        assert {n.name for n in found} == set(selected)
    cls = copy.deepcopy(original)
    cls.bases, cls.keywords, cls.decorator_list = [], [], []
    cls.body = copy.deepcopy(found)
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), cls], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[class_name], {n.name: {'start': n.lineno, 'end': n.end_lineno} for n in found}


class FakeSession:
    def __init__(self, messages, owner):
        self.messages = list(messages)
        self.user_peer_id = owner
        self.assistant_peer_id = 'assistant'
        self.honcho_session_id = 'fixture-session'
    def add_message(self, role, content, **kwargs):
        self.messages.append({'role': role, 'content': content, **kwargs})


def run(root, out):
    out.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name, expected in BLOBS.items():
        data = (root / name).read_bytes()
        assert git_blob(data) == expected, f'Unexpected upstream source: {name}'
        sources[name] = {'git_blob': expected, 'sha256': hashlib.sha256(data).hexdigest()}
        (out / name).write_bytes(data)
    namespace = {'logger': logging.getLogger('fixture'), 'Path': Path, 'json': json,
                 'HonchoAuthError': AuthError, 'tool_error': error,
                 '_is_internal_gateway_turn': lambda s: False,
                 'sanitize_context': lambda s: s,
                 'spawn_context_thread': lambda fn, **kw: InlineThread(fn),
                 '_PREWARM_QUERY': 'fixture-only',
                 '_MEMORY_FILES': (
                     ('MEMORY.md', 'consolidated_memory.md', 'Long-term agent notes and preferences', 'user'),
                     ('USER.md', 'user_profile.md', 'User profile and preferences', 'user'),
                     ('SOUL.md', 'agent_soul.md', 'Agent persona and identity configuration', 'ai'))}
    # _MEMORY_FILES is evaluated from the original module, not trusted from this fixture.
    mig_tree = ast.parse((root / 'migration.py').read_text())
    assignment = next(n for n in mig_tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == '_MEMORY_FILES' for t in n.targets))
    namespace['_MEMORY_FILES'] = ast.literal_eval(assignment.value)
    Provider, provider_lines = selected_class(root/'provider.py', 'HonchoMemoryProvider', METHODS, namespace)
    Migration, migration_lines = selected_class(root/'migration.py', 'SessionMigrationMixin', None, namespace)
    Provider._TOOL_HANDLERS = {'honcho_profile': Provider._tool_profile,
                              'honcho_conclude': Provider._tool_conclude}
    Provider._resolve_session_key = lambda self, cfg, session_id, **kw: 'fixture-session'

    class Manager(Migration):
        def __init__(self, *, warm=False, owner='owner'):
            self.events = []
            self.session = FakeSession([{'role': 'user', 'content': 'past fixture'}] if warm else [], owner)
            self._sessions_cache = {'fixture-session': self}
        def get_or_create(self, key, **kw):
            self.events.append({'op':'get_or_create'})
            return self.session
        def _cached_session(self, key): return self.session
        def _declared_owner_peer_id(self): return 'owner'
        def _sdk_session(self, key): return self
        def _get_or_create_peer(self, key): return key
        def _authed_call(self, label, fn): return fn()
        def upload_file(self, **kw):
            name, content, mime = kw['file']
            self.events.append({'op':'upload_file', 'name': name, 'peer':kw['peer'],
                                'content_sha256':hashlib.sha256(content).hexdigest(),
                                'bytes':len(content)})
        def resolve_author_peer_id(self, *a, **kw): return 'owner'
        def save(self, session): self.events.append({'op':'save', 'messages':len(session.messages)})
        def create_conclusion(self, key, content, **kw):
            self.events.append({'op':'create_conclusion', 'content':content}); return True
        def delete_conclusion(self, key, ident, **kw):
            self.events.append({'op':'delete_conclusion', 'id':ident}); return True
        def list_conclusions(self, key, **kw):
            self.events.append({'op':'list_conclusions'}); return [{'id':'fixture-id', 'content':'old fixture'}]
        def set_peer_card(self, key, card, **kw):
            self.events.append({'op':'set_peer_card', 'card':card}); return card
        def get_peer_card(self, key, **kw):
            self.events.append({'op':'get_peer_card'}); return ['old fixture']
        def flush_all(self): self.events.append({'op':'flush_all'})

    rows = []
    with tempfile.TemporaryDirectory(prefix='zero-memory-fixture-') as home:
        memory = Path(home)/'memories'; memory.mkdir()
        for filename, _, _, _ in namespace['_MEMORY_FILES']:
            (memory/filename).write_text('SYNTHETIC FIXTURE ' + filename, encoding='utf-8')
        client = types.ModuleType('plugins.memory.honcho.client')
        client.get_honcho_client = lambda cfg: object()
        session_module = types.ModuleType('plugins.memory.honcho.session')
        session_module.HonchoAuthError = AuthError
        constants = types.ModuleType('hermes_constants')
        constants.get_hermes_home = lambda: Path(home)
        # Modules stand in only for collaborator construction, never for the selected method bodies.
        sys.modules['plugins.memory.honcho.client'] = client
        sys.modules['plugins.memory.honcho.session'] = session_module
        sys.modules['hermes_constants'] = constants

        def prepared(flag, *, warm=False, owner='owner', strategy='per-directory', bot=False):
            p = Provider()
            p._config = NS(save_messages=flag, message_max_chars=25000,
                           session_strategy=strategy, context_tokens=1200)
            p._manager = Manager(warm=warm, owner=owner)
            p._session_key, p._session_initialized = 'fixture-session', True
            p._cron_skipped, p._recall_mode, p._recall_sync = False, 'tools', False
            p._query_rewriter = None; p._query_rewrite_enabled = False
            p._init_thread = p._sync_thread = p._memwrite_thread = None
            p._turn_author = {'is_bot':bot}
            return p

        cases = ('sync_turn', 'mirror_profile', 'session_end', 'conclusion_create',
                 'conclusion_delete', 'card_write', 'conclusion_list', 'card_read',
                 'cold_owner_init', 'warm_owner_init', 'per_session_init', 'nonowner_init',
                 'invalid_conclusion', 'bot_conclusion')
        for flag in (False, True):
            for case in cases:
                p = prepared(flag, warm=case=='warm_owner_init',
                             owner='visitor' if case=='nonowner_init' else 'owner',
                             strategy='per-session' if case=='per_session_init' else 'per-directory',
                             bot=case=='bot_conclusion')
                manager = p._manager
                result = None
                if case == 'sync_turn': p.sync_turn('fixture question', 'fixture answer')
                elif case == 'mirror_profile': p.on_memory_write('add', 'user', 'fixture fact')
                elif case == 'session_end': p.on_session_end([])
                elif case in ('conclusion_create', 'bot_conclusion'):
                    result = p.handle_tool_call('honcho_conclude', {'conclusion':'fixture fact'})
                elif case == 'conclusion_delete':
                    result = p.handle_tool_call('honcho_conclude', {'delete_id':'fixture-id'})
                elif case == 'card_write':
                    result = p.handle_tool_call('honcho_profile', {'card':['fixture fact']})
                elif case == 'conclusion_list': result = p.handle_tool_call('honcho_conclude', {'list':True})
                elif case == 'card_read': result = p.handle_tool_call('honcho_profile', {})
                elif case == 'invalid_conclusion':
                    result = p.handle_tool_call('honcho_conclude', {'list':True, 'conclusion':'fixture fact'})
                else:
                    p._session_initialized = False
                    session_module.HonchoSessionManager = lambda **kw: manager
                    p._do_session_init(p._config, 'fixture-session')
                    assert p._session_initialized is True
                counts = {}
                for e in manager.events: counts[e['op']] = counts.get(e['op'],0)+1
                expected = {
                    'sync_turn': {'get_or_create':1, 'save':1} if flag else {},
                    'mirror_profile': {'create_conclusion':1} if flag else {},
                    'session_end': {'flush_all':1} if flag else {},
                    'conclusion_create': {'create_conclusion':1},
                    'conclusion_delete': {'delete_conclusion':1},
                    'card_write': {'set_peer_card':1},
                    'conclusion_list': {'list_conclusions':1},
                    'card_read': {'get_peer_card':1},
                    'cold_owner_init': {'get_or_create':1, 'upload_file':3},
                    'warm_owner_init': {'get_or_create':1},
                    'per_session_init': {'get_or_create':1},
                    'nonowner_init': {'get_or_create':1},
                    'invalid_conclusion': {}, 'bot_conclusion': {},
                }[case]
                assert counts == expected, (flag, case, counts, expected)
                if case in ('bot_conclusion', 'invalid_conclusion'):
                    assert 'error' in json.loads(result)
                elif result is not None:
                    assert 'error' not in json.loads(result), (case, result)
                row = {'saveMessages':flag, 'case':case, 'counts':counts,
                       'result':json.loads(result) if result else None, 'events':manager.events}
                rows.append(row)
                print(json.dumps(row), flush=True)
    report = {'success':True, 'upstream_commit':PIN, 'sources':sources,
              'source_selected_methods':provider_lines, 'migration_methods':migration_lines,
              'observations':rows, 'count':len(rows), 'new_model_calls':0,
              'scope':'Source-selected control-flow unit probe with fake manager/SDK, inline scheduling, synthetic files; NOT full module imports, live Honcho, CLI isolation, concurrent invocation or no-metadata-write guarantee.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    # Setup downloads happen in the workflow, before this network-denied subprocess.
    def deny(*args, **kwargs): raise RuntimeError('Network denied in unit probe')
    socket.socket.connect = deny
    socket.create_connection = deny
    socket.getaddrinfo = deny
    run(args.source_dir.resolve(), args.out.resolve())
