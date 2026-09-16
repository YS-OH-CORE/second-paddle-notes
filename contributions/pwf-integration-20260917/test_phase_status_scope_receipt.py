"""Regression tests for scoped status writes and committed-write reporting.

Runs the real canonical helper with its resolver sibling. Synthetic plans use
both the legacy root route and a pinned plan with a decoy active plan.
Prepared with Zero (ChatGPT) for Youngseok Oh. Offered under upstream MIT terms.
"""
from pathlib import Path
import os
import shutil
import subprocess
import pytest

ROOT = Path(os.environ.get('PWF_TEST_REPO_ROOT', Path(__file__).resolve().parents[1]))
SCRIPT = ROOT / 'skills/planning-with-files/scripts/phase-status.sh'
SH = shutil.which('sh')
ORDINARY = '# Task Plan\n## Phases\n### Phase 1: Build\n- **Status:** pending\n### Phase 2: Verify\n- **Status:** pending\n'
CASES = [
    ('valid_target_only', ORDINARY, '1', 'complete', True, ORDINARY.replace('- **Status:** pending', '- **Status:** complete', 1), False),
    ('phase_10_not_phase_1', '### Phase 1: One\n**Status:** pending\n### Phase 10: Ten\n**Status:** pending\n', '10', 'complete', True, '### Phase 1: One\n**Status:** pending\n### Phase 10: Ten\n**Status:** complete\n', False),
    ('missing_phase', ORDINARY, '3', 'complete', False, ORDINARY, False),
    ('missing_status_at_eof', '### Phase 1: Work\nNo status yet.\n', '1', 'complete', False, '### Phase 1: Work\nNo status yet.\n', False),
    ('missing_status_before_next_phase', '### Phase 1: Work\nNo status yet.\n### Phase 2: Review\n**Status:** pending\n', '1', 'complete', False, '### Phase 1: Work\nNo status yet.\n### Phase 2: Review\n**Status:** pending\n', False),
    ('invalid_status', ORDINARY, '1', 'done', False, ORDINARY, False),
    ('nested_h4_remains_in_phase', '### Phase 1: Work\n#### Tracking\n**Status:** pending\n', '1', 'complete', True, '### Phase 1: Work\n#### Tracking\n**Status:** complete\n', False),
    ('heading_text_inside_prose', '### Phase 1: Work\nThe title refers to # release.\n**Status:** pending\n', '1', 'complete', True, '### Phase 1: Work\nThe title refers to # release.\n**Status:** complete\n', False),
    ('failed_mv_is_not_committed', ORDINARY, '1', 'complete', False, ORDINARY, True),
]
for level in (1, 2, 3):
    text = '### Phase 1: Work\nNo status yet.\n\n' + '#' * level + ' Release tracking\n**Status:** pending\n'
    CASES.append((f'missing_status_before_h{level}', text, '1', 'complete', False, text, False))

@pytest.mark.skipif(SH is None or os.name == 'nt', reason='POSIX shell fault-injection suite')
@pytest.mark.parametrize('layout', ['legacy', 'pinned'])
@pytest.mark.parametrize('case', CASES, ids=[item[0] for item in CASES])
def test_scope_and_commit(tmp_path, layout, case):
    name, text, phase, status, success, expected, fail_mv = case
    env = {k: v for k, v in os.environ.items() if not k.startswith('PWF_') and k not in ('PLAN_ID', 'PYTHON_BIN')}
    env.update(HOME=str(tmp_path), PWD=str(tmp_path), LC_ALL='C')
    target = tmp_path
    untouched = []
    if layout == 'pinned':
        target = tmp_path / '.planning' / 'alpha'
        target.mkdir(parents=True)
        beta = tmp_path / '.planning' / 'beta'
        beta.mkdir()
        for other in (tmp_path / 'task_plan.md', beta / 'task_plan.md'):
            other.write_bytes(ORDINARY.encode())
            untouched.append(other)
        (tmp_path / '.planning' / '.active_plan').write_bytes(b'beta\n')
        env['PLAN_ID'] = 'alpha'
    plan = target / 'task_plan.md'
    plan.write_bytes(text.encode())
    if fail_mv:
        fault = tmp_path / 'fault-bin'
        fault.mkdir()
        fake = fault / 'mv'
        fake.write_bytes(b'#!/bin/sh\nprintf "injected mv failure\\n" >&2\nexit 73\n')
        fake.chmod(0o755)
        env['PATH'] = str(fault) + os.pathsep + env.get('PATH', '/usr/bin:/bin')
    result = subprocess.run([SH, str(SCRIPT), phase, status], cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=20)
    assert (result.returncode == 0) == success, (name, result.returncode, result.stdout, result.stderr)
    assert plan.read_bytes() == expected.encode(), (name, plan.read_text())
    assert success or ' -> ' not in result.stdout, result.stdout
    assert not list(target.glob('task_plan.md.tmp.*'))
    assert not (target / '.pwf-locks' / 'phase-status.lock').exists()
    for other in untouched:
        assert other.read_bytes() == ORDINARY.encode(), str(other)
