"""Initialization-only review of the illustrative proposal in Hermes #121935.

Public source is fetched once through the caller's existing GitHub CLI login.
Only the pinned _init_memory function is executed, with fake memory stores,
providers, logging and tool injection. No Hermes home, model or provider is used.
The two edits are locally authored interpretations, NOT the reporter's branch.
Zero, AI assistant, for Youngseok Oh / YS-OH-CORE.
"""
from __future__ import annotations
import ast
import base64
import builtins
from contextlib import suppress
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

REF = '749220ef0007f8d87bd1531f1c24b0fe93816385'
BLOB = 'a3e3bd91d4482d14a977efc7e95f2f9262f814b4'
FLAG = 'HERMES_SKIP_MEMORY_PROVIDER'
BRANCH = '    elif not skip_memory:\n        try:\n'
ADOPTION = '    if memory_manager is not None and not skip_memory:\n'
PREDICATE = 'not skip_memory and os.environ.get("HERMES_SKIP_MEMORY_PROVIDER", "").strip().lower() in ("1", "true", "yes")'
CASES = [
    ('fresh_flag_on', '1', False, False),
    ('reused_flag_on', '1', True, False),
    ('fresh_flag_absent', None, False, False),
    ('reused_flag_absent', None, True, False),
    ('fresh_existing_skip_memory', None, False, True),
    ('reused_existing_skip_memory', None, True, True),
]


