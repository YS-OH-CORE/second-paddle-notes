#!/usr/bin/env python3
"""Execute issue #505 through upstream imports, HTTP, and the existing CLI.

Run only on a disposable checkout of the pinned public repository. This script
adds fixture regressions, tests the old check, applies a narrowly scoped candidate,
then repeats the tests and uses the official CLI against the bundled server.
No private data, model inference, remote application writes or credentials.
"""
from __future__ import annotations
import argparse, difflib, hashlib, json, os, signal, socket, subprocess, time
from pathlib import Path

PIN = '7169291ec0b68eb370fddcd9947313ab0d5e4156'
SCENARIO = Path('src/scenarios/server/input-required-result.ts')
TEST = Path('src/scenarios/server/negative-mrtr.test.ts')
FIXTURE = Path('examples/servers/typescript/sep-2322-mrtr-broken-server.ts')
SERVER = Path('examples/servers/typescript/everything-server.ts')
EXPECTED_BLOBS = {
 str(SCENARIO): '64ad4ba9e5f054259095ba38860164926296a930',
 str(TEST): '871ad73b6416fa6464d2a948efeef66dbed1853e',
 str(FIXTURE): '72cf602137a451e766dd643f07d2a6096395ae1c',
 str(SERVER): 'c76c1f565dd5e7be972cd29f4f7a881cbfffa65a',
}

FIXTURE_CASE = '''    case 'test_input_required_result_request_state': {
      if (!inputResponses) {
        return {
          resultType: 'input_required',
          inputRequests: {
            confirm: {
              method: 'elicitation/create',
              params: {
                message: 'Confirm?',
                requestedSchema: {
                  type: 'object',
                  properties: { ok: { type: 'boolean' } },
                  required: ['ok']
                }
              }
            }
          },
          requestState: 'request-state-negative-fixture'
        };
      }
      if (params.requestState !== 'request-state-negative-fixture' ||
          !inputResponses['confirm']) {
        throw { code: -32602, message: 'Expected echoed state and confirm response' };
      }
      const mode = process.env.MRTR_REQUEST_STATE_MODE || 'missing-marker';
      if (mode === 'jsonrpc-error') {
        throw { code: -32602, message: 'State rejected' };
      }
      if (mode === 'input-required') {
        return { resultType: 'input_required', requestState: 'still-pending' };
      }
      const isError = mode === 'tool-error' || mode === 'tool-error-with-marker';
      const marker = mode === 'valid' || mode === 'valid-second-text' ||
        mode === 'tool-error-with-marker';
      return {
        resultType: 'complete',
        isError,
        content: mode === 'empty-content' ? [] : [
          ...(mode === 'valid-second-text' ? [{ type: 'text', text: 'Context' }] : []),
          { type: 'text', text: marker ? 'state-ok: requestState validated' : 'State rejected' }
        ]
      };
    }

'''

REGRESSIONS = '''
// Issue #505: completion type alone does not establish fixture success.
describe('SEP-2322 request-state completion semantics', () => {
  it.each([
    ['valid', 'SUCCESS'],
    ['valid-second-text', 'SUCCESS'],
    ['missing-marker', 'FAILURE'],
    ['empty-content', 'FAILURE'],
    ['tool-error', 'FAILURE'],
    ['tool-error-with-marker', 'FAILURE'],
    ['jsonrpc-error', 'FAILURE'],
    ['input-required', 'FAILURE']
  ])('request-state %s emits %s', async (mode, expected) => {
    const port = await getFreePort();
    let proc: ChildProcess | null = null;
    try {
      proc = await startServer(
        path.join(process.cwd(), 'examples/servers/typescript/sep-2322-mrtr-broken-server.ts'),
        port,
        { MRTR_REQUEST_STATE_MODE: mode }
      );
      const checks = await new InputRequiredResultRequestStateScenario().run(
        testContext(`http://localhost:${port}/mcp`)
      );
      // Prove the second check was reached with a valid round-1 prerequisite.
      expect(checks.find(c => c.id === 'sep-2322-request-state-incomplete')?.status)
        .toBe('SUCCESS');
      const complete = checks.filter(c => c.id === 'sep-2322-request-state-complete');
      expect(complete).toHaveLength(1);
      expect(complete[0].status).toBe(expected);
      if (mode.startsWith('tool-error')) {
        expect(complete[0].errorMessage).toContain('isError');
      }
      if (mode === 'missing-marker' || mode === 'empty-content') {
        expect(complete[0].errorMessage).toContain('state-ok');
      }
    } finally {
      await stopServer(proc);
    }
  }, 20000);
});
'''

