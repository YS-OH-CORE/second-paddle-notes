"""Finite constructive tasks: candidates are retained, not treated as facts.
Standard library only. No model, files, network or executable action dispatch.
"""
from __future__ import annotations
import itertools
import json

TASKS = (
    {'id':'G1','edges':[[0,1],[1,2],[2,3],[3,4],[4,5],[5,0]]},
    {'id':'G2','edges':[[0,1],[1,2],[2,0],[3,4],[4,5],[5,3],[0,3],[1,4],[2,5]]},
    {'id':'G3','edges':[[0,3],[0,4],[0,5],[1,3],[1,4],[1,5],[2,3],[2,4],[2,5]]},
    {'id':'G4','edges':[[0,1],[1,2],[2,0],[3,4],[4,5],[5,3],[2,3]]},
)
SYSTEM = 'Construct a feasible assignment. Return only one JSON object with the single key "assignment" and a list of six integers. No explanation or Markdown.'
NEUTRAL = 'Review your candidate against the original constraints. Return a revised assignment, or keep it if it already satisfies all constraints. Use the same JSON format.'

def prompt(task):
    return ('Assign six stations numbered 0, 1, 2, 3, 4, 5 to channels 0, 1, or 2. '
            'For every pair listed below, the two stations must use different channels. '
            'Any assignment satisfying all pairs is acceptable; no one target arrangement is preferred. '
            'The list positions must correspond to stations 0 through 5. '
            'Different-channel pairs: '+json.dumps(task['edges'],separators=(',',':')))

def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate key')
        result[key]=value
    return result

def evaluate(raw, task):
    try:
        obj=json.loads(raw,object_pairs_hook=unique_object,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite')))
        if not isinstance(obj,dict) or set(obj)!={'assignment'}:raise ValueError('object grammar')
        a=obj['assignment']
        if not isinstance(a,list) or len(a)!=6 or any(type(x) is not int or x not in range(3) for x in a):
            raise ValueError('assignment grammar')
    except (ValueError,TypeError,json.JSONDecodeError):
        return {'format_valid':False,'assignment':None,'violated_pairs':None,
                'constraints_satisfied':None,'feasible':False}
    bad=[pair for pair in task['edges'] if a[pair[0]]==a[pair[1]]]
    return {'format_valid':True,'assignment':a,'violated_pairs':bad,
            'constraints_satisfied':len(task['edges'])-len(bad),'feasible':not bad}

def feedback(evaluation):
    observed=({'format_valid':False} if not evaluation['format_valid'] else
              {'format_valid':True,'violated_pairs':evaluation['violated_pairs']})
    return ('An exact checker examined your candidate. Observation: '+
            json.dumps(observed,separators=(',',':'))+'. '+NEUTRAL)

def compare(first, later,task):
    if not first['format_valid'] or not later['format_valid']:
        return {'changed_stations':None,'newly_satisfied':None,'previously_satisfied_lost':None}
    a,b=first['assignment'],later['assignment']
    prev={tuple(e) for e in task['edges'] if a[e[0]]!=a[e[1]]}
    now={tuple(e) for e in task['edges'] if b[e[0]]!=b[e[1]]}
    return {'changed_stations':sum(x!=y for x,y in zip(a,b)),
            'newly_satisfied':len(now-prev),'previously_satisfied_lost':len(prev-now)}

def solutions(task):
    return [a for a in itertools.product(range(3),repeat=6)
            if all(a[u]!=a[v] for u,v in task['edges'])]