def make_variants(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_init_memory']
    assert len(nodes) == 1
    text = ast.get_source_segment(source, nodes[0]) + '\n'
    assert text.count(BRANCH) == 1 and text.count(ADOPTION) == 1
    # The issue snippet is an elif: compose it at the external initialization branch.
    proposal = text.replace(BRANCH,
        '    elif ' + PREDICATE + ':\n        _ra().logger.info("external provider skipped")\n' + BRANCH)
    # Guard also the earlier reused-manager adoption; leave the supplied manager untouched.
    precedence = text.replace(ADOPTION,
        '    if ' + PREDICATE + ':\n        _ra().logger.info("external provider skipped")\n' + ADOPTION.replace('    if ', '    elif ', 1))
    return {'unmodified': text, 'illustrative_elif': proposal, 'guard_before_adoption': precedence}


def evaluate(text: str, flag: str | None, reused: bool, skip: bool) -> dict:
    counts = {'builtin_load_calls': 0, 'provider_load_calls': 0,
              'provider_init_calls': 0, 'injection_calls': 0, 'warnings': 0}
    class Store:
        def __init__(self, **kwargs):
            self.settings = kwargs
        def load_from_disk(self):
            # Deliberately no filesystem access.
            counts['builtin_load_calls'] += 1
    class Provider:
        def is_available(self):
            return True
    class Manager:
        def __init__(self):
            self.providers = []
        def add_provider(self, provider):
            self.providers.append(provider)
        def initialize_all(self, **kwargs):
            counts['provider_init_calls'] += 1
    def load_provider(name):
        assert name == 'fixture-provider'
        counts['provider_load_calls'] += 1
        return Provider()
    def inject(agent):
        # Invocation observer, not the real tool registry or runtime hook test.
        counts['injection_calls'] += 1
    def warning(*args):
        counts['warnings'] += 1
    modules = {
        'tools.memory_tool': SimpleNamespace(MemoryStore=Store,
            get_builtin_memory_config=lambda cfg: cfg['memory'],
            get_builtin_memory_store_flags=lambda cfg: (True, True)),
        'agent.memory_manager': SimpleNamespace(MemoryManager=Manager, inject_memory_provider_tools=inject),
        'plugins.memory': SimpleNamespace(load_memory_provider=load_provider),
    }
    def import_fixture(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name not in modules:
            raise AssertionError('Unexpected source import: ' + name)
        return modules[name]
    fake_builtins = dict(vars(builtins))
    fake_builtins['__import__'] = import_fixture
    logger = SimpleNamespace(info=lambda *a: None, debug=lambda *a: None, warning=warning)
    namespace = {'__builtins__': fake_builtins, 'suppress': suppress,
        'os': SimpleNamespace(environ={} if flag is None else {FLAG: flag}),
        'is_core_memory_provider': lambda name: name != 'fixture-provider',
        '_ra': lambda: SimpleNamespace(logger=logger),
        '_memory_provider_init_kwargs': lambda agent, platform: {'session_id': 'synthetic'},
        '_warned_unavailable_providers': set()}
    exec(compile(text, '<pinned-init-memory-variant>', 'exec'), namespace)
    agent = SimpleNamespace(enabled_toolsets=['memory'], disabled_toolsets=[], session_id='synthetic')
    cfg = {'memory': {'provider': 'fixture-provider', 'memory_char_limit': 2200,
                     'user_char_limit': 1375}, 'skills': {'auto_load': ['fixture-skill']}}
    original_cfg = deepcopy(cfg)
    borrowed = SimpleNamespace(providers=['existing-provider']) if reused else None
    namespace['_init_memory'](agent, cfg, skip, 'cli', memory_manager=borrowed)
    assert counts['warnings'] == 0 and counts['injection_calls'] == 1
    assert cfg == original_cfg
    assert counts['builtin_load_calls'] == 1 and agent._memory_store is not None
    assert agent._memory_enabled is True and agent._user_profile_enabled is True
    attached = agent._memory_manager is not None
    assert counts['provider_load_calls'] == counts['provider_init_calls'] == int(attached and not reused)
    return {**counts, 'manager_attached': attached,
            'borrowed_manager_attached': reused and agent._memory_manager is borrowed,
            'config_unchanged': cfg == original_cfg}


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix='zero-eval-memory-boundary-'))
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': REF,
              'source_blob': BLOB, 'python': sys.version.split()[0], 'success': False,
              'scope': 'AST-selected _init_memory, all collaborators fake; local interpretations of issue snippet',
              'provider_requests': 0, 'model_calls': 0, 'real_memory_reads_or_writes': 0,
              'cases': []}
    try:
        endpoint = f'repos/NousResearch/hermes-agent/contents/agent/agent_init.py?ref={REF}'
        p = subprocess.run(['gh', 'api', endpoint], capture_output=True, timeout=25,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if p.returncode:
            raise RuntimeError('Public source GET failed; no retry; exit=' + str(p.returncode))
        item = json.loads(p.stdout)
        raw = base64.b64decode(item['content'])
        assert len(raw) < 400000
        assert item['sha'] == BLOB == hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        report['source_sha256'] = hashlib.sha256(raw).hexdigest()
        (root / 'upstream_agent_init.py').write_bytes(raw)
        variants = make_variants(raw.decode('utf-8'))
        for label, text in variants.items():
            (root / (label + '.py')).write_text(text, encoding='utf-8')
        for case_id, flag, reused, skip in CASES:
            row = {'id': case_id, 'flag': flag, 'reused_input': reused, 'skip_memory': skip, 'results': {}}
            for label, text in variants.items():
                result = evaluate(text, flag, reused, skip)
                expected = not skip
                if flag == '1' and label == 'guard_before_adoption':
                    expected = False
                if flag == '1' and label == 'illustrative_elif' and not reused:
                    expected = False
                assert result['manager_attached'] == expected, (case_id, label, result)
                row['results'][label] = result
            report['cases'].append(row)
        report['function_evaluations'] = 18
        report['success'] = True
        # Four remaining cases are unchanged across all three source variants.
        assert all(len({json.dumps(r, sort_keys=True) for r in row['results'].values()}) == 1
                   for row in report['cases'][2:])
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:400]}
    finally:
        data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        (root / 'report.json').write_bytes(data)
        print('EVAL_MEMORY_REPORT=' + json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
        print('REPORT_SHA256=' + hashlib.sha256(data).hexdigest(), flush=True)
        print('SCRATCH=' + str(root), flush=True)
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
