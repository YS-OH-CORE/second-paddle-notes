"""Coarse residual interchange on the prior matched one-token cue design.

Youngseok Oh x Zero, AI collaboration partners. Deterministic CPU execution.
No third-party issue posting, training, real user history or hosted model API.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import statistics
import sys

LAYERS = (0, 11, 23)
MODES = ('cue', 'last', 'prefix', 'self')
BASE_SHA = '30a76e49011abb1dcb55df8be0ef6d43279541316b3cbef2e5fb6855490f6a63'
TOL = 1e-4


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def load_design(path):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == BASE_SHA
    spec = importlib.util.spec_from_file_location('prior_design', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [r for r in module.dataset() if r['wording'] == 0 and r['display'] == 0
            and r['mapping'] in (0, 3, 4)]
    assert len(rows) == 24
    return module, rows


def make_plans(rows):
    dims = ('scenario', 'wording', 'user_state', 'assistant_state', 'mapping', 'display')
    lookup = {tuple(r[k] for k in dims): i for i, r in enumerate(rows)}
    plans = []
    for field in ('user_state', 'assistant_state'):
        for target, row in enumerate(rows):
            donor_key = tuple(('public' if row[k] == 'private' else 'private')
                              if k == field else row[k] for k in dims)
            donor = lookup[donor_key]
            for layer, mode in [(l, m) for l in LAYERS for m in MODES] + [(11, 'suffix')]:
                plans.append({'id': f'{field}:{row["id"]}:L{layer}:{mode}',
                              'field': field, 'target': target, 'donor': donor,
                              'layer': layer, 'mode': mode})
    assert len(plans) == 624 and len({p['id'] for p in plans}) == 624
    return plans


def summarize(rows):
    base = {r['target']: r for r in rows if r['kind'] == 'baseline'}
    groups = defaultdict(list)
    for r in rows:
        if r['kind'] != 'baseline':
            groups[(r['field'], r['layer'], r['mode'])].append(r)
    result = []
    for (field, layer, mode), group in sorted(groups.items()):
        shifts, fractions = [], []
        for row in group:
            recipient, donor = base[row['target']], base[row['donor']]
            gap = donor['margin'] - recipient['margin']
            change = row['margin'] - recipient['margin']
            shifts.append(change)
            if abs(gap) >= 0.25:
                fractions.append(change / gap)
        unequal = [r for r in group if base[r['target']]['prediction'] != base[r['donor']]['prediction']]
        result.append({'field': field, 'layer': layer, 'mode': mode, 'n': len(group),
                       'choice_flips': sum(r['prediction'] != base[r['target']]['prediction'] for r in group),
                       'different_baseline_choices': len(unequal),
                       'adopts_donor_when_baselines_differ': sum(r['prediction'] == base[r['donor']]['prediction'] for r in unequal),
                       'mean_margin_shift': statistics.mean(shifts),
                       'max_abs_margin_shift': max(map(abs, shifts)),
                       'eligible_gap_rows': len(fractions),
                       'median_gap_fraction': statistics.median(fractions) if fractions else None,
                       'max_full_vocab_target_deviation': max(r['target_max_deviation'] for r in group),
                       'max_full_vocab_donor_deviation': max(r['donor_max_deviation'] for r in group)})
    return {'baselines': len(base), 'interventions': len(rows) - len(base),
            'baseline_correct': sum(r['correct'] for r in base.values()),
            'all_top_tokens_are_labels': all(r['top_is_label'] for r in rows),
            'min_label_probability_mass': min(r['label_mass'] for r in rows), 'groups': result}


def audit(root):
    import numpy as np
    rows = [json.loads(s) for s in (root / 'rows.jsonl').read_text().splitlines()]
    specs = json.loads((root / 'inputs.json').read_text())
    plans = json.loads((root / 'plans.json').read_text())
    assert plans == make_plans(specs)
    assert len(rows) == 648 and len({r['id'] for r in rows}) == 648
    indexed = {r['id']: r for r in rows}
    assert {r['id'] for r in rows if r['kind'] != 'baseline'} == {p['id'] for p in plans}
    assert {r['target'] for r in rows if r['kind'] == 'baseline'} == set(range(24))
    arrays = np.load(root / 'readout.npz', allow_pickle=False)
    assert arrays['normalized_last'].shape == (648, 896)
    expected = arrays['normalized_last'].astype('float64') @ arrays['head_rows'].astype('float64').T
    readout_error = 0.0
    for r in rows:
        values = [r['label_logits'][k] for k in ('A', 'B', 'C')]
        error = float(np.max(np.abs(expected[r['array_index']] - values)))
        readout_error = max(readout_error, error)
        assert error < TOL, (r['id'], error)
        mapping = specs[r['target']]['label_semantics']
        winner = max(r['label_logits'], key=r['label_logits'].get)
        assert r['prediction'] == mapping[winner]
        labels = {v: k for k, v in mapping.items()}
        assert r['margin'] == r['label_logits'][labels['private']] - r['label_logits'][labels['public']]
        assert r['correct'] == (r['prediction'] == specs[r['target']]['user_state'])
        if r['kind'] != 'baseline':
            assert all(r[k] == next(p for p in plans if p['id'] == r['id'])[k]
                       for k in ('field', 'target', 'donor', 'layer', 'mode'))
            t, d = specs[r['target']]['input_ids'], specs[r['donor']]['input_ids']
            assert len(t) == len(d) and [i for i, (a, b) in enumerate(zip(t, d)) if a != b] == [r['cue_position']]
            assert r['hook_calls'] == 1 and r['copied_max_error'] == 0
            if r['mode'] in ('prefix', 'self') or (r['layer'] == 23 and r['mode'] == 'cue'):
                assert r['target_max_deviation'] < TOL
            if r['mode'] == 'suffix' or (r['layer'] == 23 and r['mode'] == 'last'):
                assert r['donor_max_deviation'] < TOL
    assert summarize(rows) == json.loads((root / 'SUMMARY.json').read_text())
    full = np.load(root / 'sample_full_logits.npz', allow_pickle=False)
    label_ids = json.loads((root / 'RUN.json').read_text())['label_token_ids']
    for index in full.files:
        row = rows[int(index)]
        assert row['array_index'] == int(index)
        vector = full[index]
        assert vector.shape == (151936,)
        assert all(float(vector[token]) == row['label_logits'][letter] for letter, token in label_ids.items())
        assert int(vector.argmax()) == row['top_token']
        v = vector.astype('float64'); normalizer = float(v.max() + np.log(np.exp(v - v.max()).sum()))
        mass = sum(math.exp(row['label_logits'][k] - normalizer) for k in label_ids)
        assert abs(mass - row['label_mass']) < 1e-10
    result = {'rows_checked': len(rows), 'choice_logits_reconstructed_for_all_rows': True,
              'max_float64_readout_error': readout_error, 'full_vocab_rows_checked': len(full.files),
              'all_full_vocab_vectors_retained': False, 'plan_complete': True,
              'control_assertions_pass': True, 'independent_external_replication': False}
    dump(root / 'AUDIT.json', result)
    return result


def run(args):
    import importlib.metadata
    import os
    import socket
    import time
    import numpy as np
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    previous, specs = load_design(args.design)
    plans = make_plans(specs)
    root = args.out
    root.mkdir(parents=True, exist_ok=False)
    dump(root / 'plans.json', plans)
    meta = {'completed': False, 'model': previous.MODEL, 'revision': previous.REVISION,
            'started_utc': datetime.now(timezone.utc).isoformat(), 'forward_calls': 0,
            'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'run_id': os.environ.get('GITHUB_RUN_ID'), 'workflow_commit': os.environ.get('GITHUB_SHA'),
            'versions': {p: importlib.metadata.version(p) for p in
                         ('torch', 'transformers', 'huggingface-hub', 'tokenizers', 'safetensors', 'numpy')}}
    try:
        location = Path(snapshot_download(previous.MODEL, revision=previous.REVISION, token=False,
                        max_workers=2, allow_patterns=['*.json', '*.txt', '*.safetensors', 'LICENSE', 'README.md']))
        with (location / 'model.safetensors').open('rb') as f:
            meta['weights_sha256'] = hashlib.file_digest(f, 'sha256').hexdigest()
        assert meta['weights_sha256'] == previous.WEIGHTS_SHA256
        tokenizer = AutoTokenizer.from_pretrained(location, local_files_only=True, trust_remote_code=False)
        for s in specs:
            s['input_ids'] = tokenizer.apply_chat_template(s['messages'], tokenize=True, add_generation_prompt=True)
        for p in plans:
            a, b = specs[p['target']]['input_ids'], specs[p['donor']]['input_ids']
            assert len(a) == len(b)
            diffs = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
            assert len(diffs) == 1 and 0 < diffs[0] < len(a) - 1
        dump(root / 'inputs.json', specs)
        label_ids = {k: tokenizer.encode(k, add_special_tokens=False) for k in ('A', 'B', 'C')}
        assert all(len(v) == 1 for v in label_ids.values())
        label_ids = {k: v[0] for k, v in label_ids.items()}
        meta['label_token_ids'] = label_ids
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        torch.manual_seed(0); torch.use_deterministic_algorithms(True)
        model = AutoModelForCausalLM.from_pretrained(location, local_files_only=True, trust_remote_code=False,
                            torch_dtype=torch.float32, attn_implementation='eager').eval()
        assert len(model.model.layers) == 24 and model.config.hidden_size == 896
        network = []
        def deny(*a, **kw):
            network.append('socket_or_dns'); raise RuntimeError('Network blocked during inference')
        socket.socket.connect = deny; socket.socket.connect_ex = deny; socket.getaddrinfo = deny
        caches, logits, records, readouts, full_vectors = {}, {}, [], [], {}
        rows_file = (root / 'rows.jsonl').open('w', encoding='utf-8')
        start = time.monotonic()

        def forward(indices, patch_plans=None, capture=False):
            assert time.monotonic() - start < 900
            handles, captured, patched_info = [], {}, []
            def norm_hook(module, inputs, output):
                captured['readout'] = output[:, -1, :].detach().cpu().numpy().copy()
            handles.append(model.model.norm.register_forward_hook(norm_hook))
            if capture:
                for layer in LAYERS:
                    def cache_hook(module, inputs, output, layer=layer):
                        captured[layer] = output[0].detach().clone()
                    handles.append(model.model.layers[layer].register_forward_hook(cache_hook))
            if patch_plans:
                layer = patch_plans[0]['layer']
                assert all(p['layer'] == layer for p in patch_plans)
                def patch_hook(module, inputs, output):
                    states = output[0].clone()
                    for j, p in enumerate(patch_plans):
                        a = specs[p['target']]['input_ids']; b = specs[p['donor']]['input_ids']
                        cue = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
                        index = slice(cue, None) if p['mode'] == 'suffix' else (
                                -1 if p['mode'] == 'last' else cue - 1 if p['mode'] == 'prefix' else cue)
                        source = p['target'] if p['mode'] == 'self' else p['donor']
                        donor = caches[(source, layer)][index]
                        states[j, index] = donor
                        copied = float((states[j, index] - donor).abs().max())
                        patched_info.append({'cue_position': cue, 'hook_calls': 1, 'copied_max_error': copied})
                    return (states,) + output[1:]
                handles.append(model.model.layers[layer].register_forward_hook(patch_hook))
            try:
                with torch.inference_mode():
                    batch = torch.tensor([specs[i]['input_ids'] for i in indices], dtype=torch.long)
                    values = model(input_ids=batch, use_cache=False, logits_to_keep=1).logits[:, -1, :].float().cpu()
                    meta['forward_calls'] += 1
            finally:
                for handle in handles: handle.remove()
            if capture:
                for j, i in enumerate(indices):
                    for layer in LAYERS: caches[(i, layer)] = captured[layer][j].clone()
            return values, captured['readout'], patched_info

        def record(vector, readout, target, plan=None, info=None):
            labels = {k: float(vector[v]) for k, v in label_ids.items()}
            semantic = {v: k for k, v in specs[target]['label_semantics'].items()}
            winner = max(labels, key=labels.get)
            norm = float(torch.logsumexp(vector.double(), dim=0))
            row = {'id': 'baseline:' + specs[target]['id'], 'kind': 'baseline', 'target': target,
                   'array_index': len(records), 'label_logits': labels,
                   'margin': labels[semantic['private']] - labels[semantic['public']],
                   'prediction': specs[target]['label_semantics'][winner],
                   'top_token': int(vector.argmax()), 'top_is_label': int(vector.argmax()) in label_ids.values(),
                   'label_mass': sum(math.exp(v - norm) for v in labels.values())}
            row['correct'] = row['prediction'] == specs[target]['user_state']
            if plan:
                row.update(plan, kind='intervention', **info,
                           target_max_deviation=float((vector - logits[target]).abs().max()),
                           donor_max_deviation=float((vector - logits[plan['donor']]).abs().max()))
                if plan['mode'] in ('prefix', 'self') or (plan['layer'] == 23 and plan['mode'] == 'cue'):
                    assert row['target_max_deviation'] < TOL, row
                if plan['mode'] == 'suffix' or (plan['layer'] == 23 and plan['mode'] == 'last'):
                    assert row['donor_max_deviation'] < TOL, row
            if plan is None or target == 0:
                full_vectors[str(len(records))] = vector.numpy().copy()
            records.append(row); readouts.append(readout)
            rows_file.write(json.dumps(row) + '\n'); rows_file.flush()

        baseline_groups = defaultdict(list)
        for i, s in enumerate(specs): baseline_groups[len(s['input_ids'])].append(i)
        with torch.inference_mode():
            for group in baseline_groups.values():
                for i in range(0, len(group), 4):
                    batch = group[i:i + 4]; values, out, _ = forward(batch, capture=True)
                    for j, idx in enumerate(batch):
                        logits[idx] = values[j].clone(); record(values[j], out[j], idx)
            grouped = defaultdict(list)
            for p in plans:
                grouped[(p['layer'], p['mode'], len(specs[p['target']]['input_ids']))].append(p)
            batches = [group[i:i + 4] for group in grouped.values() for i in range(0, len(group), 4)]
            random.Random(20260926).shuffle(batches)
            dump(root / 'execution_schedule.json', [[p['id'] for p in b] for b in batches])
            for batch in batches:
                values, out, infos = forward([p['target'] for p in batch], batch)
                assert len(infos) == len(batch)
                for j, p in enumerate(batch): record(values[j], out[j], p['target'], p, infos[j])
                if len(records) % 48 == 24:
                    print(json.dumps({'rows': len(records), 'seconds': time.monotonic() - start}), flush=True)
        rows_file.close()
        head = model.lm_head.weight.detach()[list(label_ids.values())].cpu().numpy().copy()
        np.savez_compressed(root / 'readout.npz', normalized_last=np.stack(readouts), head_rows=head)
        np.savez_compressed(root / 'sample_full_logits.npz', **full_vectors)
        # Retain actual cached post-block vectors, including the complete suffix-control donor.
        np.savez_compressed(root / 'baseline_activations.npz', **{f'{i}_{l}': v.numpy() for (i, l), v in caches.items()})
        dump(root / 'SUMMARY.json', summarize(records))
        meta.update(completed=True, rows=len(records), network_attempts=len(network),
                    elapsed_seconds=time.monotonic() - start, full_vocab_rows_retained=len(full_vectors))
        assert len(records) == 648 and meta['forward_calls'] == 162 and not network
    except Exception as exc:
        meta['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        dump(root / 'RUN.json', meta)
    print(json.dumps(audit(root)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('run', 'audit', 'prepare'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--design', type=Path)
    a = p.parse_args()
    if a.command == 'audit':
        print(json.dumps(audit(a.out)))
    elif a.command == 'prepare':
        _, rows = load_design(a.design)
        a.out.mkdir(parents=True, exist_ok=False)
        dump(a.out / 'inputs.json', rows); dump(a.out / 'plans.json', make_plans(rows))
    else:
        run(a)
