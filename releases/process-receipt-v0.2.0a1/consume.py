#!/usr/bin/env python3
"""Read the public alpha without auth, install that exact wheel, use its real CLI.

Native Windows/Linux disposable-runner check; no user's computer is changed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import venv
from publish import REPO, TAG, SOURCE, WHEEL, WHEEL_SHA, MODULES, NAMES, sha, require, dump, wheel_modules

BASE = f'https://github.com/{REPO}/releases/download/{TAG}/'
TEXT = '공개 배포 확인\n  들여쓰기와 공백 유지  \n'


def public_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'process-receipt-alpha-consumer/0.2',
        'Accept': 'application/octet-stream' if '/download/' in url else 'application/vnd.github+json'})
    # No cookie jar, GitHub CLI, token lookup, or Authorization header.
    with urllib.request.urlopen(request, timeout=30) as response:
        require(response.status == 200 and response.url.startswith('https://'), 'Unexpected public download response')
        result = response.read(1_000_001)
    require(len(result) <= 1_000_000, 'Public response too large')
    return result


def consume(out: Path) -> None:
    require(os.name in ('posix', 'nt'), 'Untested platform')
    out.mkdir(parents=True, exist_ok=False)
    release = json.loads(public_get(f'https://api.github.com/repos/{REPO}/releases/tags/{TAG}'))
    require(not release['draft'] and release['prerelease'] and release['target_commitish'] == SOURCE,
            'Not the pinned public experimental release')
    require({a['name'] for a in release['assets']} == NAMES and len(release['assets']) == 3, 'Unexpected public assets')
    data = public_get(BASE+WHEEL)
    modules = wheel_modules(data)
    wheel = out/WHEEL
    wheel.write_bytes(data)
    provenance_bytes = public_get(BASE+'BUILD_PROVENANCE.json')
    provenance = json.loads(provenance_bytes)
    require(provenance['source_commit'] == SOURCE and provenance['wheel_sha256'] == WHEEL_SHA,
            'Public provenance mismatch')
    checksums = public_get(BASE+'SHA256SUMS').decode()
    expected_sums = ''.join(f'{sha(value)}  {name}\n' for name, value in
                            ((WHEEL, data), ('BUILD_PROVENANCE.json', provenance_bytes)))
    require(checksums == expected_sums, 'Public checksum bytes mismatch')
    (out/'BUILD_PROVENANCE.json').write_bytes(provenance_bytes)
    work = out/'outside-source'; work.mkdir()
    # Explicit allowlist: no model/API/workflow/account credentials reach pip or child processes.
    allowed = ('PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR', 'PATHEXT')
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    home = out/'home'; home.mkdir()
    env.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING='utf-8',
               PIP_CONFIG_FILE=os.devnull, PIP_NO_INPUT='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    environment = out/'consumer'
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    binary = environment/('Scripts' if os.name == 'nt' else 'bin')
    py = binary/('python.exe' if os.name == 'nt' else 'python')
    cli = binary/('process-receipt.exe' if os.name == 'nt' else 'process-receipt')
    transcript = []

    def run(args, expected=0):
        p = subprocess.run([str(a) for a in args], cwd=work, env=env,
                           capture_output=True, timeout=40, check=False)
        transcript.append({'exit_code': p.returncode, 'stdout': p.stdout.decode('utf-8', 'replace'),
                           'stderr': p.stderr.decode('utf-8', 'replace')})
        dump(out/'consumer-commands.json', transcript)
        require(p.returncode == expected, f'Consumer operation {len(transcript)} failed; see consumer-commands.json')
        return p.stdout.decode('utf-8')

    run([py, '-I', '-m', 'pip', '--isolated', 'install', '--no-index', '--no-deps', '--no-cache-dir', wheel])
    identity = json.loads(run([py, '-I', '-c',
        'import process_receipt,process_receipt_cli,process_receipt_windows,importlib.metadata as m,json,sys; '
        'print(json.dumps({"version":m.version("second-paddle-process-receipt"),'
        '"modules":{p.__name__+".py":p.__file__ for p in [process_receipt,process_receipt_cli,process_receipt_windows]},'
        '"base_executable":sys._base_executable,"python":sys.version}))']))
    require(identity['version'] == '0.2.0a1', 'Wrong installed version')
    for name, path in identity['modules'].items():
        path = Path(path).resolve()
        require(path.is_relative_to(environment) and path.read_bytes() == modules[name], 'Import not from exact fresh installation')
    require('--receipt' in run([cli, '--help']), 'CLI help failed')
    worker = Path(identity['base_executable']).resolve(strict=True)
    # Use the real base EXE, not a Windows venv launcher with out-of-scope descendants.
    output = work/'공개 결과 with spaces.txt'
    receipt = work/'normal.json'
    code = f'from pathlib import Path; Path({str(output)!r}).write_bytes({TEXT.encode()!r})'
    run([cli, '--receipt', receipt, '--timeout', '10', '--', worker, '-I', '-c', code])
    r = json.loads(receipt.read_bytes())
    require(output.read_bytes() == TEXT.encode() and r['status'] == 'completed'
            and r['child_exit_code'] == 0 and r['direct_child_exit_observed'], 'Actual public-wheel job failed')
    original_receipt = receipt.read_bytes()
    sentinel = work/'must-not-run'
    run([cli, '--receipt', receipt, '--', worker, '-I', '-c',
         f'from pathlib import Path; Path({str(sentinel)!r}).touch()'], expected=2)
    require(receipt.read_bytes() == original_receipt and not sentinel.exists(), 'Existing receipt not preserved')
    running = work/'running'; running.mkdir()
    ready, stop, beat, done = [running/name for name in ('READY', 'STOP', 'heartbeat.txt', 'DONE')]
    stopped = running/'receipt.json'
    worker_code = (
        'from pathlib import Path\nimport time\n'
        f'folder=Path({str(running)!r})\n'
        'with (folder/"heartbeat.txt").open("x") as f:\n'
        '    (folder/"READY").touch()\n'
        '    for i in range(160):\n'
        '        f.write(str(i)+"\\n"); f.flush(); time.sleep(0.05)\n'
        '(folder/"DONE").touch()\n')
    proc = subprocess.Popen([str(cli), '--receipt', str(stopped), '--stop-file', str(stop),
        '--timeout', '10', '--', str(worker), '-I', '-c', worker_code],
        cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        until = time.monotonic()+10
        while not ready.exists() and proc.poll() is None and time.monotonic() < until:
            time.sleep(0.01)
        require(ready.exists() and proc.poll() is None, 'Worker not observed running')
        time.sleep(0.12)
        stop.touch(exist_ok=False)
        stdout, stderr = proc.communicate(timeout=8)
        require(proc.returncode == 130, 'Public-wheel stop did not return observed-stop category')
        stopped_record = json.loads(stopped.read_bytes())
        before = beat.read_bytes(); time.sleep(0.1)
        require(before and before == beat.read_bytes() and not done.exists()
                and stopped_record['direct_child_exit_observed'], 'Missing actual stopped-workload evidence')
        expected_status = 'finished_after_stop_request' if os.name == 'nt' else 'interrupted'
        require(stopped_record['status'] == expected_status, 'Wrong platform stop classification')
        (out/'stop-cli.txt').write_bytes(stdout+b'\n'+stderr)
    finally:
        if proc.poll() is None:
            if not stop.exists():
                stop.touch()
            try:
                proc.communicate(timeout=12)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.communicate(timeout=3)
    dump(out/'consumer-verification.json', dict(status='public_download_install_and_use_verified',
        observed_at=datetime.now(timezone.utc).isoformat(), platform=sys.platform,
        release_id=release['id'], release_url=release['html_url'], wheel_url=BASE+WHEEL,
        wheel_sha256=sha(data), wheel_bytes=len(data), installed=identity,
        used_authorization_header=False, source_fallback=False,
        unicode_output_bytes_match=True, existing_receipt_preserved=True,
        actual_stop=stopped_record, heartbeat_count=len(before.splitlines()),
        natural_completion_file=False, heartbeat_unchanged_after_exit=True,
        limits='Author-run public consumer path; directly launched base Python, no descendant/rollback guarantee, no model calls.'))
    print('Exact public alpha downloaded without auth, installed, used and stopped on '+sys.platform)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    consume(parser.parse_args().out.resolve())
