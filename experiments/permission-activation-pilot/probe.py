"""Permission-pair activation interchange: exploratory instrumentation pilot.

One reused fictional prompt pair, six answer orders, three prespecified decoder
block outputs. Full final-position residual replacement is coarse, not a claim
of a memory feature, unique circuit, consciousness, or general safety behavior.
No fitting, model self-report, action execution, or response-based retries.
Question direction: Youngseok Oh. Implementation and analysis: Zero (AI).
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import random
import socket
import statistics
import time

BASE_SHA = '9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4'
WEIGHTS_SHA = 'fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe'
CASES = ('permission_cancel', 'permission_restore')
LAYERS = (0, 11, 23)  # zero-based, selected before this experiment
ORDERS = tuple(permutations(range(3)))
TOLERANCE = 1e-4
MIN_MARGIN_GAP = 0.25


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_base(path: Path):
    if sha_file(path) != BASE_SHA:
        raise ValueError('Prior fixture script identity mismatch')
    spec = importlib.util.spec_from_file_location('frozen_pilot_fixture', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Cannot load pinned fixture definitions')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(base) -> dict:
    result = {}
    for cid in CASES:
        case = next(c for c in base.CASES if c['id'] == cid)
        for order in ORDERS:
            copy = deepcopy(case)
            copy['answers'] = [case['answers'][i] for i in order]
            key = cid + '_' + ''.join(map(str, order))
            result[key] = {'case': cid, 'order': list(order), 'gold': case['gold'],
                           'messages': base.prompts(copy, 'chronology')}
    assert len(result) == 12
    assert next(c for c in base.CASES if c['id'] == CASES[0])['answers'] == next(
        c for c in base.CASES if c['id'] == CASES[1])['answers']
    return result


def patch_output(output, donor, position: int):
    # Clone before replacement: never modify cached or upstream tensors in place.
    if not isinstance(output, tuple) or not output:
        raise TypeError('Expected pinned Qwen2 decoder tuple output')
    states = output[0].clone()
    if states.shape[0] != 1 or donor.shape != states[:, position, :].shape:
        raise ValueError('Unexpected patch dimensions')
    states[:, position, :] = donor
    return (states,) + output[1:]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--plan-only', action='store_true')
    args = p.parse_args()
    base = read_base(args.base)
    prompts = prepare(base)
    if args.plan_only:
        print(json.dumps({'baseline':12, 'donor':36, 'self_control':36,
                          'wrong_position_control':12, 'total_forward_passes':96,
                          'layers':LAYERS, 'cases':CASES}))
        return 0
    args.out.mkdir(parents=True, exist_ok=False)
    report = {'protocol':'permission-residual-interchange-v1', 'success':False,
              'started_utc':datetime.now(timezone.utc).isoformat(),
              'model':base.MODEL, 'revision':base.REVISION, 'layers_zero_based':list(LAYERS),
              'planned_forward_passes':96, 'base_sha256':BASE_SHA,
              'runner_sha256':sha_file(Path(__file__)), 'sampling':False, 'training':False,
              'fixture_unit':'one reused fictional cancel/restore pair, not 12 independent cases',
              'completed_forward_passes':0, 'network_attempts_during_inference':0}
    raw_rows = []
    started = time.monotonic()
    raw_file = (args.out/'raw.jsonl').open('w', encoding='utf-8')
    prior_socket = (socket.socket.connect, socket.socket.connect_ex)
    try:
        import torch
        from safetensors.torch import save_file
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        report['versions'] = {x:importlib.metadata.version(x) for x in
            ['torch','transformers','huggingface-hub','tokenizers','safetensors']}
        cache_path = Path(snapshot_download(base.MODEL, revision=base.REVISION, token=False,
            max_workers=2, allow_patterns=['config.json','generation_config.json','tokenizer.json',
              'tokenizer_config.json','vocab.json','merges.txt','model.safetensors','LICENSE']))
        assert sha_file(cache_path/'model.safetensors') == WEIGHTS_SHA
        report['weights_sha256'] = WEIGHTS_SHA
        tokenizer = AutoTokenizer.from_pretrained(cache_path, local_files_only=True, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(cache_path, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, torch_dtype=torch.float32, attn_implementation='eager').eval()
        assert next(model.parameters()).device.type == 'cpu'
        assert len(model.model.layers) == 24 and model.config.hidden_size == 896
        model.requires_grad_(False)
        parameter_versions = tuple(x._version for x in model.parameters())
        choices = [tokenizer.encode(x, add_special_tokens=False) for x in 'ABC']
        assert all(len(x) == 1 for x in choices)
        choice_ids = [x[0] for x in choices]
        inputs = {}
        for key, fixture in prompts.items():
            rendered = tokenizer.apply_chat_template(fixture['messages'], tokenize=False, add_generation_prompt=True)
            encoded = tokenizer(rendered, return_tensors='pt')
            assert 2 < encoded.input_ids.shape[1] <= 768
            inputs[key] = encoded
            fixture.update(rendered_prompt=rendered, input_ids=encoded.input_ids[0].tolist(),
                           tokens=int(encoded.input_ids.shape[1]))
        (args.out/'prompts.json').write_text(json.dumps(prompts, indent=2)+'\n', encoding='utf-8')
        for filename in ['config.json','tokenizer_config.json','LICENSE']:
            source = cache_path/filename
            if source.exists():
                (args.out/('model_'+filename)).write_bytes(source.read_bytes())
        def deny(*_args, **_kwargs):
            report['network_attempts_during_inference'] += 1
            raise RuntimeError('Network is not required during this inference')
        socket.socket.connect = socket.socket.connect_ex = deny
        baseline_logits, vectors, baseline_stats = {}, {}, {}
        def stats(logits, key):
            order = prompts[key]['order']
            values = logits[choice_ids]
            chosen = int(values.argmax())
            # Same semantic contrast under every A/B/C arrangement.
            private_minus_publish = float(values[order.index(0)] - values[order.index(1)])
            return {'choice_logits':values.tolist(), 'conditional_probs':torch.softmax(values,dim=0).tolist(),
                    'selected_semantic_id':order[chosen], 'correct':order[chosen] == prompts[key]['gold'],
                    'private_minus_publish':private_minus_publish,
                    'abc_probability_mass':float(torch.softmax(logits,dim=0)[choice_ids].sum()),
                    'unconstrained_token':tokenizer.decode([int(logits.argmax())])}
        def log(row):
            raw_rows.append(row)
            raw_file.write(json.dumps(row)+'\n'); raw_file.flush()
            print('ACTIVATION_ROW '+json.dumps(row), flush=True)
        def forward(key, handles):
            try:
                with torch.inference_mode():
                    result = model(**inputs[key], use_cache=False)
                    values = result.logits[0,-1].detach().float().clone()
                    del result
                report['completed_forward_passes'] += 1
                return values
            finally:
                for handle in handles:
                    handle.remove()
        inference_start = time.monotonic()
        for key in sorted(prompts):
            handles = []
            hits = {layer:0 for layer in LAYERS}
            for layer in LAYERS:
                def capture(_module, _inputs, output, layer=layer, key=key):
                    assert isinstance(output,tuple)
                    hits[layer] += 1
                    for pos in (-1,-2):
                        vectors[f'{key}.L{layer}.P{pos}'] = output[0][:,pos,:].detach().clone().contiguous()
                handles.append(model.model.layers[layer].register_forward_hook(capture))
            logits = forward(key, handles)
            assert all(v == 1 for v in hits.values())
            baseline_logits[key] = logits
            baseline_stats[key] = stats(logits,key)
            log({'kind':'baseline','target':key,**baseline_stats[key]})
        # Artifacts contain only synthetic-prompt activations and outputs, not model weights.
        save_file(vectors, str(args.out/'baseline_activations.safetensors'))
        save_file(baseline_logits, str(args.out/'baseline_logits.safetensors'))
        schedule = []
        for key in sorted(prompts):
            other_case = CASES[1] if prompts[key]['case'] == CASES[0] else CASES[0]
            other = other_case + '_' + ''.join(map(str,prompts[key]['order']))
            for layer in LAYERS:
                schedule += [('donor',key,other,layer,-1), ('self_control',key,key,layer,-1)]
            schedule += [('wrong_position_control',key,other,23,-2)]
        random.Random(20260925).shuffle(schedule)
        report['intervention_schedule'] = schedule
        for kind,key,donor_key,layer,pos in schedule:
            calls = [0]
            replacement = vectors[f'{donor_key}.L{layer}.P{pos}']
            def intervene(_module,_inputs,output):
                calls[0] += 1
                return patch_output(output,replacement,pos)
            handle = model.model.layers[layer].register_forward_hook(intervene)
            logits = forward(key,[handle])
            assert calls[0] == 1
            observed = stats(logits,key)
            target_diff = float((logits-baseline_logits[key]).abs().max())
            donor_diff = float((logits-baseline_logits[donor_key]).abs().max())
            row = {'kind':kind,'target':key,'donor':donor_key,'layer_zero_based':layer,'position':pos,
                   'max_full_vocab_diff_from_target':target_diff,
                   'max_full_vocab_diff_from_donor':donor_diff,**observed}
            baseline_margin = baseline_stats[key]['private_minus_publish']
            donor_gap = baseline_stats[donor_key]['private_minus_publish'] - baseline_margin
            effect = observed['private_minus_publish'] - baseline_margin
            row.update(donor_margin_gap=donor_gap, intervention_margin_shift=effect,
                       gap_fraction=effect/donor_gap if abs(donor_gap)>=MIN_MARGIN_GAP else None)
            log(row)
            if kind in ('self_control','wrong_position_control'):
                assert target_diff <= TOLERANCE, (kind,key,layer,target_diff)
            if kind == 'donor' and layer == 23:
                # Architecture-level positive control, NOT discovery of a decision circuit.
                assert donor_diff <= TOLERANCE, (key,donor_diff)
        assert report['completed_forward_passes'] == 96
        assert tuple(x._version for x in model.parameters()) == parameter_versions
        assert report['network_attempts_during_inference'] == 0
        assert all(len(m._forward_hooks)==0 for m in model.model.layers)
        summary = {}
        for layer in LAYERS:
            rows = [r for r in raw_rows if r['kind']=='donor' and r['layer_zero_based']==layer]
            fractions = [r['gap_fraction'] for r in rows if r['gap_fraction'] is not None]
            summary[str(layer)] = {'paired_directions':len(rows),
                'changed_semantic_choices':sum(r['selected_semantic_id'] != baseline_stats[r['target']]['selected_semantic_id'] for r in rows),
                'fraction_eligible':len(fractions),'median_gap_fraction':statistics.median(fractions) if fractions else None,
                'gap_fractions':fractions,
                'note':'last-block output replacement is a positive control' if layer==23 else 'coarse intervention, not unique-circuit localization'}
        report.update(success=True, inference_seconds=round(time.monotonic()-inference_start,3),
            baseline=baseline_stats, interventions=summary,
            self_control_max_diff=max(r['max_full_vocab_diff_from_target'] for r in raw_rows if r['kind']=='self_control'),
            wrong_position_max_diff=max(r['max_full_vocab_diff_from_target'] for r in raw_rows if r['kind']=='wrong_position_control'),
            positive_control_max_diff=max(r['max_full_vocab_diff_from_donor'] for r in raw_rows if r['kind']=='donor' and r['layer_zero_based']==23))
    except Exception as exc:
        report['error'] = {'type':type(exc).__name__,'message':str(exc)[:2000]}
    finally:
        socket.socket.connect,socket.socket.connect_ex = prior_socket
        raw_file.close()
        report.update(ended_utc=datetime.now(timezone.utc).isoformat(),total_seconds=round(time.monotonic()-started,3),
                      rows_written=len(raw_rows))
        (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
        print('ACTIVATION_REPORT '+json.dumps({k:v for k,v in report.items() if k!='intervention_schedule'}),flush=True)
    return 0 if report['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
