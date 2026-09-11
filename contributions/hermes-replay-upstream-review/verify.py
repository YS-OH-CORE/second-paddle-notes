#!/usr/bin/env python3
"""Assess another contributor's exact replay patch, without applying ours.

The original broad test set is retained, including its two valid-JSON non-object
expectations. A completed assessment is NOT a claim that all tests passed.
Only disposable public source checkouts and synthetic temporary databases.
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
import xml.etree.ElementTree as ET

BASE = '3b044261b6afe97277d48e7e75c65ce34e76e8a2'
HEAD = '59048b3a0335216b7983072bb1d006a179ca57ae'
MODULE = 'agent/replay_cleanup.py'
TEST = 'tests/agent/test_replay_cleanup_structured_results.py'
DB_TEST = 'tests/agent/test_replay_cleanup_sessiondb_roundtrip.py'
EXISTING = 'tests/agent/test_replay_cleanup.py'
FIXTURE_BLOBS = {
    'replay_cleanup.patch': '2239377525e4d5fc4c060019b5a5a5fe376f8e50',
    'test_replay_cleanup_sessiondb_roundtrip.py': '4a4ff387be6a14d1423e5ef149f5f92f003354e7',
}
BOUNDARY_CASES = {
    'test_structured_interrupt_classification[json_list_is_data]',
    'test_structured_interrupt_classification[json_string_is_data]',
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def run_suite(root, output, label, test, env):
    xml = output/(label+'.xml')
    env = dict(env, REPLAY_ROUNDTRIP_EVIDENCE=str(output/(label+'.observations.jsonl')))
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '-o', 'addopts=', '-q', test, '--junitxml='+str(xml)],
        cwd=root, env=env, capture_output=True, text=True, timeout=120,
    )
    (output/(label+'.txt')).write_text(proc.stdout+'\n'+proc.stderr, encoding='utf-8')
    require(xml.exists(), label+': no pytest report; inspect output')
    cases = ET.parse(xml).getroot().findall('.//testcase')
    failed = [c for c in cases if c.find('failure') is not None]
    report = {
        'exit_code': proc.returncode, 'tests': len(cases), 'failures': len(failed),
        'errors': sum(c.find('error') is not None for c in cases),
        'skipped': sum(c.find('skipped') is not None for c in cases),
        'failed_cases': [c.attrib['name'] for c in failed],
        'failure_details': [{'name': c.attrib['name'], 'message': c.find('failure').get('message'),
                             'text': c.find('failure').text} for c in failed],
    }
    (output/(label+'.json')).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(label, json.dumps({k:v for k,v in report.items() if k != 'failure_details'}), flush=True)
    require(not report['errors'] and not report['skipped'], label+': setup error or skip is not a behavior result')
    return report


def main(base, head, out):
    base, head, out = base.resolve(), head.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture_dir = Path(__file__).resolve().parent.parent/'hermes-replay-status'
    for name, expected in FIXTURE_BLOBS.items():
        data = (fixture_dir/name).read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        require(blob == expected, 'Existing fixture changed: '+name)
    reports, identities = {}, {}
    for label, root, revision in [('base', base, BASE), ('head', head, HEAD)]:
        require(git(root, 'rev-parse', 'HEAD') == revision, 'Wrong source revision: '+label)
        require(not git(root, 'status', '--porcelain'), 'Use a clean disposable checkout: '+label)
        require(not (root/TEST).exists() and not (root/DB_TEST).exists(), 'Supplemental tests already present')
        original = {name: sha((root/name).read_bytes()) for name in (MODULE, EXISTING)}
        # Apply ONLY the new test-file hunk, NEVER our production-code patch.
        subprocess.run(['git', 'apply', '--check', '--include='+TEST, str(fixture_dir/'replay_cleanup.patch')], cwd=root, check=True)
        subprocess.run(['git', 'apply', '--include='+TEST, str(fixture_dir/'replay_cleanup.patch')], cwd=root, check=True)
        shutil.copyfile(fixture_dir/Path(DB_TEST).name, root/DB_TEST)
        require(not git(root, 'diff', '--name-only'), 'Unexpected tracked source modification')
        home = out/(label+'-home')
        home.mkdir()
        env = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT', 'TMPDIR', 'TEMP', 'TMP') if k in os.environ}
        env.update(HOME=str(home), HERMES_HOME=str(home/'hermes'), PYTHONPATH=str(root),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TZ='UTC', LANG='C.UTF-8')
        reports[label+'-broad'] = run_suite(root, out, label+'-broad', TEST, env)
        reports[label+'-db'] = run_suite(root, out, label+'-db', DB_TEST, env)
        if label == 'head':
            reports['author-tests'] = run_suite(root, out, 'author-tests', EXISTING, env)
        loaded = json.loads(subprocess.check_output([
            sys.executable, '-c', 'import json,agent.replay_cleanup as r,agent.tool_dispatch_helpers as t,hermes_state as h; '
            'print(json.dumps({"replay":r.__file__,"builder":t.__file__,"state":h.__file__}))'],
            cwd=root, env=env, text=True, timeout=25))
        for name, path in [('replay', MODULE), ('builder', 'agent/tool_dispatch_helpers.py'), ('state', 'hermes_state.py')]:
            require(Path(loaded[name]).resolve() == root/path, 'Wrong import: '+name)
        require(not git(root, 'diff', '--name-only'), 'Tracked source changed during assessment')
        require(original == {name: sha((root/name).read_bytes()) for name in original}, 'Original module/test changed')
        identities[label] = {
            'revision': revision, 'module_and_author_test_sha256': original,
            'replay_git_blob': git(root, 'rev-parse', 'HEAD:'+MODULE),
            'supplemental_test_sha256': sha((root/TEST).read_bytes()),
            'database_test_sha256': sha((root/DB_TEST).read_bytes()),
            'imports': loaded, 'tracked_source_unchanged': True,
        }
    # Preserve the actual red tests instead of excluding, xfail-ing, or editing them.
    require(reports['base-broad']['tests'] == reports['head-broad']['tests'] == 27, 'Unexpected broad case count')
    require(reports['base-broad']['exit_code'] == 1 and reports['base-broad']['failures'] > 2, 'No baseline defect reproduced')
    require(reports['head-broad']['exit_code'] == 1 and set(reports['head-broad']['failed_cases']) == BOUNDARY_CASES,
            'Candidate differs from the inspected object-only boundary; inspect red report')
    require(reports['base-db']['tests'] == reports['head-db']['tests'] == 8, 'Unexpected DB case count')
    require(reports['base-db']['exit_code'] == 1 and reports['base-db']['failures'] > 0, 'No DB replay defect reproduced')
    require(reports['head-db']['exit_code'] == 0 and not reports['head-db']['failures'], 'Candidate DB object cases failed')
    require(reports['author-tests']['exit_code'] == 0 and reports['author-tests']['tests'] > 0, 'Author tests failed')
    for label in ('base', 'head'):
        rows = [json.loads(x) for x in (out/(label+'-db.observations.jsonl')).read_text().splitlines()]
        require(len(rows) == 8, 'Missing actual DB observations')
        require(all(r['writer_pid'] != r['reader_pid'] and r['persisted_tool_text_equal']
                    and r['latest_user_preserved'] and r['stored_history_unchanged'] and r['input_unchanged'] for r in rows),
                'Persistence provenance mismatch')
    summary = {
        'status': 'assessment_complete_with_documented_boundary_failures',
        'all_supplied_supplemental_tests_pass': False,
        'declared_object_scope_cases_pass': True,
        'candidate': 'NousResearch/hermes-agent#107809', 'source_identities': identities,
        'reports': reports, 'reused_fixtures': FIXTURE_BLOBS,
        'known_boundary_failures': sorted(BOUNDARY_CASES),
        'boundary': 'Valid JSON arrays and strings still enter the explicitly retained legacy heuristic. These failures are not hidden and are not represented as regressions newly introduced by this candidate.',
        'scope': 'Real module/message-builder imports and separate-process synthetic SessionDB roundtrips; no production patch of ours is applied. No live gateway, model/provider call, private history, or independent institutional certification.',
        'model_calls': 0, 'production_modules_modified': False,
    }
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('reports','source_identities')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--head', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.head, args.out)
