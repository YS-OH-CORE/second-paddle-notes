"""Run a bounded follow-up against one pinned LangGraph checkout."""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

PIN = '7daa3ab49d678a5da75edb08baa87db4a2be52c3'
BLOB = '95e161b9078e3123afa1854247a5dfd132410a53'
PROBE_SHA = 'ce94a2042bd5d4ea8562696a44750df666a6f26f3b90e9d2608681b2a1ba4d1c'
BASELINE_SHA = '86b4a500e79568eae246894d70b6b59893e7a714477f800119627b99319b68c1'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    args = p.parse_args()
    root, bundle = args.root.resolve(), args.bundle.resolve()
    root.mkdir(exist_ok=False)
    out = root / 'output'
    out.mkdir()
    report = {'completed': False, 'upstream_commit': PIN, 'variants': [], 'model_calls': 0,
              'run_id': os.environ.get('GITHUB_RUN_ID'), 'workflow_commit': os.environ.get('GITHUB_SHA')}
    source, original = None, None
    def call(argv, env=None, timeout=180):
        r = subprocess.run(list(map(str, argv)), cwd=root, env=env, text=True, capture_output=True, timeout=timeout)
        with (out / 'execution.log').open('a', encoding='utf-8') as log:
            log.write('COMMAND ' + str(argv) + '\n' + r.stdout + '\nSTDERR\n' + r.stderr + '\n')
        print(r.stdout[-2000:] + r.stderr[-2000:], flush=True)
        return r
    try:
        for name, expected in (('edge_probe.py', PROBE_SHA), ('baseline_probe.py', BASELINE_SHA)):
            data = (bundle / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == expected
            (out / name).write_bytes(data)
        (out / 'run_edge.py').write_bytes(Path(__file__).read_bytes())
        (out / 'PROTOCOL.md').write_bytes((bundle / 'PROTOCOL.md').read_bytes())
        archive = root / 'source.zip'
        with urllib.request.urlopen(f'https://codeload.github.com/langchain-ai/langgraph/zip/{PIN}', timeout=45) as r:
            data = r.read(100_000_001)
        assert len(data) <= 100_000_000
        archive.write_bytes(data)
        report['archive_sha256'] = hashlib.sha256(data).hexdigest()
        with zipfile.ZipFile(archive) as z:
            assert all((root / n).resolve().is_relative_to(root) for n in z.namelist())
            z.extractall(root)
        repo = root / ('langgraph-' + PIN)
        source = repo / 'libs/prebuilt/langgraph/prebuilt/tool_node.py'
        raw = source.read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == BLOB
        original = raw.decode()
        (out / 'LICENSE.upstream').write_bytes((repo / 'LICENSE').read_bytes())
        (out / 'tool_node.original.py').write_bytes(raw)
        call([sys.executable, '-m', 'venv', root / 'venv'], timeout=30).check_returncode()
        py = root / 'venv/bin/python'
        libs = [repo / 'libs' / n for n in ('checkpoint', 'sdk-py', 'prebuilt', 'langgraph')]
        call([py, '-m', 'pip', 'install', '--disable-pip-version-check', *libs, 'langchain-core==1.6.5'], timeout=240).check_returncode()
        env_result = call([py, '-m', 'pip', 'freeze', '--all'])
        env_result.check_returncode()
        (out / 'environment.txt').write_text(env_result.stdout, encoding='utf-8')
        fresh = 'parent_command = Command(graph=Command.PARENT, goto=output.goto)'
        goto = 'goto=cast("list[Send]", parent_command.goto) + output.goto,'
        assert original.count(fresh) == original.count(goto) == 1
        prior = original.replace(fresh, 'parent_command = output').replace(
            goto, goto + '\n                            update=parent_command._update_as_tuples() + output._update_as_tuples(),')
        assert hashlib.sha256(prior.encode()).hexdigest() == '32ee5d28f4bff7b6af6694ba4ea6abb87dc1048ba5bbefd1a8314fa6efbe2dcd'
        normalized = prior.replace('update=parent_command._update_as_tuples() + output._update_as_tuples(),',
            'update=list(parent_command._update_as_tuples()) + list(output._update_as_tuples()),')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, libs)), PYTHONDONTWRITEBYTECODE='1',
                   LANGSMITH_TRACING='false', LANGCHAIN_TRACING_V2='false')
        for key in list(env):
            if key.endswith('API_KEY'):
                env.pop(key, None)
        for name, text in (('base', original), ('prior_ordered', prior), ('normalized_ordered', normalized)):
            ast.parse(text)
            target = out / name
            target.mkdir()
            source.write_text(text, encoding='utf-8')
            (target / 'tool_node.py').write_text(text, encoding='utf-8')
            (target / 'experimental.diff').write_text(''.join(difflib.unified_diff(
                original.splitlines(True), text.splitlines(True), fromfile='base/tool_node.py', tofile=name + '/tool_node.py')))
            r = call([py, '-B', out / 'edge_probe.py', '--baseline-probe', out / 'baseline_probe.py',
                      '--source-module', source, '--variant', name, '--out', target / 'report.json'], env=env, timeout=120)
            (target / 'execution.log').write_text(r.stdout + '\nSTDERR\n' + r.stderr, encoding='utf-8')
            if (target / 'report.json').exists():
                observed = json.loads((target / 'report.json').read_text())
                assert observed['source_sha256'] == hashlib.sha256(text.encode()).hexdigest()
                report['variants'].append(observed)
            r.check_returncode()
        report.update(completed=True, graph_invocations=sum(v['count'] for v in report['variants']))
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        if original is not None:
            source.write_text(original, encoding='utf-8')
        (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'completed': report['completed'], 'counts': [(v['variant'], v['count'], v['contract_met']) for v in report['variants']], 'error': report.get('error')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
