"""Compare the same I/O-fault tests on an unchanged baseline and current sources."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

MODULES = ('process_receipt.py', 'process_receipt_cli.py', 'process_receipt_windows.py')
DRIVER = r'''
import importlib.util, json, pathlib, sys, unittest
root, test, report = map(pathlib.Path, sys.argv[1:])
sys.path.insert(0, str(root))
import process_receipt, process_receipt_cli
assert pathlib.Path(process_receipt.__file__).resolve() == root/'process_receipt.py'
assert pathlib.Path(process_receipt_cli.__file__).resolve() == root/'process_receipt_cli.py'
spec=importlib.util.spec_from_file_location('receipt_io_tests', test)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
suite=unittest.defaultTestLoader.loadTestsFromModule(m)
r=unittest.TextTestRunner(verbosity=2).run(suite)
report.write_text(json.dumps(dict(tests=r.testsRun, failures=len(r.failures), errors=len(r.errors), skipped=len(r.skipped), success=r.wasSuccessful()), indent=2)+'\n')
sys.exit(0 if r.wasSuccessful() else 1)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    old,new=a.baseline.resolve(strict=True),a.candidate.resolve(strict=True)
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    test=Path(__file__).with_name('test_receipt_persistence.py').resolve(strict=True)
    before={str(root):{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in MODULES} for root in (old,new)}
    results={}
    for label,root in [('baseline',old),('candidate',new)]:
        allowed=('PATH','SYSTEMROOT','WINDIR','SYSTEMDRIVE','COMSPEC','PATHEXT','TEMP','TMP','TMPDIR','LANG')
        env={k:v for k,v in os.environ.items() if k.upper() in allowed}
        home=out/(label+'-home');home.mkdir()
        env.update(HOME=str(home),USERPROFILE=str(home),PYTHONIOENCODING='utf-8',PYTHONUTF8='1',
            RECEIPT_IO_OBSERVATIONS=str(out/(label+'-observations.jsonl')))
        report=out/(label+'-counts.json')
        r=subprocess.run([sys.executable,'-I','-c',DRIVER,str(root),str(test),str(report)],
            cwd=out,env=env,capture_output=True,timeout=35)
        (out/(label+'-output.txt')).write_bytes(r.stdout+b'\n'+r.stderr)
        if not report.exists(): raise RuntimeError(label+': test report missing')
        data=json.loads(report.read_text())
        skipped=1 if os.name=='nt' else 0
        expected={'tests':9,'failures':(6 if os.name=='nt' else 7) if label=='baseline' else 0,
                  'errors':0,'skipped':skipped,'success':label=='candidate'}
        if data!=expected or r.returncode!=(1 if label=='baseline' else 0):
            raise RuntimeError(label+': unexpected actual test outcomes: '+repr(data))
        observations=[json.loads(x) for x in (out/(label+'-observations.jsonl')).read_text().splitlines()]
        if len(observations)!=9-skipped: raise RuntimeError('Missing executed-case observations')
        for row in observations:
            for name,path in row['runtime_paths'].items():
                if Path(path).resolve()!=root/(name+'.py'): raise RuntimeError('Wrong source imported')
        results[label]=data
    after={str(root):{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in MODULES} for root in (old,new)}
    if before!=after: raise RuntimeError('Runtime sources changed during verification')
    summary={'status':'verified','platform':sys.platform,'python':sys.version,'results':results,
        'source_hashes':before,'source_unchanged':True,'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),
        'scope':'Real directly launched inert workers; receipt fsync/close faults injected. No real disk exhaustion, model or network call. Windows skips the POSIX-only legacy entrypoint.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
