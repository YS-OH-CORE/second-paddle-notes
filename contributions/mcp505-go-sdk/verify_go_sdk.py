#!/usr/bin/env python3
"""Check MCP #505 using the separately maintained Go SDK and upstream CLI.

Only run on fresh disposable checkouts at the pins below. The Go library and
transport are never changed. Negative controls alter one diagnostic handler in
that checkout, preserving each variant and restoring the original in finally.
No credential, real model, external application or independent-review claim.
"""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

CONF_PIN = '7169291ec0b68eb370fddcd9947313ab0d5e4156'
GO_PIN = 'fbd36cb7870176bfc3e8e423df697cf110d0f927'
GO_FILE = Path('conformance/everything-server/main.go')
GO_BLOB = 'c532d438f0575e7eefbbe0b8f22a07874cdab239'
PATCH_HASH = '6b54c4129d72691775a01c911515dee4bc59036262a957e3f9bf61c0bac7faa9'
TARGET = 'input-required-result-request-state'
MARKER = 'state-ok: requestState received and confirmation accepted'
MODES = ('original', 'missing-marker', 'tool-error', 'tool-error-with-marker')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def make_variant(original: str, mode: str) -> str:
    if mode not in MODES:
        raise ValueError('Unknown diagnostic mode')
    if mode == 'original':
        return original
    start = original.index('func testInputRequiredRequestStateHandler(')
    end = original.index('\nfunc ', start + 5)
    section = original[start:end]
    if section.count(MARKER) != 1 or section.count('return &mcp.CallToolResult{') != 2:
        raise ValueError('Pinned handler shape is not the expected one')
    if mode in ('missing-marker', 'tool-error'):
        section = section.replace(MARKER, 'requestState received; diagnostic marker omitted', 1)
    if mode in ('tool-error', 'tool-error-with-marker'):
        section = section.replace('return &mcp.CallToolResult{',
            'return &mcp.CallToolResult{\n\t\t\t\tIsError: true,', 1)
    return original[:start] + section + original[end:]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--conformance', required=True, type=Path)
    ap.add_argument('--go-sdk', required=True, type=Path)
    ap.add_argument('--patch', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    conf, sdk, patch, out = (p.resolve() for p in
        (args.conformance, args.go_sdk, args.patch, args.out))
    if conf == sdk or out in (conf, sdk) or not (conf/'.git').exists() or not (sdk/'.git').exists():
        raise ValueError('Separate disposable repository checkouts are required')
    out.mkdir(parents=True, exist_ok=False)
    runtime = out.parent / (out.name + '-runtime')
    runtime.mkdir(exist_ok=False)
    record = {'status': 'incomplete', 'conformance_commit': CONF_PIN, 'go_sdk_commit': GO_PIN,
              'commands': [], 'cases': [], 'negative_controls': 'synthetically altered diagnostic handler only'}
    original = None

    def save() -> None:
        (out/'verification.json').write_text(json.dumps(record, indent=2)+'\n')

    def run(argv, cwd, name, timeout=240, allowed=(0,)):
        cp = subprocess.run([str(x) for x in argv], cwd=cwd,
            env={**os.environ, 'CI': 'true', 'LEFTHOOK': '0', 'GOTOOLCHAIN': 'local'},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        (out/(name+'.log')).write_text(cp.stdout)
        record['commands'].append({'argv': list(map(str, argv)), 'cwd': str(cwd),
                                  'returncode': cp.returncode, 'log': name+'.log'})
        save()
        if cp.returncode not in allowed:
            raise RuntimeError(name+' failed: '+str(cp.returncode))
        return cp

    def stop(proc, log):
        if proc.poll() is None:
            # Only this verifier's child process group is stopped.
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        log.close()

    def launch(binary, label):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        log = (out/(label+'-server.log')).open('w')
        proc = subprocess.Popen([str(binary), '-http=127.0.0.1:'+str(port), '-stateless=true'],
            cwd=sdk, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            for _ in range(150):
                if proc.poll() is not None:
                    raise RuntimeError(label+' exited before listening')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                        return proc, log, port
                except OSError:
                    time.sleep(0.2)
            raise TimeoutError(label+' did not start')
        except BaseException:
            stop(proc, log)
            raise

    def cli(stage, mode, binary, scenario=TARGET):
        label = stage+'-'+mode+'-'+scenario
        proc, log, port = launch(binary, label)
        try:
            result_dir = out/(label+'-results')
            cp = run(['node', 'dist/index.js', 'server', '--url', f'http://127.0.0.1:{port}',
                '--scenario', scenario, '--spec-version', '2026-07-28', '-o', result_dir],
                conf, label, timeout=90, allowed=(0, 1))
            checks = []
            def visit(obj):
                if isinstance(obj, dict):
                    if 'id' in obj and 'status' in obj:
                        checks.append(obj)
                    for v in obj.values():
                        visit(v)
                elif isinstance(obj, list):
                    for v in obj:
                        visit(v)
            for item in sorted(result_dir.rglob('checks.json')):
                visit(json.loads(item.read_text()))
            expected = 'FAILURE' if stage == 'candidate' and mode != 'original' else 'SUCCESS'
            entry = {'stage': stage, 'mode': mode, 'scenario': scenario, 'returncode': cp.returncode,
                     'checks': [{'id': c['id'], 'status': c['status'],
                                'errorMessage': c.get('errorMessage')} for c in checks]}
            record['cases'].append(entry)
            save()
            if not checks:
                raise RuntimeError(label+': no checks emitted')
            if scenario == TARGET:
                for slug in ('sep-2322-request-state-incomplete', 'wire-schema-valid',
                             'sep-2322-request-state-complete'):
                    selected = [c for c in checks if c['id'] == slug]
                    wanted = expected if slug.endswith('-complete') else 'SUCCESS'
                    if len(selected) != 1 or selected[0]['status'] != wanted:
                        raise RuntimeError(label+': unexpected '+slug)
                if cp.returncode != (1 if expected == 'FAILURE' else 0):
                    raise RuntimeError(label+': exit code mismatch')
            elif cp.returncode or any(c['status'] != 'SUCCESS' for c in checks):
                raise RuntimeError(label+': adjacent positive scenario failed')
        finally:
            stop(proc, log)

    try:
        for repo, pin, name in ((conf, CONF_PIN, 'conformance'), (sdk, GO_PIN, 'go-sdk')):
            if run(['git', 'rev-parse', 'HEAD'], repo, name+'-head').stdout.strip() != pin:
                raise ValueError(name+' commit mismatch')
            if run(['git', 'status', '--porcelain'], repo, name+'-clean').stdout.strip():
                raise ValueError(name+' must initially be clean')
            for rel in ('LICENSE', 'go.mod', 'go.sum') if repo == sdk else ('LICENSE', 'package-lock.json'):
                data = (repo/rel).read_bytes()
                target = out/'provenance'/name/rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        data = patch.read_bytes()
        if sha(data) != PATCH_HASH:
            raise ValueError('Do not substitute a new conformance patch')
        (out/'request-state-505.patch').write_bytes(data)
        record['patch_sha256'] = sha(data)
        original = (sdk/GO_FILE).read_bytes()
        if git_blob(original) != GO_BLOB:
            raise ValueError('Unexpected Go diagnostic source identity')
        (out/'go-original.go').write_bytes(original)
        record['go_diagnostic_blob'] = GO_BLOB
        record['node_version'] = run(['node', '--version'], conf, 'node-version').stdout.strip()
        record['go_version'] = run(['go', 'version'], sdk, 'go-version').stdout.strip()
        run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], conf, 'npm-ci', 300)
        run(['go', 'mod', 'download'], sdk, 'go-mod-download', 240)
        run(['go', 'mod', 'verify'], sdk, 'go-mod-verify', 180)
        binaries = {}
        for mode in MODES:
            text = make_variant(original.decode(), mode)
            (sdk/GO_FILE).write_text(text)
            (out/('go-'+mode+'.go')).write_text(text)
            binary = runtime / ('go-server-'+mode)
            run(['go', 'build', '-mod=readonly', '-o', binary, './conformance/everything-server'],
                sdk, 'go-build-'+mode, 300)
            binaries[mode] = binary
        (sdk/GO_FILE).write_bytes(original)
        if run(['git', 'status', '--porcelain'], sdk, 'go-restored').stdout.strip():
            raise RuntimeError('Go source/dependency checkout was not restored')
        for stage in ('baseline', 'candidate'):
            if stage == 'candidate':
                run(['git', 'apply', '--check', patch], conf, 'patch-check')
                run(['git', 'apply', patch], conf, 'apply-unchanged-patch')
            run(['npm', 'run', 'build'], conf, stage+'-build', 180)
            for mode in MODES:
                cli(stage, mode, binaries[mode])
            for scenario in ('input-required-result-multi-round', 'input-required-result-tampered-state'):
                cli(stage, 'original', binaries['original'], scenario)
        run(['git', 'diff', '--check'], conf, 'diff-check')
        record['status'] = 'passed_real_go_sdk_transport_and_cli_matrix'
        record['scope'] = ('Unmodified Go SDK library and transport, pinned official diagnostic server; '
            'three negative controls alter only that fixture handler. Original conformance CLI and '
            'unchanged previously tested patch. No independent human review or live deployment.')
    except BaseException as exc:
        record['status'] = 'failed'
        record['error'] = repr(exc)
        raise
    finally:
        if original is not None:
            (sdk/GO_FILE).write_bytes(original)
        save()


if __name__ == '__main__':
    main()
