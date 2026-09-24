"""Real-import Signal configuration/inbound contract check for Hermes #121970.

Modes are run in fresh processes against a caller-provided scratch checkout.
The candidate is OUR reconstruction of public snippets, not the recipient's diff.
No actual Signal connection, message send, model, credential or service is used.
Zero, AI collaborator with Youngseok Oh (@YS-OH-CORE).
"""
from __future__ import annotations
import argparse
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import AsyncMock

REF = '749220ef0007f8d87bd1531f1c24b0fe93816385'
BLOB = 'f763db86f71d50a922d23b4f324da92ff6f5683e'
ACCOUNT = '+15550001111'
GROUP = 'synthetic-group'
CHANGED_CASES = {'self_false', 'self_quoted_false', 'self_false_attachment', 'home_aba'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def child(repo: Path, output: Path, label: str) -> int:
    # OS environment was replaced by the parent BEFORE any Hermes import.
    # A Python network guard is additional defense, not an OS-level sandbox.
    def no_network(*args, **kwargs):
        raise RuntimeError('Network is outside this synthetic inbound test')
    socket.socket.connect = socket.socket.connect_ex = no_network
    sys.path.insert(0, str(repo))
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override
    from gateway.config import Platform, load_gateway_config
    import gateway.platforms.signal as sig
    from gateway.platforms.signal import SignalAdapter
    assert Path(inspect.getfile(sig)).resolve() == repo / 'gateway/platforms/signal.py'
    report = {'label': label, 'source_commit': REF, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': sha((repo / 'gateway/platforms/signal.py').read_bytes()),
              'python': sys.version, 'cases': [], 'success': False,
              'scope': 'real YAML loader, real SignalAdapter and inbound handling; dispatch/attachments observed with AsyncMock; no Signal transport or gateway runner auth'}
    root = Path(tempfile.mkdtemp(prefix='signal-contract-homes-', dir=output))
    counter = 0

    def home(raw: str | None) -> Path:
        nonlocal counter
        counter += 1
        path = root / str(counter)
        path.mkdir()
        text = 'signal:\n  enabled: true\n  account: "' + ACCOUNT + '"\n  http_url: "http://127.0.0.1:9"\n'
        if raw is not None:
            text += '  note_to_self: ' + raw + '\n'
        (path / 'config.yaml').write_text(text, encoding='utf-8')
        return path

    @contextmanager
    def adapter_at(path: Path, *, mention: bool = False):
        token = set_hermes_home_override(path)
        before = (path / 'config.yaml').read_bytes()
        try:
            config = load_gateway_config()
            selected = config.platforms[Platform.SIGNAL]
            adapter = SignalAdapter(selected)
            # This case checks note_to_self YAML routing, not require_mention YAML plumbing.
            adapter.require_mention = mention
            adapter.handle_message = AsyncMock()
            adapter._collect_attachments = AsyncMock(return_value=([], []))
            yield adapter, selected
            assert (path / 'config.yaml').read_bytes() == before, 'Input config was rewritten'
            assert adapter.client is None, 'Unexpected Signal client creation'
        finally:
            reset_hermes_home_override(token)

    def envelope(kind: str = 'self', *, attachment: bool = False, mentioned: bool = True) -> dict:
        sent = {'destinationNumber': ACCOUNT, 'timestamp': 123456789,
                'message': ('@' + ACCOUNT + ' ') if mentioned and kind == 'group' else 'synthetic note'}
        if kind in ('group', 'blocked_group'):
            sent['groupInfo'] = {'groupId': GROUP if kind == 'group' else 'blocked-fixture', 'groupName': 'fixture'}
        if kind == 'other_destination':
            sent['destinationNumber'] = '+15550002222'
        if attachment:
            sent['attachments'] = [{'id': 'not-a-real-attachment', 'contentType': 'image/png', 'size': 8}]
        return {'envelope': {'sourceNumber': ACCOUNT, 'timestamp': 123456789,
                            'syncMessage': {'sentMessage': sent}}}

    def exercise(raw=None, kind='self', expected=1, attachment=False, mention=False, mentioned=True, echo=False):
        with adapter_at(home(raw), mention=mention) as (adapter, config):
            if raw == 'false':
                assert config.extra['note_to_self'] is False, 'Boolean lost in YAML loader'
            if raw == '"false"':
                assert config.extra['note_to_self'] == 'false', 'String not passed by real loader'
            event = envelope(kind, attachment=attachment, mentioned=mentioned)
            if echo:
                adapter._recent_sent_timestamps[123456789] = time.monotonic()
            asyncio.run(adapter._handle_envelope(deepcopy(event)))
            seen = adapter.handle_message.await_count
            downloads = adapter._collect_attachments.await_count
            assert seen == expected, f'dispatch count {seen}, expected {expected}'
            if expected == 0:
                assert downloads == 0, f'rejected message still fetched attachments: {downloads}'
            if seen and kind == 'group':
                assert adapter.handle_message.await_args.args[0].source.chat_id == 'group:' + GROUP
            return {'dispatches': seen, 'attachment_fetch_calls': downloads}

    def aba():
        a, b = home('false'), home(None)
        counts = []
        for path in (a, b, a):
            with adapter_at(path) as (adapter, _):
                asyncio.run(adapter._handle_envelope(envelope()))
                counts.append(adapter.handle_message.await_count)
        assert counts == [0, 1, 0], f'A(false), B(default), A(false) yielded {counts}'
        return {'dispatches_by_home': counts}

    cases = [
        ('self_unset', lambda: exercise()),
        ('self_true', lambda: exercise('true')),
        ('self_false', lambda: exercise('false', expected=0)),
        ('self_quoted_false', lambda: exercise('"false"', expected=0)),
        ('self_false_attachment', lambda: exercise('false', expected=0, attachment=True)),
        ('group_kept_with_self_destination', lambda: exercise('false', kind='group')),
        ('group_without_mention_rejected', lambda: exercise('false', kind='group', expected=0, mention=True, mentioned=False)),
        ('group_with_mention_kept', lambda: exercise('false', kind='group', mention=True)),
        ('group_not_allowed', lambda: exercise('false', kind='blocked_group', expected=0)),
        ('group_outbound_echo', lambda: exercise('false', kind='group', expected=0, echo=True)),
        ('other_outbound_destination', lambda: exercise('false', kind='other_destination', expected=0)),
        ('home_aba', aba),
    ]
    for name, check in cases:
        row = {'name': name}
        try:
            row['observation'] = check()
            row['passed'] = True
        except Exception as exc:
            row.update(passed=False, error_type=type(exc).__name__, error=str(exc))
        report['cases'].append(row)
        print('SIGNAL_CONTRACT_CASE ' + json.dumps(row), flush=True)
    failed = {r['name'] for r in report['cases'] if not r['passed']}
    report['failed_cases'] = sorted(failed)
    report['expected_failure_set'] = sorted(CHANGED_CASES) if label == 'base' else []
    report['success'] = failed == (CHANGED_CASES if label == 'base' else set())
    report['versions'] = {name: importlib.metadata.version(name) for name in ['PyYAML', 'httpx', 'pydantic']}
    (output / (label + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('SIGNAL_CONTRACT_REPORT ' + json.dumps(report), flush=True)
    return 0 if report['success'] else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--child', choices=['base', 'candidate'])
    args = p.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.child:
        return child(repo, out, args.child)
    source = repo / 'gateway/platforms/signal.py'
    original = source.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(original)).encode() + b'\0' + original).hexdigest()
    if blob != BLOB:
        raise RuntimeError('Refusing unreviewed source: Git blob mismatch')
    text = original.decode('utf-8')
    replacements = [
        ('from utils import TRUTHY_STRINGS\n', 'from utils import TRUTHY_STRINGS, is_truthy_value\n'),
        ('        self.ignore_stories = extra.get("ignore_stories", True)\n',
         '        self.ignore_stories = extra.get("ignore_stories", True)\n        self.note_to_self = is_truthy_value(extra.get("note_to_self"), default=True)\n'),
        ('        if dest != self._account_normalized and not (sent_msg.get("groupInfo") or {}).get("groupId"):\n',
         '        is_group_sync = bool((sent_msg.get("groupInfo") or {}).get("groupId"))\n        if not is_group_sync and not (dest == self._account_normalized and self.note_to_self):\n'),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise RuntimeError('Reviewed edit anchor missing or ambiguous')
        text = text.replace(old, new, 1)
    candidate = text.encode('utf-8')
    import difflib
    patch = ''.join(difflib.unified_diff(original.decode().splitlines(keepends=True), text.splitlines(keepends=True),
                                         fromfile='a/gateway/platforms/signal.py', tofile='b/gateway/platforms/signal.py'))
    (out / 'reconstructed-candidate.patch').write_text(patch, encoding='utf-8')
    results = {}
    try:
        for label, content in [('base', original), ('candidate', candidate)]:
            source.write_bytes(content)
            clean_home = out / (label + '-home')
            clean_home.mkdir(exist_ok=False)
            env = {'PATH': os.environ['PATH'], 'HOME': str(clean_home), 'HERMES_HOME': str(clean_home / 'hermes'),
                   'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'SIGNAL_ALLOWED_USERS': ACCOUNT,
                   'SIGNAL_GROUP_ALLOWED_USERS': GROUP, 'SIGNAL_REQUIRE_MENTION': 'false',
                   'HERMES_SKIP_PROJECT_ENV': '1', 'LANGSMITH_TRACING': 'false'}
            run = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--repo', str(repo),
                                  '--out', str(out), '--child', label], env=env, cwd=clean_home,
                                 capture_output=True, text=True, timeout=90)
            (out / (label + '.stdout.txt')).write_text(run.stdout, encoding='utf-8')
            (out / (label + '.stderr.txt')).write_text(run.stderr, encoding='utf-8')
            print(run.stdout[-24000:] + run.stderr[-5000:], flush=True)
            results[label] = {'exit': run.returncode, 'report_exists': (out / (label + '.json')).exists()}
    finally:
        source.write_bytes(original)
    results['original_restored'] = source.read_bytes() == original
    results['source_commit'] = REF
    results['candidate_origin'] = 'Zero reconstruction of public snippets, NOT the recipient private diff'
    results['success'] = all(results[x]['exit'] == 0 and results[x]['report_exists'] for x in ['base', 'candidate'])
    (out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print('SIGNAL_CONTRACT_SUMMARY ' + json.dumps(results), flush=True)
    return 0 if results['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
