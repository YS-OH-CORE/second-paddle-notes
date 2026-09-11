"""Hosted consumer of the composite action outputs, not a model evaluation."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(os.environ['RUNNER_TEMP'])/'receipt-action-fixture'
TEXT = '한글 사용자 자료\n  들여쓰기와 끝 공백  \n$(touch SHOULD_NOT_EXIST)'
WORKER = '''from pathlib import Path
import os,sys,time
root=Path(sys.argv[1]); mode=sys.argv[2]
assert not any(k in os.environ for k in ('GITHUB_OUTPUT','GITHUB_ENV','GITHUB_PATH','GITHUB_STEP_SUMMARY'))
if mode=='normal':
    (root/'actual 한글 result.txt').write_bytes(sys.argv[3].encode('utf-8'))
    print('Process not launched: OSError')  # innocent content must not override API outcome
elif mode=='failed':
    (root/'failed-effect.txt').write_text('ran before exit seven',encoding='utf-8')
    raise SystemExit(7)
elif mode=='forbidden':
    (root/'must-not-run.txt').touch()
elif mode=='deadline':
    time.sleep(5)
'''


def prepare():
    ROOT.mkdir(exist_ok=False)
    worker = ROOT/'trusted_worker.py'
    worker.write_text(WORKER, encoding='utf-8')
    stop = ROOT/'PRESTOP'; stop.touch()
    base = str(Path(sys._base_executable).resolve())
    entries = {key: json.dumps([base, '-I', str(worker), str(ROOT), mode, TEXT])
               for key, mode in [('normal','normal'), ('failed','failed'),
                                 ('forbidden','forbidden'), ('deadline','deadline')]}
    entries['stop'] = str(stop)
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8', newline='\n') as file:
        file.write(''.join(k+'='+v+'\n' for k,v in entries.items()))


def verify():
    steps = json.loads(os.environ['CHECK_STEPS'])
    evidence = Path(os.environ['RUNNER_TEMP'])/'action-evidence'
    evidence.mkdir(exist_ok=True)
    expected = {
      'normal': ('success','completed','completed','true','0','finalized'),
      'failed': ('failure','failed','failed','true','7','finalized'),
      'prestop': ('failure','failed','not_started','false','unknown','finalized'),
      'collision': ('failure','rejected','not_started','false','unknown','not_created'),
      'invalid': ('failure','rejected','not_started','false','unknown','not_created'),
      'deadline': ('failure','failed','deadline_reached','true',None,'finalized'),
    }
    observations = []
    for name, row in expected.items():
        step = steps[name]; out = step['outputs']
        actual = (step['outcome'], out.get('action-status'), out.get('execution-status'),
                  out.get('task-started'), out.get('child-exit-code'), out.get('receipt-state'))
        assert all(wanted is None or wanted == got for wanted,got in zip(row,actual)), (name, actual, row)
        summary = json.loads(Path(out['summary-path']).read_text(encoding='utf-8'))
        assert summary['execution']['status'] == out['execution-status']
        assert summary['action_status'] == out['action-status']
        if name in ('normal','failed','deadline'):
            assert out['exit-observed'] == 'true'
        destination = evidence/name; destination.mkdir(exist_ok=False)
        shutil.copyfile(out['summary-path'], destination/'action-summary.json')
        if summary['receipt_state'] == 'finalized':
            receipt = json.loads(Path(out['receipt-path']).read_bytes())
            assert all(receipt[k] == v for k,v in summary['execution'].items())
            shutil.copyfile(out['receipt-path'], destination/'receipt.json')
        observations.append({'case': name, 'step_outcome': step['outcome'], 'outputs': out,
                             'actual_execution': summary['execution']})
    assert (ROOT/'actual 한글 result.txt').read_bytes() == TEXT.encode('utf-8')
    assert (ROOT/'failed-effect.txt').read_text() == 'ran before exit seven'
    assert not (ROOT/'must-not-run.txt').exists()
    assert not (Path.cwd()/'SHOULD_NOT_EXIST').exists()
    assert (ROOT/'downstream-success.txt').read_text() == 'continued from observed completion'
    assert steps['downstream_success']['outcome'] == 'success'
    assert steps['downstream_failure']['outcome'] == 'skipped'
    stats = json.loads((evidence/'adapter-tests.json').read_text())
    assert stats['tests'] == 10 and not any(stats[k] for k in ('errors','failures','skips'))
    shutil.copyfile(ROOT/'actual 한글 result.txt', evidence/'exact-argument-output.txt')
    shutil.copyfile(ROOT/'failed-effect.txt', evidence/'failed-effect.txt')
    shutil.copyfile(ROOT/'downstream-success.txt', evidence/'downstream-success.txt')
    result = dict(status='verified', platform=sys.platform, composite_invocations=6,
                  downstream_success_executed=True, downstream_failure_skipped=True,
                  adapter_api_tests=stats['tests'], observations=observations,
                  limitations='Owned workflow, synthetic trusted children. Fault injection is in the separate adapter API suite, not a live composite step.')
    (evidence/'consumer-summary.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['verify']:
        verify()
    else:
        raise SystemExit('Expected prepare or verify')
