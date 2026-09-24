"""Pydantic AI #8728: distinguish inherited settings from an explicit equal ID.

Uses real Agent/DynamicCapability/WrapperCapability and local FunctionModel.
The two candidate edits are reviewer-authored experiments, not the issue author's
unpublished patch or an upstream proposal. Run only on a disposable checkout.
Zero, AI collaborator with Youngseok Oh (@YS-OH-CORE).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

REF = '8e333cef5811743584c645d3cbd84ab5bb809a3b'
REL = 'pydantic_ai_slim/pydantic_ai/capabilities/wrapper.py'
BLOB = '866b7b24fcfd387312f76c9604f1ce0f3af05f26'
MARKER = 'UNIQUE_FIXTURE_INSTRUCTION_8728'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def child(repo: Path, out: Path, mode: str) -> int:
    sys.path[:0] = [str(repo / 'pydantic_ai_slim'), str(repo / 'pydantic_graph')]
    import socket
    def deny_network(*args, **kwargs):
        raise RuntimeError('Live network is outside this test')
    socket.socket.connect = socket.socket.connect_ex = deny_network
    from dataclasses import dataclass
    from typing import ClassVar
    from pydantic_ai import Agent, RunContext, models
    from pydantic_ai.capabilities import Capability, DynamicCapability, WrapperCapability
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel
    import pydantic_ai.capabilities.wrapper as wrapper_module
    import pydantic_graph
    models.ALLOW_MODEL_REQUESTS = False
    assert Path(inspect.getfile(wrapper_module)).resolve() == repo / REL
    assert Path(inspect.getfile(pydantic_graph)).resolve().is_relative_to(repo / 'pydantic_graph')

    @dataclass
    class Wrapper(WrapperCapability[bool]):
        constructions: ClassVar[int] = 0
        def __post_init__(self) -> None:
            type(self).constructions += 1
            super().__post_init__()

    def feature(ctx: RunContext[bool]) -> Capability[bool]:
        return Capability(id='feat', description='Synthetic feature',
                          instructions=MARKER, defer_loading=ctx.deps)

    def dynamic() -> DynamicCapability[bool]:
        return DynamicCapability(feature, id='feat')

    def snapshot(capability):
        result = []
        while isinstance(capability, Wrapper):
            result.append({'id': capability.id, 'defer_loading': capability.defer_loading})
            capability = capability.wrapped
        result.append({'id': capability.id, 'defer_loading': capability.defer_loading})
        return result

    specs = [
        ('direct_dynamic', lambda: dynamic(), [True, False, True]),
        ('transparent', lambda: Wrapper(dynamic()), [True, False, True]),
        ('nested_transparent', lambda: Wrapper(Wrapper(dynamic())), [True, False, True]),
        ('explicit_equal_id_eager', lambda: Wrapper(dynamic(), id='feat', defer_loading=False), [False]*3),
        ('explicit_distinct_id_eager', lambda: Wrapper(dynamic(), id='owned', defer_loading=False), [False]*3),
        ('explicit_distinct_id_deferred', lambda: Wrapper(dynamic(), id='owned', defer_loading=True,
                                                       description='Owned deferred identity'), [True]*3),
    ]
    report = {'source_commit': REF, 'mode': mode, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'source_sha256': sha((repo / REL).read_bytes()), 'cases': [],
              'scope': 'real Agent setup and first-request FunctionModel observations; no live LLM, tool execution or provider transport',
              'live_provider_requests': 0, 'success': False}
    for name, build, expected in specs:
        row = {'name': name, 'expected_deferred': expected}
        try:
            cap = build()
            initial = snapshot(cap)
            builds = Wrapper.constructions
            requests = []
            def observe(messages, info: AgentInfo) -> ModelResponse:
                requests.append({'tools': sorted(t.name for t in info.function_tools),
                                 'instructions_sent': MARKER in (info.instructions or '')})
                return ModelResponse(parts=[TextPart('fixture complete')])
            agent = Agent(FunctionModel(observe), deps_type=bool, capabilities=[cap])
            for flag in [True, False, True]:
                result = agent.run_sync('synthetic request', deps=flag)
                assert result.output == 'fixture complete'
            row.update(requests=requests, template_before=initial, template_after=snapshot(cap),
                       constructor_reruns=Wrapper.constructions-builds)
            assert len(requests) == 3
            assert initial == snapshot(cap), 'Reusable template mutated'
            assert Wrapper.constructions == builds, 'Wrapper constructor reran during binding'
            actual = ['load_capability' in r['tools'] and not r['instructions_sent'] for r in requests]
            eager = [r['instructions_sent'] and 'load_capability' not in r['tools'] for r in requests]
            assert all(d or e for d, e in zip(actual, eager)), 'Unexpected first-request shape'
            row['observed_deferred'] = actual
            row['passed'] = actual == expected
        except Exception as exc:
            row.update(passed=False, error_type=type(exc).__name__, error=str(exc))
        report['cases'].append(row)
        print('WRAPPER_CASE ' + json.dumps(row), flush=True)
    failures = {r['name'] for r in report['cases'] if not r['passed']}
    expected_failures = {'base': {'transparent', 'nested_transparent'}, 'origin': set(),
                         'unconditional': {'explicit_equal_id_eager', 'explicit_distinct_id_eager',
                                           'explicit_distinct_id_deferred'}}[mode]
    report.update(failed_cases=sorted(failures), expected_failures=sorted(expected_failures),
                  success=failures == expected_failures and not any('error_type' in r for r in report['cases']))
    (out / (mode + '.json')).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('WRAPPER_REPORT ' + json.dumps(report), flush=True)
    return 0 if report['success'] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['base', 'origin', 'unconditional'])
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    if args.mode:
        return child(repo, out, args.mode)
    out.mkdir(parents=True, exist_ok=False)
    path = repo / REL
    original = path.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest() == BLOB
    text = original.decode('utf-8')
    post = '    def __post_init__(self) -> None:\n        self.__adopt_wrapped_identity()\n'
    guard = '        if self.id is None:\n            self.id = self.wrapped.id\n'
    assert text.count(post) == text.count(guard) == 1
    origin = text.replace(post, '    def __post_init__(self) -> None:\n        self.__identity_inherited = self.id is None\n        self.__adopt_wrapped_identity()\n', 1)
    origin = origin.replace(guard, '        if self.__identity_inherited:\n            self.id = self.wrapped.id\n', 1)
    unconditional = text.replace(guard, '        if True:  # deliberately wrong experimental control\n            self.id = self.wrapped.id\n', 1)
    variants = {'base': text, 'origin': origin, 'unconditional': unconditional}
    summary = {'source_commit': REF, 'experiment_origin': 'reviewer-authored interpretation of issue proposal',
               'success': False, 'phases': {}, 'upstream_patch_submitted': False}
    try:
        for mode, variant in variants.items():
            (out / (mode+'.patch')).write_text(''.join(difflib.unified_diff(text.splitlines(True), variant.splitlines(True),
                fromfile='a/'+REL, tofile='b/'+REL)), encoding='utf-8')
            path.write_text(variant, encoding='utf-8')
            home = out / (mode+'-home'); home.mkdir()
            env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
                   'OTEL_SDK_DISABLED': 'true', 'LOGFIRE_SEND_TO_LOGFIRE': 'false'}
            p = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--repo', str(repo),
                                '--out', str(out), '--mode', mode], cwd=home, env=env,
                               capture_output=True, text=True, timeout=60)
            (out / (mode+'.stdout.txt')).write_text(p.stdout, encoding='utf-8')
            (out / (mode+'.stderr.txt')).write_text(p.stderr, encoding='utf-8')
            print(p.stdout[-26000:]+p.stderr[-5000:], flush=True)
            summary['phases'][mode] = {'exit': p.returncode}
            p.check_returncode()
        summary['success'] = True
    except Exception as exc:
        summary['error'] = {'type': type(exc).__name__, 'message': str(exc)[:400]}
    finally:
        path.write_bytes(original)
        summary['source_restored'] = path.read_bytes() == original
        (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        print('WRAPPER_SUMMARY '+json.dumps(summary), flush=True)
    return 0 if summary['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
