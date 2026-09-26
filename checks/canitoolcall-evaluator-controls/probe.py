# SPDX-License-Identifier: Apache-2.0
"""Check a frozen evaluator against its own expected parses and bad outputs.

Youngseok Oh x Zero. No inference-engine parsing or model generation occurs.
Source fixtures remain unchanged; synthetic ParseResult controls test the scorer.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import inspect
import json
from pathlib import Path
import socket
import sys

PIN = '9edf62cfd4c493749ca76bc8816db86a5bc8f91d'
CHECKS_BLOB = '2d89ddc661920bc08c686b3edd7aeba9e73f4b13'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();repo=a.repo.resolve();out=a.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(repo/'src'))
    from canitoolcall import checks
    from canitoolcall.fixtures import Fixture,Family
    from canitoolcall.results import Observation,ParseResult,ParsedToolCall,Status
    source=Path(inspect.getfile(checks)).resolve()
    assert source==repo/'src/canitoolcall/checks.py'
    raw=source.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==CHECKS_BLOB
    attempts=[]
    def deny(*args,**kwargs):
        attempts.append('socket_or_dns');raise RuntimeError('No network during evaluator check')
    socket.socket.connect=socket.socket.connect_ex=socket.getaddrinfo=deny
    rows=[]; manifest={}; seen=set()
    def sha(data):return hashlib.sha256(data).hexdigest()
    def save(name,data):
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def assess(family,fixture,kind,value,expected_pass):
        # Identical synthetic observations isolate grader behavior, not chunking.
        observation=Observation(nonstream=value,streams={'token':value,'one':value})
        try:
            cr=checks.run_checks(fixture,family,observation)
            status=checks.case_status(cr).value
            details=[asdict(r) for r in cr if r.status not in (Status.PASS,Status.SOFT_PASS)]
            actual_pass=status in ('pass','soft_pass')
            row={'fixture':fixture.id,'kind':kind,'expected_pass':expected_pass,
                 'status':status,'contract_met':actual_pass==expected_pass,'details':details}
        except Exception as exc:
            row={'fixture':fixture.id,'kind':kind,'expected_pass':expected_pass,
                 'status':'raised','contract_met':False,'error':type(exc).__name__+': '+str(exc)}
        rows.append(row)
    for fp in sorted((repo/'fixtures').glob('*/family.json')):
        fam=Family.from_dict(json.loads(fp.read_text()))
        manifest[str(fp.relative_to(repo))]=sha(fp.read_bytes())
        for path in sorted(fp.parent.glob('*.jsonl')):
            data=path.read_bytes();manifest[str(path.relative_to(repo))]=sha(data)
            for line_no,line in enumerate(data.decode().splitlines(),1):
                if not line.strip():continue
                f=Fixture.from_dict(json.loads(line),source=path,line=line_no)
                assert f.id not in seen,f.id
                seen.add(f.id)
                if f.expected is not None:
                    want=checks.expected_as_result(f.expected)
                    assess(fam,f,'exact_expected',want,True)
                    if want.content:
                        assess(fam,f,'drop_content',replace(want,content=None),False)
                    if want.reasoning_content:
                        assess(fam,f,'drop_reasoning',replace(want,reasoning_content=None),False)
                    if want.tool_calls:
                        assess(fam,f,'drop_all_calls',replace(want,tool_calls=()),False)
                        first=want.tool_calls[0]
                        bad=replace(first,name='ZERO_SYNTHETIC_UNOFFERED_TOOL')
                        assess(fam,f,'rename_tool',replace(want,tool_calls=(bad,*want.tool_calls[1:])),False)
                        bad=replace(first,arguments_raw='{"duplicate":1,"duplicate":2}')
                        assess(fam,f,'duplicate_json_key',replace(want,tool_calls=(bad,*want.tool_calls[1:])),False)
                    else:
                        bad=ParsedToolCall('ZERO_SYNTHETIC_UNOFFERED_TOOL','{}')
                        assess(fam,f,'invent_call',replace(want,tool_calls=(bad,)),False)
                else:
                    assert f.expected_error is not None
                    for outcome in f.expected_error.accept:
                        result=(ParseResult(exception='SyntheticExpectedFailure: evaluator control') if outcome=='exception'
                                else ParseResult(content=f.raw_output) if outcome=='content_passthrough'
                                else ParseResult())
                        assess(fam,f,'accepted_'+outcome,result,True)
                    assess(fam,f,'partial_call_then_error',ParseResult(
                        exception='SyntheticExpectedFailure: after output',
                        tool_calls=(ParsedToolCall('ZERO_SYNTHETIC_PARTIAL_TOOL','{}'),)),False)
    # Save all observations, including failures. Green means the run completed,
    # NOT that all of the evaluator contracts were met.
    save('OBSERVATIONS.json',rows)
    save('FIXTURE_MANIFEST.json',manifest)
    summary={'source_commit':PIN,'fixture_count':len(seen),'observations':len(rows),
             'by_kind':{k:dict(Counter(r['status'] for r in rows if r['kind']==k)) for k in sorted({r['kind'] for r in rows})},
             'contract_failures':[r for r in rows if not r['contract_met']],
             'model_calls':0,'engine_parser_calls':0,'network_attempts':len(attempts),
             'python':sys.version,'checks_sha256':sha(raw),'completed':True,
             'scope':'Actual evaluator imports with expected-output and synthetic-corruption controls; no engine replay or benchmark replication'}
    save('SUMMARY.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
