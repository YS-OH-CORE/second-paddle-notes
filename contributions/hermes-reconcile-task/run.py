"""Run the unchanged reconciliation skill through real Hermes loading and terminal.

Uses a fresh disposable profile. The harness chooses the task; no model is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

HERMES_REV = '65a6b6831ef681da73955dd97a44f35794a2d4b9'
NAME = 'github-write-reconcile'
READER_SHA = 'a800e8a327d2d2b8531e9807ba9d42a8f6d20f611182a4c2a35c75ba1aac4349'
DOC_SHA = 'a83435536a333634efcbff79b2847860ddb47bbeef02cf5751c1e133dfd7ecb6'
EXIT = {'content_match': 0, 'content_conflict': 2, 'absent_at_snapshot': 3, 'unknown': 4}


def need(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def manifest(root):
    paths = sorted(root.rglob('*'))
    need(not any(p.is_symlink() for p in paths), 'SYMLINK_IN_SKILL')
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in paths if p.is_file()}


def child(upstream, out, authenticated):
    profile = out / 'sandbox/profile'
    record = {'status': 'incomplete', 'pid': os.getpid(), 'started_ns': time.monotonic_ns(),
              'hermes_revision': HERMES_REV, 'bridge_sha256': sha(Path(__file__).read_bytes()),
              'calls': [], 'host_network_attempts': [], 'denied_host_writes': [], 'host_subprocesses': []}
    sandbox = out / 'sandbox'
    def contained(value):
        if isinstance(value, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(value)).resolve()
            if not path.is_relative_to(out) and str(path) != '/dev/null':
                record['denied_host_writes'].append(str(path))
                raise PermissionError('WRITE_OUTSIDE_DISPOSABLE_RUNTIME')
    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo'):
            record['host_network_attempts'].append(event)
            raise RuntimeError('HOST_NETWORK_DISABLED')
        if event == 'subprocess.Popen':
            # Never retain environment values, where a read-only job token may live.
            record['host_subprocesses'].append({'executable': str(args[0]),
                'argv_sha256': sha(repr(args[1]).encode()), 'cwd': str(args[2])})
        if event == 'open':
            mode, flags = args[1:3]
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                contained(args[0])
        if event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod'):
            contained(args[0])
        if event in ('os.rename', 'os.link', 'os.symlink'):
            contained(args[0]); contained(args[1])
    sys.addaudithook(audit)
    terminal_module = None
    try:
        sys.path.insert(0, str(upstream))
        from tools import skills_tool, terminal_tool
        terminal_module = terminal_tool
        from tools.registry import registry
        from hermes_constants import get_hermes_home
        need(get_hermes_home().resolve() == profile, 'WRONG_PROFILE')
        for module, rel in ((skills_tool, 'tools/skills_tool.py'), (terminal_tool, 'tools/terminal_tool.py')):
            need(Path(module.__file__).resolve() == upstream / rel, 'WRONG_HOST_MODULE')
        def call(tool, arguments):
            result = json.loads(registry.dispatch(tool, arguments, task_id='reconcile-task', session_id='reconcile-task'))
            record['calls'].append({'tool': tool, 'arguments': arguments, 'result': result})
            save(out / 'host.json', record)
            return result
        listing = call('skills_list', {})
        need(listing.get('success') is True, 'LIST_FAILED')
        need(sum(s['name'] == NAME for s in listing['skills']) == 1, 'SKILL_NOT_UNIQUE')
        view = call('skill_view', {'name': NAME})
        need(view.get('success') is True and sha(view['content'].encode()) == DOC_SHA, 'DOCUMENT_CHANGED')
        loaded = Path(view['skill_dir']).resolve()
        need(loaded == profile / 'skills' / NAME, 'WRONG_LOADED_SKILL')
        source = call('skill_view', {'name': NAME, 'file_path': 'scripts/reconcile.py'})
        need(source.get('success') is True and sha(source['content'].encode()) == READER_SHA, 'READER_CHANGED')
        command = [sys.executable, '-B', '-S', str(loaded / 'scripts/reconcile.py'),
                   '--intent', str(sandbox / 'intent.json')]
        if authenticated:
            command.append('--use-github-token')
        terminal = call('terminal', {'command': shlex.join(command), 'workdir': str(loaded),
                                     'timeout': 55, 'background': False, 'pty': False})
        need(type(terminal.get('exit_code')) is int, 'NO_TERMINAL_EXIT')
        result = json.loads(terminal.get('output', ''))
        need(result['status'] in EXIT and EXIT[result['status']] == terminal['exit_code'], 'STATUS_EXIT_DIFFER')
        need(result.get('retry_authorized') is False and result.get('reader_sha256') == READER_SHA, 'RESULT_CONTRACT')
        need(not record['host_network_attempts'] and not record['denied_host_writes'], 'UNEXPECTED_HOST_ACCESS')
        need(bool(record['host_subprocesses']), 'NO_HOST_PROCESS_EXECUTION')
        imported = {}
        for module in tuple(sys.modules.values()):
            value = getattr(module, '__file__', None)
            if value:
                p = Path(value).resolve()
                if p.is_relative_to(upstream) and p.is_file():
                    imported[p.relative_to(upstream).as_posix()] = sha(p.read_bytes())
        need('tools/environments/local.py' in imported, 'LOCAL_BACKEND_NOT_IMPORTED')
        record.update(status='completed', result=result, tool_exit_code=terminal['exit_code'],
                      host_sources=dict(sorted(imported.items())))
    except Exception as exc:
        # Do not serialize arbitrary exception messages, which may contain input.
        record.update(status='failed', failure_type=type(exc).__name__)
        if isinstance(exc, ValueError) and len(exc.args) == 1 and str(exc.args[0]).isupper():
            record['failure_code'] = str(exc.args[0])
        raise
    finally:
        if terminal_module is not None:
            terminal_module.cleanup_all_environments()
        record['finished_ns'] = time.monotonic_ns()
        save(out / 'host.json', record)


def run(upstream, skill, intent, out, authenticated):
    need(not out.exists() and not out.is_relative_to(upstream) and not out.is_relative_to(skill), 'NEW_RUNTIME_REQUIRED')
    need(subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() == HERMES_REV, 'HOST_REVISION')
    before = manifest(skill)
    need(before['SKILL.md'] == DOC_SHA and before['scripts/reconcile.py'] == READER_SHA, 'SKILL_IDENTITY')
    raw = intent.read_bytes()
    need(len(raw) <= 8192, 'INTENT_TOO_LARGE')
    out.mkdir(parents=True)
    sandbox = out / 'sandbox'
    profile = sandbox / 'profile'
    for p in (profile, sandbox / 'home', sandbox / 'tmp', sandbox / 'work'):
        p.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill, profile / 'skills' / NAME)
    (sandbox / 'intent.json').write_bytes(raw)
    save(profile / 'config.yaml', {'skills': {'external_dirs': [], 'disabled': []},
                                  'terminal': {'backend': 'local'}})
    (profile / '.env').write_text('')
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(sandbox / 'home'), 'HERMES_HOME': str(profile),
           'TMPDIR': str(sandbox / 'tmp'), 'XDG_CONFIG_HOME': str(sandbox / 'home/config'),
           'XDG_CACHE_HOME': str(sandbox / 'home/cache'), 'TERMINAL_ENV': 'local',
           'TERMINAL_CWD': str(sandbox / 'work'), 'TERMINAL_TIMEOUT': '55',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'LANG': 'C.UTF-8', 'TERM': 'dumb'}
    if authenticated:
        need(bool(os.environ.get('GITHUB_TOKEN')), 'TOKEN_NOT_SET')
        env['GITHUB_TOKEN'] = os.environ['GITHUB_TOKEN']
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child', '--upstream', str(upstream),
               '--skill', str(skill), '--intent', str(intent), '--out', str(out)]
    if authenticated:
        command.append('--use-github-token')
    with (out / 'host.log').open('w', encoding='utf-8') as log:
        proc = subprocess.run(command, env=env, cwd=sandbox / 'work', stdout=log, stderr=subprocess.STDOUT, timeout=85)
    need(proc.returncode == 0, 'HOST_PROCESS_FAILED')
    record = json.loads((out / 'host.json').read_text())
    need(record['status'] == 'completed', 'HOST_RECORD_FAILED')
    need(manifest(skill) == before and manifest(profile / 'skills' / NAME) == before, 'SKILL_MUTATED')
    need(not subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain', '--untracked-files=no'], text=True).strip(), 'HOST_SOURCE_MUTATED')
    result = {'status': 'completed', 'scope': 'Harness-selected task through real Hermes skill and terminal handlers; not model-selected',
              'result': record['result'], 'tool_exit_code': record['tool_exit_code'], 'host_pid': record['pid'],
              'host_calls': len(record['calls']), 'intent_sha256': sha(raw), 'skill_files': before,
              'hermes_revision': HERMES_REV, 'bridge_sha256': sha(Path(__file__).read_bytes())}
    save(out / 'result.json', result)
    print(json.dumps(result, indent=2))
    return result['tool_exit_code']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--skill', type=Path, required=True)
    p.add_argument('--intent', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--use-github-token', action='store_true')
    p.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args()
    paths = [v.resolve() for v in (a.upstream, a.skill, a.intent, a.out)]
    if a.child:
        child(paths[0], paths[3], a.use_github_token)
    else:
        raise SystemExit(run(*paths, a.use_github_token))
