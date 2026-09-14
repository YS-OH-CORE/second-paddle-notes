"""Load the existing skill through real, pinned Hermes tool-registry handlers.

No model call, user-profile installation, provider write or network exercise.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

HERMES_REV = '65a6b6831ef681da73955dd97a44f35794a2d4b9'
NAME = 'github-write-reconcile'
HOST_BLOBS = {
    'tools/skills_tool.py': '3e50e1ec7abf8a54f593e8d4415e729b4c651187',
    'tools/registry.py': 'f2469d41364b92e4f5f1da8df2934c24834cb966',
    'agent/skill_utils.py': '9a615e6a8a0b8e0d31e2af9799bbdf29c929a780',
}
SKILL_MD = 'a83435536a333634efcbff79b2847860ddb47bbeef02cf5751c1e133dfd7ecb6'
READER = 'a800e8a327d2d2b8531e9807ba9d42a8f6d20f611182a4c2a35c75ba1aac4349'
CASES = ('empty', 'full', 'reopened', 'markdown_only', 'disabled')


def need(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def manifest(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes())
            for p in sorted(root.rglob('*')) if p.is_file()}


def clean_env(root, profile):
    # Do not inherit provider credentials, real HOME, plugins, or user config.
    return {'PATH': os.environ.get('PATH', ''), 'HOME': str(root / 'home'),
            'HERMES_HOME': str(profile), 'TMPDIR': str(root / 'tmp'),
            'XDG_CONFIG_HOME': str(root / 'home/config'), 'XDG_CACHE_HOME': str(root / 'home/cache'),
            'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'LANG': 'C.UTF-8', 'TERM': 'dumb'}


def child(upstream, root, case):
    profile = Path(os.environ['HERMES_HOME']).resolve()
    sandbox = Path(os.environ['HOME']).resolve().parent
    network_attempts, process_attempts, denied_writes = [], [], []
    allowed_process = None
    report = {'case': case, 'status': 'incomplete', 'pid': os.getpid(),
              'started_ns': time.monotonic_ns(), 'hermes_revision': HERMES_REV,
              'profile': str(profile), 'calls': [], 'probe_sha256': sha(Path(__file__).read_bytes())}
    def contained(path):
        if isinstance(path, (str, bytes, os.PathLike)):
            target = Path(os.fsdecode(path)).resolve()
            if not target.is_relative_to(sandbox) and target != root / (case + '.json'):
                denied_writes.append(str(target))
                raise PermissionError('WRITE_OUTSIDE_TEST_SANDBOX')
    def audit(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo'):
            network_attempts.append(event)
            raise RuntimeError('NETWORK_DISABLED_DURING_HOST_LOAD')
        if event == 'subprocess.Popen':
            process_attempts.append(str(args[0]))
            if allowed_process is None or list(args[1]) != allowed_process:
                raise RuntimeError('UNEXPECTED_CHILD_PROCESS')
        if event == 'open':
            mode, flags = args[1], args[2]
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                contained(args[0])
        if event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod'):
            contained(args[0])
        if event in ('os.rename', 'os.link', 'os.symlink'):
            contained(args[0]); contained(args[1])
    sys.addaudithook(audit)
    try:
        sys.path.insert(0, str(upstream))
        import tools.skills_tool as skills_tool
        from tools.registry import registry
        from hermes_constants import get_hermes_home
        need(Path(skills_tool.__file__).resolve() == upstream / 'tools/skills_tool.py', 'WRONG_HOST_MODULE')
        need(get_hermes_home().resolve() == profile, 'WRONG_PROFILE')
        def call(tool, arguments):
            value = json.loads(registry.dispatch(tool, arguments, task_id='host-load-' + case))
            report['calls'].append({'tool': tool, 'arguments': arguments, 'result': value})
            return value
        listing = call('skills_list', {})
        view = call('skill_view', {'name': NAME})
        script = call('skill_view', {'name': NAME, 'file_path': 'scripts/reconcile.py'})
        need(listing.get('success') is True, 'LIST_FAILED')
        matches = [x for x in listing['skills'] if x['name'] == NAME]
        available = case in ('full', 'reopened', 'markdown_only')
        need(len(matches) == (1 if available else 0), 'DISCOVERY_RESULT')
        need(view.get('success') is available, 'VIEW_RESULT')
        if available:
            need(sha(view['content'].encode('utf-8')) == SKILL_MD, 'LOADED_DOCUMENT_CHANGED')
            need(view.get('readiness_status') == 'available', 'HOST_READINESS')
            need(Path(view['skill_dir']).resolve() == profile / 'skills' / NAME, 'WRONG_SKILL_PATH')
        executable = case in ('full', 'reopened')
        need(script.get('success') is executable, 'SUPPORT_FILE_RESULT')
        if executable:
            linked = [p for group in view['linked_files'].values() for p in group]
            need('scripts/reconcile.py' in linked, 'READER_NOT_LINKED')
            need(sha(script['content'].encode('utf-8')) == READER, 'LOADED_READER_CHANGED')
            command = [sys.executable, '-B', '-S', str(Path(view['skill_dir']) / 'scripts/reconcile.py'), '--help']
            allowed_process = command
            proc = subprocess.run(command, capture_output=True, text=True, timeout=10)
            allowed_process = None
            need(proc.returncode == 0 and '--intent' in proc.stdout and not proc.stderr, 'COPIED_CLI_HELP')
            report['cli_help'] = {'exit_code': proc.returncode, 'stdout': proc.stdout}
        elif case == 'markdown_only':
            need('not found' in script.get('error', '').lower(), 'MISSING_SCRIPT_CONTROL')
        elif case == 'disabled':
            need('disabled' in view.get('error', '').lower(), 'DISABLED_CONTROL')
        # Record the actual unmodified upstream files imported, not stand-in modules.
        imported = {}
        for module in tuple(sys.modules.values()):
            path = getattr(module, '__file__', None)
            if path:
                path = Path(path).resolve()
                if path.is_relative_to(upstream) and path.is_file():
                    imported[path.relative_to(upstream).as_posix()] = sha(path.read_bytes())
        report['host_sources'] = dict(sorted(imported.items()))
        report['dependencies'] = {d: importlib.metadata.version(d) for d in
                                  ('PyYAML', 'python-dotenv', 'rich', 'prompt_toolkit', 'Jinja2')}
        need(not network_attempts and not denied_writes, 'UNEXPECTED_HOST_ACCESS')
        need(len(process_attempts) == (1 if executable else 0), 'UNEXPECTED_HOST_PROCESS')
        report['status'] = 'verified'
    except Exception as exc:
        report.update(status='failed', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        report.update(network_attempts=network_attempts, process_attempts=process_attempts,
                      denied_writes=denied_writes, finished_ns=time.monotonic_ns())
        save(root / (case + '.json'), report)


def run(upstream, skill, out):
    need(upstream.is_dir() and skill.is_dir(), 'SOURCE_DIRECTORY_MISSING')
    revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    need(revision == HERMES_REV, 'HOST_REVISION')
    for name, expected in HOST_BLOBS.items():
        raw = (upstream / name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        need(actual == expected, 'HOST_BLOB_' + name)
    original = manifest(skill)
    need(original['SKILL.md'] == SKILL_MD and original['scripts/reconcile.py'] == READER, 'SKILL_IDENTITY')
    out.mkdir(parents=True, exist_ok=False)
    sandbox = out / 'sandbox'
    for name in ('home', 'tmp', 'work'):
        (sandbox / name).mkdir(parents=True)
    report = {'status': 'incomplete', 'hermes_revision': revision, 'skill_files': original,
              'scope': 'Real Hermes registered skill handlers in isolated profiles; no model selection or user installation', 'cases': []}
    profiles = {}
    try:
        for case in CASES:
            profile = sandbox / ('profile-full' if case == 'reopened' else 'profile-' + case)
            if case != 'reopened':
                profile.mkdir()
                (profile / 'skills').mkdir()
                config = {'skills': {'external_dirs': [], 'disabled': [NAME] if case == 'disabled' else []}}
                save(profile / 'config.yaml', config)  # JSON is valid YAML, with no templated input.
                (profile / '.env').write_text('', encoding='utf-8')
                if case in ('full', 'disabled'):
                    shutil.copytree(skill, profile / 'skills' / NAME)
                elif case == 'markdown_only':
                    target = profile / 'skills' / NAME
                    target.mkdir()
                    shutil.copyfile(skill / 'SKILL.md', target / 'SKILL.md')
            profiles[case] = profile
            with (out / (case + '.log')).open('w', encoding='utf-8') as log:
                proc = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--child', case,
                    '--upstream', str(upstream), '--skill', str(skill), '--out', str(out)],
                    env=clean_env(sandbox, profile), cwd=sandbox / 'work', stdout=log, stderr=subprocess.STDOUT, timeout=40)
            need(proc.returncode == 0, 'HOST_CHILD_FAILED_' + case)
            value = json.loads((out / (case + '.json')).read_text(encoding='utf-8'))
            need(value['status'] == 'verified', 'HOST_RECORD_STATUS')
            report['cases'].append({'case': case, 'pid': value['pid'], 'status': value['status'],
                                    'calls': len(value['calls']), 'cli_help_checked': 'cli_help' in value})
        need(len({c['pid'] for c in report['cases']}) == 5, 'PROCESS_REUSE')
        for case in ('full', 'disabled'):
            need(manifest(profiles[case] / 'skills' / NAME) == original, 'COPIED_SKILL_MUTATED')
        need(manifest(skill) == original, 'ORIGINAL_SKILL_MUTATED')
        need(not subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain', '--untracked-files=no'], text=True).strip(), 'UPSTREAM_MODIFIED')
        report.update(status='verified', registry_calls=15, cli_help_checks=2,
                      probe_sha256=sha(Path(__file__).read_bytes()))
    finally:
        save(out / 'summary.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--skill', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--child', choices=CASES)
    a = p.parse_args()
    paths = [v.resolve() for v in (a.upstream, a.skill, a.out)]
    child(paths[0], paths[2], a.child) if a.child else run(*paths)
