"""Observe a candidate without repairing it or replacing v0.1 acceptance.
Accept for inspection only one bare object or one whole JSON fence. Never
execute a candidate, invent missing entries, clamp values, or search prose.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import task

CONDITIONS = ('coarse', 'format_explicit', 'layered')


def observe(raw, case):
    result = {'strict': task.evaluate(raw, case), 'serialization': 'unrecognized',
              'object_decoded': False, 'shape_valid': False, 'candidate': None,
              'out_of_domain': None, 'equal_value_pairs': None,
              'fully_in_domain_pairs': None, 'candidate_feasible': False}
    if not isinstance(raw, str) or len(raw) > 10000:
        return result
    text = raw.strip()
    if text.startswith('```json\n') and text.endswith('\n```') and text.count('```') == 2:
        text = text[8:-4]
        result['serialization'] = 'whole_json_fence'
    else:
        result['serialization'] = 'bare_attempt'
    try:
        obj = json.loads(text, object_pairs_hook=task.unique_object,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    except (ValueError, TypeError, RecursionError):
        return result
    result['object_decoded'] = True
    if not isinstance(obj, dict) or set(obj) != {'assignment'}:
        return result
    a = obj['assignment']
    if not isinstance(a, list) or len(a) != 6 or any(type(x) is not int for x in a):
        return result
    result.update(shape_valid=True, candidate=a,
                  out_of_domain=[{'station': i, 'value': x} for i, x in enumerate(a) if x not in (0, 1, 2)],
                  equal_value_pairs=[e for e in case['edges'] if a[e[0]] == a[e[1]]],
                  fully_in_domain_pairs=[e for e in case['edges'] if a[e[0]] in (0, 1, 2) and a[e[1]] in (0, 1, 2)])
    result['candidate_feasible'] = not result['out_of_domain'] and not result['equal_value_pairs']
    return result


def cue(raw, case, condition):
    if condition == 'coarse':
        return task.feedback(task.evaluate(raw, case))
    if condition not in CONDITIONS:
        raise ValueError('Unknown condition')
    o = observe(raw, case)
    # This experiment reuses only verified fenced, six-integer initial seeds.
    if o['serialization'] != 'whole_json_fence' or not o['shape_valid']:
        raise ValueError('The frozen seed preconditions no longer hold')
    text = ('Your response used a Markdown code block. Return only the JSON object, '
            'without the opening or closing triple backticks. ')
    if condition == 'layered':
        text += ('The checker could still read the proposed list. '
                 'Allowed channel values are 0, 1, 2. Out-of-domain entries: ' +
                 json.dumps(o['out_of_domain'], separators=(',', ':')) + '. '
                 'List positions identify stations; list values identify channels. '
                 'Pairs assigned equal values: ' + json.dumps(o['equal_value_pairs'], separators=(',', ':')) + '. '
                 'An empty equal-pair list is not sufficient: every value must also be an allowed channel. ')
    return text + task.NEUTRAL


def summarize(rows):
    wanted = {(t['id'], c) for t in task.TASKS for c in CONDITIONS}
    if len(rows) != 12 or {(r['case'], r['condition']) for r in rows} != wanted:
        raise ValueError('Missing, duplicate or unknown cell')
    result = {}
    for c in CONDITIONS:
        group = [r for r in rows if r['condition'] == c]
        result[c] = {'denominator': 4,
                     'strict_feasible': sum(r['observation']['strict']['feasible'] for r in group),
                     'shape_readable': sum(r['observation']['shape_valid'] for r in group),
                     'candidate_feasible': sum(r['observation']['candidate_feasible'] for r in group),
                     'domain_valid': sum(r['observation']['shape_valid'] and not r['observation']['out_of_domain'] for r in group)}
    return result
