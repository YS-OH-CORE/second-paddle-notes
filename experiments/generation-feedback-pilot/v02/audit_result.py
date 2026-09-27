"""Read-only analyst audit; no model calls, network, or primary-score repairs.
The file is added after the run; it verifies rather than changing the frozen evaluator.
"""
from pathlib import Path
import hashlib
import gzip
import json
import sys
import observe as o

ROOT=Path(__file__).resolve().parent


def audit(result):
    if result['environment']['head']!='b6a0889164ec62bd5b1ff2d4b5c9f01aca026fce':
        raise ValueError('Unexpected evaluated source')
    seeds={r['case']:r['raw_response'] for r in json.loads((ROOT.parent/'OBSERVED.json').read_text())['rows'] if r['stage']=='initial'}
    rows=result['rows']
    o.summarize(rows)  # checks exact inventory before scoring
    case_index={c['id']:c for c in o.task.TASKS}
    movements=[]
    for row in rows:
        case=case_index[row['case']];seed=seeds[case['id']]
        expected_messages=[{'role':'system','content':o.task.SYSTEM},{'role':'user','content':o.task.prompt(case)},
                           {'role':'assistant','content':seed},{'role':'user','content':o.cue(seed,case,row['condition'])}]
        if row['messages']!=expected_messages:raise ValueError('Treatment or seed differs from frozen source')
        if row['observation']!=o.observe(row['raw_response'],case):raise ValueError('Observation is not reproducible')
        old=o.observe(seed,case);new=row['observation']
        movements.append({'case':case['id'],'condition':row['condition'],
                          'raw_changed':seed!=row['raw_response'],
                          'candidate_changed':old['candidate']!=new['candidate'] if new['shape_valid'] else None,
                          'strict_feasible':new['strict']['feasible'],'candidate_feasible':new['candidate_feasible'],
                          'invalid_channel_entries':len(new['out_of_domain']) if new['shape_valid'] else None,
                          'equal_pair_count':len(new['equal_value_pairs']) if new['shape_valid'] else None,
                          'input_tokens':row['input_tokens'],'output_tokens':len(row['output_token_ids'])})
    summary=o.summarize(rows)
    if summary!=result['summary']:raise ValueError('Summary differs')
    report={'status':'audited_against_frozen_source','cells':len(rows),'new_model_calls':0,
            'all_cues_and_seeds_match':True,'all_observations_recomputed':True,
            'summary':summary,'movements':movements,
            'known_limits':'This analyst audit is not an independent replication of model inference.'}
    return report


if __name__=='__main__':
    source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'RESULT.json.gz'
    data=source.read_bytes()
    if source.suffix=='.gz':data=gzip.decompress(data)
    if len(data)!=27687 or hashlib.sha256(data).hexdigest()!='ad7051056bac34d164228b04e6e8ee60d23cd9d271fab5b41466469b77c21bc1':
        raise ValueError('Recorded result bytes differ from inference-log digest')
    print(json.dumps(audit(json.loads(data)),ensure_ascii=False,indent=2))
