"""Recompute recorded first-response scores. No model generation or score repair."""
from pathlib import Path
import json
import task

def audit(observed):
    rows=observed['rows'];stages=('initial','neutral','feedback')
    index={(r['case'],r['stage']):r for r in rows}
    if len(rows)!=12 or len(index)!=12 or set(index)!={(t['id'],s) for t in task.TASKS for s in stages}:
        raise ValueError('Missing or duplicated model response')
    counts={s:{'format_valid':0,'feasible':0,'denominator':4} for s in stages}
    for t in task.TASKS:
        for s in stages:
            evaluation=task.evaluate(index[t['id'],s]['raw_response'],t)
            for metric in ('format_valid','feasible'):counts[s][metric]+=int(evaluation[metric])
    primary={'counts':counts,'model_generations':12,'complete_inventory':True,
             'scores_recomputed_without_repair':True,
             'changed_feedback_responses':[t['id'] for t in task.TASKS if index[t['id'],'initial']['raw_response']!=index[t['id'],'feedback']['raw_response']],
             'changed_neutral_responses':[t['id'] for t in task.TASKS if index[t['id'],'initial']['raw_response']!=index[t['id'],'neutral']['raw_response']]}
    # Post-hoc inspection, explicitly excluded from primary scores and feedback.
    out_of_range=[]
    for r in rows:
        raw=r['raw_response']
        if raw.startswith('```json\n') and raw.endswith('\n```'):
            obj=json.loads(raw[len('```json\n'):-len('\n```')])
            if any(x not in (0,1,2) for x in obj['assignment']):out_of_range.append([r['case'],r['stage']])
    primary['post_hoc_only']={'method':'Inspect one fenced JSON object; do not change primary parser or scores.',
       'out_of_range_even_ignoring_markdown_fences':out_of_range,
       'conflict_specific_feedback_delivered':0,
       'why':'All four initial proposals failed the declared grammar, so the actual feedback was only format_valid=false.'}
    return primary

if __name__=='__main__':
    w=Path(__file__).resolve().parent
    report=audit(json.loads((w/'OBSERVED.json').read_text()))
    print(json.dumps(report,ensure_ascii=False,indent=2))
