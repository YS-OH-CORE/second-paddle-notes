"""Compare a single completion-order change on disposable public checkouts."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

REV = '6754ef387da97cf6cfbcd1bd5c216b533937b304'
BASE_BLOB = 'c096b665e9857f9df86a01c81be3093c786cc353'
CASES = ('normal', 'delayed', 'disconnect', 'loopback')
TESTS = ('tests/test_sse.py', 'tests/test_issue167.py', 'tests/test_event.py')


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def main(base: Path, candidate: Path, out: Path):
    base, candidate, out = base.resolve(), candidate.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=base, text=True).strip() == REV
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=base, text=True).strip()
    assert not candidate.exists()
    shutil.copytree(base, candidate)
    relative = 'sse_starlette/sse.py'
    original = (base/relative).read_bytes()
    assert blob(original) == BASE_BLOB
    old = '            self.active = False\n            await send({"type": "http.response.body", "body": b"", "more_body": False})'
    new = '            await send({"type": "http.response.body", "body": b"", "more_body": False})\n            self.active = False'
    text = original.decode('utf-8')
    assert text.count(old) == 1
    changed = text.replace(old, new)
    (candidate/relative).write_text(changed, encoding='utf-8')
    patch = ''.join(difflib.unified_diff(text.splitlines(True), changed.splitlines(True),
                                     fromfile='a/'+relative, tofile='b/'+relative))
    (out/'final-send.patch').write_text(patch, encoding='utf-8')
    summary = {'status': 'incomplete', 'upstream_revision': REV, 'baseline_blob': BASE_BLOB,
               'candidate_blob': blob(changed.encode()), 'cases': {}, 'upstream_tests': {},
               'scope': 'Synthetic ASGI scheduling and real localhost HTTP with instrumented receive/send; no MCP/client production incident claim.'}
    try:
        for label, root in [('baseline', base), ('candidate', candidate)]:
            env = {k: os.environ[k] for k in ('PATH','HOME','LANG','TMPDIR','SYSTEMROOT') if k in os.environ}
            env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1')
            rows = {}
            summary['cases'][label] = rows
            for case in CASES:
                target = out/f'{label}-{case}.json'
                run = subprocess.run([sys.executable, str(Path(__file__).with_name('probe.py')),
                                      case, str(target)], env=env, cwd=out,
                                     capture_output=True, text=True, timeout=15)
                (out/f'{label}-{case}.log').write_text(run.stdout+'\n'+run.stderr, encoding='utf-8')
                assert run.returncode == 0, f'{label}-{case}: probe did not finish; inspect log'
                row = json.loads(target.read_text())
                assert Path(row['source']) == root/relative
                assert row['source_blob'] == summary[f'{label}_blob']
                rows[case] = row
            xml = out/f'{label}-upstream.xml'
            result = subprocess.run([sys.executable, '-m', 'pytest', '-o', 'addopts=', '-q',
                                     *TESTS, '--junitxml='+str(xml)], env=env, cwd=root,
                                    capture_output=True, text=True, timeout=90)
            (out/f'{label}-upstream.log').write_text(result.stdout+'\n'+result.stderr, encoding='utf-8')
            assert xml.exists(), 'Original tests produced no report'
            cases = ET.parse(xml).getroot().findall('.//testcase')
            summary['upstream_tests'][label] = {
                'exit_code': result.returncode, 'tests': len(cases),
                'failures': [c.get('name') for c in cases if c.find('failure') is not None],
                'errors': [c.get('name') for c in cases if c.find('error') is not None],
                'skips': [c.get('name') for c in cases if c.find('skipped') is not None],
                'file_blobs': {name: blob((root/name).read_bytes()) for name in TESTS}}
        before, after = summary['cases']['baseline'], summary['cases']['candidate']
        assert before['normal']['final_completed'] and after['normal']['final_completed']
        assert before['delayed']['final_cancelled'] and not before['delayed']['final_completed']
        assert after['delayed']['final_completed'] and not after['delayed']['final_cancelled']
        for rows in (before, after):
            assert rows['disconnect']['final_cancelled'] and not rows['disconnect']['final_completed']
            assert rows['disconnect']['disconnect_callbacks'] == 1
            assert not rows['loopback']['app_exit_before_server_shutdown']
        assert not before['loopback']['complete_http'] and before['loopback']['error_type'] == 'RemoteProtocolError'
        assert after['loopback']['complete_http'] and after['loopback']['exact_payload']
        assert before['loopback']['final_cancelled'] and after['loopback']['final_completed']
        a, b = summary['upstream_tests']['baseline'], summary['upstream_tests']['candidate']
        assert a['exit_code'] == b['exit_code'] == 0 and a['tests'] == b['tests'] > 0
        assert a['file_blobs'] == b['file_blobs']
        assert not a['skips'] and not b['skips']
        assert (base/relative).read_bytes() == original
        assert (candidate/relative).read_text() == changed
        assert subprocess.check_output(['git','diff','--name-only'],cwd=candidate,text=True).splitlines() == [relative]
        summary['status'] = 'reproduced_and_candidate_passed_selected_controls'
    finally:
        write(out/'summary.json', summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.candidate, args.out)
