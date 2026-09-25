"""Secondary descriptive decomposition; not a separate model experiment."""
import argparse
from collections import defaultdict, Counter
import json
from pathlib import Path


def analyze(rows):
    base = ('scenario', 'wording', 'user_state', 'assistant_state')
    order_groups, rename_groups = defaultdict(list), defaultdict(list)
    for row in rows:
        condition = tuple(row[k] for k in base)
        semantic_order = tuple(row['label_semantics'][letter] for letter in row['display_order'])
        order_groups[(condition, row['mapping'])].append(row)
        rename_groups[(condition, semantic_order)].append(row)
    result = {'status': 'secondary descriptive analysis, not separately preregistered primary outcome',
              'source_rows': len(rows), 'model_calls': 0}
    for name, groups in [('display_order_only', order_groups), ('label_names_only', rename_groups)]:
        assert len(groups) == 96 and all(len(values) == 3 for values in groups.values())
        result[name] = {'groups': len(groups), 'variants_per_group': 3,
                        'groups_with_semantic_choice_changes': sum(len({r['prediction'] for r in g}) > 1 for g in groups.values()),
                        'mean_within_group_margin_range': sum(max(r['margin'] for r in g)-min(r['margin'] for r in g) for g in groups.values())/len(groups)}
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rows',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=analyze([json.loads(line) for line in a.rows.read_text().splitlines()])
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
