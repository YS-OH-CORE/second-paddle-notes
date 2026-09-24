"""Recalculate two published memory development runs, offline, Python 3.10+.

Read ZIP members without extracting or executing their code. No model, package
installation, network request, credential, or personal workspace is needed.
This checks saved evidence, not the experiment's scientific validity or a new
model replication. The literal authored fixture supplies the scoring key.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

ARCHIVES = {
    'pilot': ('ZERO_MEMORY_CPU_RAW_20260924.zip', 'c244093931b39b1b8082576b7961b87a5fd926439678b325ee25e9a9cbe864a9'),
    'order': ('ZERO_MEMORY_ORDER_RAW_20260924.zip', 'e85d77194332280346d2e87b4a491e0a6bed5da902caea9a9c4167f1c889dee9'),
}
VIEWS = ('chronology', 'correct_edges', 'reversed_edges')
BASE_SHA = '9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4'
ORDER_SHA = '559369a3e9c652898d6ee9f99b7951c04461fa71998988664fc02171af924a0e'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_archive(path: Path, expected_hash: str) -> dict[str, bytes]:
    require(path.stat().st_size <= 2_000_000, 'Archive exceeds the bounded input size')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash,
            'Archive hash mismatch: ' + path.name)
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(infos) <= 12 and len(set(names)) == len(names), 'Duplicate/excess ZIP entries')
        require(sum(i.file_size for i in infos) <= 2_000_000, 'Expanded ZIP too large')
        require(all(not n.startswith('/') and '..' not in n.split('/') for n in names), 'Unsafe member name')
        return {n: z.read(n) for n in names}


def literals(script: bytes) -> dict:
    """Read assignments as data; never import or exec the archived script."""
    require(hashlib.sha256(script).hexdigest() == BASE_SHA, 'Original script mismatch')
    result = {}
    for node in ast.parse(script).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'CASES', 'SYSTEM', 'MODEL', 'REVISION'}:
                    result[target.id] = ast.literal_eval(node.value)
    require(set(result) == {'CASES', 'SYSTEM', 'MODEL', 'REVISION'}, 'Missing fixture literals')
    return result


def check_rows(rows: list[dict], cases: list[dict], system: str, kind: str) -> dict:
    by_id = {case['id']: case for case in cases}
    require(len(by_id) == 8, 'Expected eight authored cases')
    perms = tuple(itertools.permutations(range(3))) if kind == 'order' else ((0, 1, 2),)
    expected_grid = {(cid, view, p) for cid in by_id for view in VIEWS for p in perms}
    require(len(rows) == len(expected_grid), 'Wrong row count')
    require(sorted(r['ordinal'] for r in rows) == list(range(len(rows))), 'Ordinal coverage error')
    seen = set()
    indexed = {}
    masses = []
    for row in rows:
        p = tuple(row['permutation']) if kind == 'order' else (0, 1, 2)
        key = (row['case'], row['view'], p)
        require(key in expected_grid and key not in seen, 'Duplicate or unexpected experiment cell')
        seen.add(key)
        case = by_id[row['case']]
        values = row['choice_logits']
        require(len(values) == 3 and all(math.isfinite(x) for x in values), 'Invalid logits')
        chosen = max(range(3), key=lambda j: values[j])
        label = 'ABC'[chosen]
        semantic = p[chosen]
        require(row['messages'][0] == {'role': 'system', 'content': system}, 'System prompt changed')
        require(row['choice_ids'] == [32, 33, 34], 'Choice-token IDs changed')
        require(row['correct'] == (semantic == case['gold']), 'Stored correctness mismatch')
        if kind == 'order':
            require(row['selected_label'] == label and row['selected_semantic_id'] == semantic, 'Choice mapping mismatch')
            require(row['selected_answer'] == case['answers'][semantic], 'Answer text mismatch')
            require(row['gold_semantic_id'] == case['gold'], 'Gold mapping mismatch')
            require(row['expected_label'] == 'ABC'[p.index(case['gold'])], 'Gold label mismatch')
        else:
            require(row['selected'] == label and row['expected'] == 'ABC'[case['gold']], 'Pilot label mismatch')
        exp_values = [math.exp(v - max(values)) for v in values]
        conditional = [v / sum(exp_values) for v in exp_values]
        require(max(abs(a - b) for a, b in zip(conditional, row['conditional_choice_probabilities'])) < 2e-6,
                'Conditional probabilities disagree with logits')
        mass = sum(math.exp(x) for x in row['choice_logprobs_full_vocab'])
        require(abs(mass - row['choice_probability_mass']) < 2e-6 and 0 < mass <= 1.000002,
                'Recorded option probability mass inconsistent')
        masses.append(mass)
        indexed[key] = (semantic, row)
    require(seen == expected_grid, 'Missing experiment cells')
    summary = {}
    for view in VIEWS:
        subset = [r for r in rows if r['view'] == view]
        groups = [[indexed[(cid, view, p)][0] for p in perms] for cid in by_id]
        summary[view] = {
            'correct': sum(r['correct'] for r in subset), 'total': len(subset),
            'cases_changing_across_orders': sum(len(set(g)) > 1 for g in groups),
            'cases_correct_in_every_order': sum(all(x == by_id[cid]['gold'] for x in g)
                for cid, g in zip(by_id, groups)),
        }
    recorded_top_matches = sum(r['unconstrained_next_token'] ==
        (r['selected_label'] if kind == 'order' else r['selected']) for r in rows)
    return {'summary': summary, 'probability_mass': {'min': min(masses), 'median': statistics.median(masses),
            'max': max(masses)}, 'recorded_full_vocabulary_top1_matches': recorded_top_matches,
            'rows': len(rows)}


def verify(folder: Path) -> dict:
    data = {kind: read_archive(folder / name, sha) for kind, (name, sha) in ARCHIVES.items()}
    require(data['pilot']['pilot.py'] == data['order']['pilot.py'], 'Different base scripts')
    require(hashlib.sha256(data['order']['option_order.py']).hexdigest() == ORDER_SHA, 'Diagnostic script mismatch')
    fixture = literals(data['pilot']['pilot.py'])
    rows = {kind: [json.loads(line) for line in archive['inference/raw.jsonl'].decode('utf-8').splitlines()]
            for kind, archive in data.items()}
    result = {kind: check_rows(rs, fixture['CASES'], fixture['SYSTEM'], kind) for kind, rs in rows.items()}
    lookup = {(r['case'], r['view']): r for r in rows['pilot']}
    original_order = [r for r in rows['order'] if r['permutation'] == [0, 1, 2]]
    max_difference = 0.0
    for row in original_order:
        old = lookup[(row['case'], row['view'])]
        for field in ('messages', 'rendered_prompt', 'input_ids_sha256', 'input_tokens'):
            require(row[field] == old[field], 'Original input changed: ' + field)
        require(row['selected_label'] == old['selected'], 'Original-order choice changed')
        max_difference = max(max_difference, *(abs(a-b) for a,b in zip(row['choice_logits'], old['choice_logits'])))
    pairs = {(r['case'], tuple(r['permutation']), r['view']): r['selected_semantic_id'] for r in rows['order']}
    correct_reversed_agreements = sum(pairs[(c['id'], p, 'correct_edges')] == pairs[(c['id'], p, 'reversed_edges')]
        for c in fixture['CASES'] for p in itertools.permutations(range(3)))
    result.update(status='SAVED_EVIDENCE_RECALCULATED', model=fixture['MODEL'], revision=fixture['REVISION'],
        authored_case_count=8, recorded_forward_passes=168, new_forward_passes=0,
        original_order_comparisons=len(original_order), max_original_order_logit_difference=max_difference,
        correct_reversed_matched_choices=correct_reversed_agreements,
        scoring_key_source='literal authored CASES, not an independent judgment of the gold labels',
        system_prompt=fixture['SYSTEM'],
        interpretation_limit='Equal correct/reversed choices cannot establish inability to read relations: the system prioritizes the original statements over optional imperfect metadata. Both conditions also contain the full short transcript.',
        scope='Offline author-side bookkeeping audit of saved records; not a new model run, external replication, or proof of long-term memory improvement.')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.dir), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print('VERIFICATION_FAILED: ' + str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
