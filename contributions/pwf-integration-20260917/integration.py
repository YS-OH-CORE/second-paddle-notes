"""Pinned upstream integration check; no remote repository writes or model calls.

The job uses a disposable checkout, never user plans. Existing tests are not
modified or skipped. Two exact source edits are made only after baseline runs.
Prepared with Zero (ChatGPT) for Youngseok Oh; MIT contribution terms.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

PIN = '746f57a7c51797bee512edd3e0ded277916f8cb3'
BLOB = 'c06fe48b93ffbd7d72f23bea706a5919ec8efeb6'
CANDIDATE_SHA256 = 'c9dbcc2edb162091ab3804ea6c12303fceaa5944c71b8e167d1f0e398c5f842b'
CANONICAL = 'skills/planning-with-files/scripts/phase-status.sh'
HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[1]).resolve(strict=True)
SUITE = sys.argv[2]
OUT = Path(sys.argv[3]).resolve()
OUT.mkdir(parents=True, exist_ok=False)
RECEIPT = {'upstream': PIN, 'suite': SUITE, 'calls': [], 'status': 'incomplete'}


def run(label, args, cwd=ROOT, timeout=720, **kwargs):
    started = time.monotonic()
    with (OUT / (label + '.log')).open('w', encoding='utf-8') as stream:
        try:
            proc = subprocess.run(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                  text=True, timeout=timeout, **kwargs)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = 124
            stream.write('\nHARNESS_TIMEOUT\n')
    data = (OUT / (label + '.log')).read_bytes()
    item = {'label': label, 'argv': args, 'exit': rc, 'seconds': round(time.monotonic()-started, 3),
            'log_sha256': hashlib.sha256(data).hexdigest(), 'log_bytes': len(data)}
    RECEIPT['calls'].append(item)
    print('COMMAND_RESULT ' + json.dumps(item), flush=True)
    print(data.decode('utf-8', errors='replace')[-9000:], flush=True)
    return rc


def junit(label):
    path = OUT / (label + '.xml')
    tree = ET.parse(path)
    entries = []
    for case in tree.iter('testcase'):
        state = 'passed'
        detail = ''
        for tag in ('failure', 'error', 'skipped'):
            child = case.find(tag)
            if child is not None:
                state = tag
                detail = (child.get('message', '') + '\n' + (child.text or ''))[:5000]
                break
        entry = {'name': case.get('classname', '') + '::' + case.get('name', ''), 'status': state}
        if detail:
            entry['detail'] = detail
        entries.append(entry)
    counts = {s: sum(e['status'] == s for e in entries) for s in ('passed', 'failure', 'error', 'skipped')}
    result = {'tests': len(entries), 'counts': counts, 'nonpassing': [e for e in entries if e['status'] != 'passed'],
              'xml_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    RECEIPT[label] = result
    (OUT / (label + '.json')).write_text(json.dumps(entries, indent=2))
    print('JUNIT_RESULT ' + label + ' ' + json.dumps(result), flush=True)
    return entries


def apply_candidate():
    raw = (ROOT / CANONICAL).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob != BLOB:
        raise RuntimeError('canonical source identity mismatch')
    text = raw.decode()
    old = '            } else if (in_block == 1 && done == 0 && line ~ /\\*\\*Status:\\*\\*/) {'
    new = ('            } else if (line ~ /^#(#(#)?)?([ \\t]|$)/) {\n'
           '                # A same-level or parent heading ends this phase. A missing\n'
           '                # phase status must not borrow one from an unrelated section.\n'
           '                in_block = 0\n' + old)
    if text.count(old) != 1:
        raise RuntimeError('heading hunk ambiguous')
    text = text.replace(old, new)
    old_mv = '    mv -f "${TMP_FILE}" "${PLAN_FILE}"\n    return 0\n'
    new_mv = ('    if ! mv -f "${TMP_FILE}" "${PLAN_FILE}"; then\n'
              '        printf "[phase-status] Could not replace %s; phase update was not committed.\\n" "${PLAN_FILE}" >&2\n'
              '        return 1\n'
              '    fi\n    return 0\n')
    if text.count(old_mv) != 1:
        raise RuntimeError('replacement hunk ambiguous')
    candidate = text.replace(old_mv, new_mv).encode()
    if hashlib.sha256(candidate).hexdigest() != CANDIDATE_SHA256:
        raise RuntimeError('candidate differs from previously delivered bytes')
    (ROOT / CANONICAL).write_bytes(candidate)
    if run('synchronize', [sys.executable, 'scripts/sync-ide-folders.py']) != 0:
        raise RuntimeError('upstream synchronization failed')
    # The root phase writer is not included in the official sync manifest.
    root_writer = ROOT / 'scripts/phase-status.sh'
    if root_writer.read_bytes() != raw:
        raise RuntimeError('root writer differs before explicit synchronization')
    root_writer.write_bytes(candidate)
    if run('verify-synchronization', [sys.executable, 'scripts/sync-ide-folders.py', '--verify']) != 0:
        raise RuntimeError('upstream synchronization verification failed')
    changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True).splitlines()
    if not changed or any(not path.endswith('/phase-status.sh') for path in changed):
        raise RuntimeError('unexpected tracked-file change: ' + repr(changed))
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [p for p in tracked if p.endswith('/phase-status.sh')]
    identities = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    if any(v != CANDIDATE_SHA256 for v in identities.values()):
        raise RuntimeError('unpatched or divergent tracked mirror: ' + repr(identities))
    RECEIPT['changed_scripts'] = changed
    RECEIPT['all_tracked_phase_writers'] = identities
    RECEIPT['candidate_sha256'] = CANDIDATE_SHA256
    patch = subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)
    (OUT / 'integrated-scripts.patch').write_bytes(patch)
    RECEIPT['scripts_patch_sha256'] = hashlib.sha256(patch).hexdigest()
    print('MIRROR_RESULT ' + json.dumps(identities), flush=True)


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head != PIN:
        raise RuntimeError('upstream commit mismatch')
    if subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT).strip():
        raise RuntimeError('baseline checkout is already modified')
    RECEIPT['python'] = sys.version
    if SUITE == 'python':
        rc = run('baseline', [sys.executable, '-m', 'pytest', 'tests/', '-q', '--durations=10', '--junitxml=' + str(OUT/'baseline.xml')])
        baseline = junit('baseline')
        env = dict(os.environ, PWF_TEST_REPO_ROOT=str(ROOT))
        regression_rc = run('baseline-regression', [sys.executable, '-m', 'pytest', str(HERE/'test_phase_status_scope_receipt.py'), '-q', '--junitxml=' + str(OUT/'baseline-regression.xml')], env=env)
        old = junit('baseline-regression')
        expected_failed = {f'test_phase_status_scope_receipt::test_scope_and_commit[{name}-{layout}]'
                           for name in ('failed_mv_is_not_committed', 'missing_status_before_h1', 'missing_status_before_h2', 'missing_status_before_h3')
                           for layout in ('legacy', 'pinned')}
        actual_failed = {e['name'] for e in old if e['status'] == 'failure'}
        # Classname prefixes differ between pytest root directories; compare suffixes.
        norm = lambda x: x.split('::')[-1]
        if len(old) != 24 or {norm(x) for x in expected_failed} != {norm(x) for x in actual_failed} or regression_rc != 1:
            raise RuntimeError('baseline regression did not reproduce the predeclared eight failures')
        apply_candidate()
        dst = ROOT/'tests/test_phase_status_scope_receipt.py'
        if dst.exists():
            raise RuntimeError('new regression filename already exists')
        shutil.copyfile(HERE/'test_phase_status_scope_receipt.py', dst)
        candidate_rc = run('candidate', [sys.executable, '-m', 'pytest', 'tests/', '-q', '--durations=10', '--junitxml=' + str(OUT/'candidate.xml')])
        final = junit('candidate')
        old_map = {e['name']: e['status'] for e in baseline}
        new_map = {e['name']: e['status'] for e in final}
        new_cases = [e for e in final if e['name'] not in old_map]
        RECEIPT['comparison'] = {'existing_tests_preserved': all(new_map.get(k) == v for k,v in old_map.items()),
                                 'added_cases': len(new_cases), 'all_added_passed': all(e['status']=='passed' for e in new_cases)}
        # Export only the reviewed modifications plus the new regression file.
        subprocess.run(['git', 'add', '-N', 'tests/test_phase_status_scope_receipt.py'], cwd=ROOT, check=True)
        patch = subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)
        (OUT/'integration-with-tests.patch').write_bytes(patch)
        RECEIPT['integration_patch_sha256'] = hashlib.sha256(patch).hexdigest()
        print('PATCH_BEGIN\n' + patch.decode() + '\nPATCH_END', flush=True)
        passed = rc == 0 and candidate_rc == 0 and RECEIPT['comparison']['existing_tests_preserved'] and len(new_cases)==24 and all(e['status']=='passed' for e in new_cases)
    else:
        dirs = {'pi': '.pi/skills/planning-with-files/extensions/planning-with-files',
                'opencode': '.opencode/packages/opencode-planning-with-files'}
        cwd = ROOT / dirs[SUITE]
        if run('npm-install', ['npm', 'ci', '--no-audit', '--no-fund'], cwd=cwd, timeout=300) != 0:
            raise RuntimeError('locked dependency install failed')
        build0 = run('baseline-build', ['npm', 'run', 'build'], cwd=cwd, timeout=180) if SUITE=='opencode' else 0
        rc = run('baseline-node', ['npm', 'test'], cwd=cwd, timeout=300)
        apply_candidate()
        build1 = run('candidate-build', ['npm', 'run', 'build'], cwd=cwd, timeout=180) if SUITE=='opencode' else 0
        candidate_rc = run('candidate-node', ['npm', 'test'], cwd=cwd, timeout=300)
        passed = all(c == 0 for c in (build0, build1, rc, candidate_rc))
    RECEIPT['status'] = 'passed' if passed else 'failed'
    return 0 if passed else 1

if __name__ == '__main__':
    result = 2
    try:
        result = main()
    except Exception as exc:
        RECEIPT['status'] = 'harness-or-integration-error'
        RECEIPT['error'] = repr(exc)
        print('HARNESS_ERROR ' + repr(exc), flush=True)
    finally:
        (OUT/'RECEIPT.json').write_text(json.dumps(RECEIPT, indent=2))
        print('PWF_RECEIPT_JSON ' + json.dumps(RECEIPT, separators=(',', ':')), flush=True)
    raise SystemExit(result)