CANDIDATE = '''        } else {
          if (r2Result.isError === true) {
            r2Errors.push('Tool result reported isError: true after retry with requestState');
          }
          const content = r2Result.content;
          const hasStateMarker = Array.isArray(content) && content.some(
            (block) => typeof block === 'object' && block !== null &&
              block.type === 'text' && typeof block.text === 'string' &&
              block.text.includes('state-ok')
          );
          if (!hasStateMarker) {
            r2Errors.push('Expected text content containing the fixture marker "state-ok"');
          }
'''


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    record = {'status': 'incomplete', 'commands': [], 'source_commit': PIN}
    originals: dict[Path, bytes] = {}
    def save():
        (out/'verification.json').write_text(json.dumps(record, indent=2)+'\n')
    def run(argv, name, timeout=180, allowed=(0,)):
        started = time.monotonic()
        cp = subprocess.run(argv, cwd=repo, env={**os.environ, 'CI': 'true', 'LEFTHOOK': '0'},
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=timeout)
        (out/(name+'.log')).write_text(cp.stdout)
        record['commands'].append({'argv': argv, 'log': name+'.log',
            'returncode': cp.returncode, 'elapsed_seconds': round(time.monotonic()-started, 3)})
        save()
        if cp.returncode not in allowed:
            raise RuntimeError(f'{name} returned {cp.returncode}; see retained log')
        return cp
    def replace_once(text, old, new):
        if text.count(old) != 1:
            raise ValueError('Source anchor is missing or ambiguous: '+old[:75])
        return text.replace(old, new, 1)
    def launch(argv, name, port):
        log = (out/(name+'.log')).open('w')
        proc = subprocess.Popen(argv, cwd=repo, env={**os.environ, 'PORT': str(port)},
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(150):
            if proc.poll() is not None:
                log.close(); raise RuntimeError(name+' exited before listening')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                    return proc, log
            except OSError:
                time.sleep(0.2)
        stop(proc, log)
        raise RuntimeError(name+' readiness timeout')
    def stop(proc, log):
        if proc.poll() is None:
            # Only the isolated process group created by launch is stopped.
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=5)
        log.close()
    def free_port():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); return sock.getsockname()[1]
    def test_run(label, expected_failures):
        report_path = out/(label+'.json')
        cp = run(['node','node_modules/vitest/vitest.mjs','run',str(TEST),
            '--reporter=json', '--outputFile='+str(report_path)], label, 240, (0,1))
        report = json.loads(report_path.read_text())
        checks = [a for suite in report.get('testResults', [])
                    for a in suite.get('assertionResults', [])]
        failed = [a.get('fullName', a.get('title')) for a in checks if a.get('status') == 'failed']
        if len(checks) != 12 or len(failed) != expected_failures:
            raise RuntimeError(f'{label}: expected 12 tests / {expected_failures} failures, got {len(checks)} / {len(failed)}')
        if any('request-state completion semantics' not in name for name in failed):
            raise RuntimeError('Failure outside the new targeted cases')
        if (expected_failures == 0) != (cp.returncode == 0):
            raise RuntimeError('Test process status contradicts assertions')
        record[label] = {'total': len(checks), 'failed': failed, 'passed': len(checks)-len(failed)}
        save()
    def collect_checks(path):
        seen = []
        def visit(obj):
            if isinstance(obj, dict):
                if 'id' in obj and 'status' in obj: seen.append(obj)
                for value in obj.values(): visit(value)
            elif isinstance(obj, list):
                for value in obj: visit(value)
        for file in path.rglob('checks.json'):
            visit(json.loads(file.read_text()))
        return seen
    def cli_run(label, script, mode=None, expected='SUCCESS'):
        port = free_port()
        saved_mode = os.environ.get('MRTR_REQUEST_STATE_MODE')
        if mode is not None: os.environ['MRTR_REQUEST_STATE_MODE'] = mode
        proc, log = launch(['node','node_modules/tsx/dist/cli.mjs',str(script)], label+'-server', port)
        try:
            output = out/(label+'-results')
            cp = run(['node','dist/index.js','server','--url',f'http://localhost:{port}/mcp',
                '--scenario','input-required-result-request-state','--spec-version','2026-07-28',
                '-o',str(output)], label, 90, (0,1))
            checks = collect_checks(output)
            first = [c for c in checks if c['id']=='sep-2322-request-state-incomplete']
            last = [c for c in checks if c['id']=='sep-2322-request-state-complete']
            if len(first)!=1 or first[0]['status']!='SUCCESS' or len(last)!=1 or last[0]['status']!=expected:
                raise RuntimeError(label+': named CLI checks did not match the expected path')
            record[label] = {'returncode': cp.returncode, 'target_check': last[0],
                'checks': [{'id':c['id'],'status':c['status']} for c in checks]}
            save()
        finally:
            stop(proc,log)
            if saved_mode is None: os.environ.pop('MRTR_REQUEST_STATE_MODE',None)
            else: os.environ['MRTR_REQUEST_STATE_MODE']=saved_mode
    try:
        actual = run(['git','rev-parse','HEAD'],'upstream-commit').stdout.strip()
        if actual != PIN or run(['git','status','--porcelain'],'clean-checkout').stdout.strip():
            raise RuntimeError('Use a clean disposable checkout of the exact pinned commit')
        record['sources'] = {}
        for rel, expected in EXPECTED_BLOBS.items():
            path = Path(rel); data = (repo/path).read_bytes(); originals[path]=data
            blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if blob != expected: raise RuntimeError('Pinned source identity mismatch: '+rel)
            record['sources'][rel] = {'git_blob':blob,'sha256':digest(data)}
            target=out/'original'/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        record['node'] = run(['node','--version'],'node-version').stdout.strip()
        record['npm'] = run(['npm','--version'],'npm-version').stdout.strip()
        lock=(repo/'package-lock.json').read_bytes()
        (out/'package-lock.json').write_bytes(lock); record['lock_sha256']=digest(lock)
        run(['npm','ci','--ignore-scripts','--no-audit','--no-fund'],'npm-ci',300)
        record['sdk_version']=json.loads((repo/'node_modules/@modelcontextprotocol/sdk/package.json').read_text())['version']
        run(['npm','run','build'],'baseline-build',180)
        cli_run('baseline-everything',SERVER)
        # Add cases in the existing fixture and existing negative-test file.
        fixture=replace_once(originals[FIXTURE].decode(),
            "    case 'test_input_required_result_capabilities': {", FIXTURE_CASE+"    case 'test_input_required_result_capabilities': {")
        tests=replace_once(originals[TEST].decode(), '  InputRequiredResultCapabilityCheckScenario\n',
            '  InputRequiredResultCapabilityCheckScenario,\n  InputRequiredResultRequestStateScenario\n')
        tests=replace_once(tests,'function startServer(scriptPath: string, port: number): Promise<ChildProcess> {',
            'function startServer(scriptPath: string, port: number, extraEnv: NodeJS.ProcessEnv = {}): Promise<ChildProcess> {')
        tests=replace_once(tests,"env: { ...process.env, PORT: port.toString() },",
            "env: { ...process.env, ...extraEnv, PORT: port.toString() },")+REGRESSIONS
        (repo/FIXTURE).write_text(fixture); (repo/TEST).write_text(tests)
        test_run('before-source-fix',4)
        for mode in ('missing-marker','tool-error','tool-error-with-marker'):
            cli_run('baseline-'+mode,FIXTURE,mode,'SUCCESS')
        source=originals[SCENARIO].decode()
        begin=source.index('export class InputRequiredResultRequestStateScenario')
        end=source.index('export class InputRequiredResultMultipleInputRequestsScenario',begin)
        section=source[begin:end]
        anchor="            'Expected complete result after retry with requestState'\n          );\n"
        section=replace_once(section,anchor,anchor+CANDIDATE)
        (repo/SCENARIO).write_text(source[:begin]+section+source[end:])
        run(['node','node_modules/prettier/bin/prettier.cjs','--write',str(SCENARIO),str(TEST),str(FIXTURE)],'format-candidate')
        test_run('after-source-fix',0)
        run(['npm','run','build'],'candidate-build')
        cli_run('candidate-everything',SERVER)
        for mode in ('missing-marker','tool-error','tool-error-with-marker'):
            cli_run('candidate-'+mode,FIXTURE,mode,'FAILURE')
        # All other tests are unmodified; retain any unrelated failures verbatim.
        full=run(['npm','test','--','--reporter=json','--outputFile='+str(out/'full-suite.json')],
            'full-suite',300,(0,1))
        record['full_suite_returncode']=full.returncode
        run(['npm','run','typecheck'],'typecheck',180,(0,1))
        run(['node','node_modules/eslint/bin/eslint.js',str(SCENARIO),str(TEST),str(FIXTURE)],'touched-eslint',180,(0,1))
        run(['git','diff','--check'],'diff-check')
        diffs=[]
        for path in (SCENARIO,TEST,FIXTURE):
            data=(repo/path).read_bytes(); target=out/'candidate'/path
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            diffs.extend(difflib.unified_diff(originals[path].decode().splitlines(True),
                data.decode().splitlines(True),fromfile='a/'+str(path),tofile='b/'+str(path)))
        (out/'request-state-505.patch').write_text(''.join(diffs))
        record['status']='targeted_upstream_tests_and_cli_passed'
        record['scope']='Pinned actual modules and upstream CLI over loopback HTTP. Bundled everything-server uses SDK imports but MRTR is its explicit stateless handler, not an independently supplied SDK implementation. Full-suite result is separate. No maintainer acceptance.'
    except Exception as exc:
        record['status']='failed'; record['error']=str(exc); raise
    finally:
        # Preserve every altered source even on failure. No reset/deletion of evidence.
        for path in originals:
            if (repo/path).exists() and (repo/path).read_bytes()!=originals[path]:
                dest=out/'work-in-progress'/path;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((repo/path).read_bytes())
        save()

if __name__ == '__main__':
    main()
