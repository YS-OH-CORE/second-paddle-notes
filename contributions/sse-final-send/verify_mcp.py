"""Run the unchanged prior patch through fresh/restarted real MCP HTTP servers.

A completed comparison is not a claim that the candidate repairs every scenario.
Actual per-request successes and failures remain in the returned evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REV = '6754ef387da97cf6cfbcd1bd5c216b533937b304'
SOURCE = 'sse_starlette/sse.py'
BLOBS = {'baseline': 'c096b665e9857f9df86a01c81be3093c786cc353',
         'candidate': 'f483035db645995f76168e66378ec1f42864beb7'}
MODES = ['fresh', 'restart', 'restart_reset']


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def main(base, candidate, out):
    base, candidate, out = base.resolve(), candidate.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'incomplete', 'sse_revision': REV, 'observations': {},
              'scope': 'MCP 2.2.0 initialize over actual loopback Uvicorn/h11 HTTP; final send delayed, real receives unchanged. Not CPU-load frequencies.',
              'attribution': 'Original issue: jonpspri; restart/watcher mechanism and reset control: skulitom in MCP #3494. This extends the previously published final-send candidate into actual MCP and crossed restart controls.'}
    try:
        assert git(base, 'rev-parse', 'HEAD') == REV
        assert not git(base, 'status', '--porcelain') and not candidate.exists()
        fixture = Path(__file__).with_name('final-send.patch')
        assert blob(fixture.read_bytes()) == '113709cfa3e7ca147f064ec716411cae1ee0f0cc'
        shutil.copytree(base, candidate)
        subprocess.run(['git', 'apply', '--check', str(fixture)], cwd=candidate, check=True)
        subprocess.run(['git', 'apply', str(fixture)], cwd=candidate, check=True)
        assert git(candidate, 'diff', '--name-only').splitlines() == [SOURCE]
        for label, root in [('baseline', base), ('candidate', candidate)]:
            assert blob((root/SOURCE).read_bytes()) == BLOBS[label]
            rows = report['observations'][label] = {}
            env = {key: os.environ[key] for key in ['PATH', 'HOME', 'LANG', 'TMPDIR'] if key in os.environ}
            env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1')
            for mode in MODES:
                target = out/f'{label}-{mode}.json'
                run = subprocess.run([sys.executable, str(Path(__file__).with_name('mcp_probe.py')),
                                      mode, str(target)], env=env, cwd=out,
                                     capture_output=True, text=True, timeout=30)
                (out/f'{label}-{mode}.log').write_text(run.stdout+'\n'+run.stderr, encoding='utf-8')
                if target.exists():
                    rows[mode] = json.loads(target.read_text())
                assert run.returncode == 0, f'{label}-{mode}: probe/setup incomplete; inspect log'
                row = rows[mode]
                assert row['status'] == 'observed' and row['packages']['mcp'] == '2.2.0'
                assert Path(row['sse_source']) == root/SOURCE and row['sse_source_blob'] == BLOBS[label]
            assert blob((root/SOURCE).read_bytes()) == BLOBS[label]
        pids = [row['pid'] for rows in report['observations'].values() for row in rows.values()]
        assert len(set(pids)) == len(pids) == 6
        report['outcomes'] = {label: {mode: [bool(a.get('initialize_succeeded')) for a in row['attempts']]
                                    for mode, row in rows.items()}
                              for label, rows in report['observations'].items()}
        report['all_initializations_succeeded'] = all(ok for modes in report['outcomes'].values()
                                                      for outcomes in modes.values() for ok in outcomes)
        report['candidate_fixed_restart'] = (
            not report['outcomes']['baseline']['restart'][-1]
            and report['outcomes']['candidate']['restart'][-1])
        report['candidate_and_baseline_same_outcomes'] = report['outcomes']['baseline'] == report['outcomes']['candidate']
        assert not git(base, 'status', '--porcelain')
        assert git(candidate, 'diff', '--name-only').splitlines() == [SOURCE]
        report['status'] = 'comparison_complete'
    finally:
        (out/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['base', 'candidate', 'out']:
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    main(args.base, args.candidate, args.out)
