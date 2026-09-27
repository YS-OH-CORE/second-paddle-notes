"""Post-run read-only audit against frozen prompts, parser and seed values.
This audit does not run a model or constitute independent model replication.
"""
from pathlib import Path
import argparse, gzip, hashlib, json
import probe

def audit(data):
    if data['environment']['source_head']!='e19c1c03cf3190bc229f202ab6f787a5020a7891':
        raise ValueError('Unexpected source head')
    plan={r['id']:r for r in probe.cells()}
    rows=data['rows']
    if len(rows)!=8 or len({r['id'] for r in rows})!=8 or {r['id'] for r in rows}!=set(plan):
        raise ValueError('Incomplete, duplicate, or foreign inventory')
    for row in rows:
        expected=plan[row['id']]
        for name in ('case','condition','messages'):
            if row[name]!=expected[name]:raise ValueError('Changed stimulus: '+row['id'])
        if row['observation']!=probe.o.observe(row['raw'],row['case']):
            raise ValueError('Changed scoring: '+row['id'])
        if len(row['output_ids'])!=row['output_tokens']:raise ValueError('Output length')
        if row['input_tokens']>1200 or row['output_tokens']>96:raise ValueError('Budget exceeded')
    if probe.summarize(rows)!=data['summary']:raise ValueError('Summary mismatch')
    index={r['id']:r for r in rows}
    for graph in probe.GOOD:
        if index[graph+'/bad_prior']['input_tokens']!=index[graph+'/valid_prior']['input_tokens']:
            raise ValueError('Prior-pair token imbalance')
    root=Path(__file__).resolve().parent
    for name,wanted in data['environment']['manifest'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=wanted:raise ValueError('Frozen source drift')
    return {'status':'input_and_score_audit_passed','new_model_calls':0,'cells':8,
            'all_declared_inputs_match':True,'all_observations_recomputed':True,
            'prior_pairs_token_matched':True,'summary':data['summary'],
            'full_raw_outputs_retained':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('result',type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();raw=args.result.read_bytes()
    if args.result.suffix=='.gz':raw=gzip.decompress(raw)
    if hashlib.sha256(raw).hexdigest()!=args.sha256:raise ValueError('Result bytes differ from run digest')
    print(json.dumps(audit(json.loads(raw)),ensure_ascii=False,indent=2))
