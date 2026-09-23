"""Frozen diagnostic v1: exhaust all six option orders on the prior eight cases.

Question: is the first memory pilot's forced-choice result sensitive to the
answer-content/label arrangement? This is a diagnostic of reused development
items, NOT a held-out memory study or an attempt to select the best arrangement.

Freeze before inference: unchanged prior model/weights/system/cases/three views;
all 8 x 3 x 6 = 144 forward passes, no sampling, two CPU threads, one run per
cell. Only the ordering of answer contents changes. Original semantic answer
IDs, not letters, define correctness and cross-order consistency. All errors,
raw prompts, logits, scores, and orders are retained. No answer-based retries.

Primary descriptive outcome: cases whose semantic choice changes across orders
in each view. Secondary: all-order accuracy, per-global-order accuracy, and
casewise consistency/correctness. The independent content unit remains eight
cases, not 144 observations. No p-values, population estimate, or causal memory
benefit is claimed. Failure or no order sensitivity is a valid outcome.

Prior work, not a novelty claim: Pezeshkpour & Hruschka arXiv:2308.11483;
Gupta et al. arXiv:2406.19470. This experiment does not replicate their datasets.
Authored by Zero (ChatGPT) for Youngseok Oh / YS-OH-CORE.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import random
import resource
import socket
import sys
import time

BASE_SHA = '9f22d6f753eceef2847be49076fa6ae8f60a0e967ed48a8e631706f84f4514c4'
WEIGHTS_SHA = 'fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe'
PERMS = tuple(permutations(range(3)))
EXPECTED_PRIOR = {'permission_cancel': 1, 'permission_restore': 1,
 'suggestion_rejected': 0, 'suggestion_adopted': 0, 'temporary_step': 1,
 'goal_replaced': 2, 'past_preference_unknown': 1, 'past_preference_confirmed': 1}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_base(path: Path):
    assert digest(path.read_bytes()) == BASE_SHA, 'Prior script hash mismatch'
    spec = importlib.util.spec_from_file_location('frozen_memory_pilot', path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    return base

def prepare(base, case: dict, view: str, perm: tuple) -> list[dict]:
    changed = deepcopy(case)
    changed['answers'] = [case['answers'][i] for i in perm]
    # Gold is never included in a prompt; the original constructor ignores it.
    changed['gold'] = perm.index(case['gold'])
    return base.prompts(changed, view)

def selftest(base) -> None:
    assert len(base.CASES) == 8 and len(base.VIEWS) == 3 and len(PERMS) == 6
    for case in base.CASES:
        original = deepcopy(case)
        assert len(set(case['answers'])) == 3
        assert Counter(p.index(case['gold']) for p in PERMS) == {0: 2, 1: 2, 2: 2}
        for view in base.VIEWS:
            for perm in PERMS:
                messages = prepare(base, case, view, perm)
                assert messages[0]['content'] == base.SYSTEM
                prefix = messages[1]['content'].split('\n\nQuestion:', 1)[0]
                assert prefix == base.prompts(case, view)[1]['content'].split('\n\nQuestion:', 1)[0]
                assert case['question'] in messages[1]['content']
                for j, semantic_id in enumerate(perm):
                    assert f'{"ABC"[j]}. {case["answers"][semantic_id]}' in messages[1]['content']
                if perm == (0, 1, 2):
                    assert messages == base.prompts(case, view)
        assert case == original, 'Fixture mutation'
    print('ORDER_FIXTURE_SELFTEST_OK', flush=True)

def summarize(rows: list[dict], base) -> dict:
    result = {}
    for view in base.VIEWS:
        part = [r for r in rows if r['view'] == view]
        per_case = {}
        for case in base.CASES:
            subset = sorted([r for r in part if r['case'] == case['id']], key=lambda r: r['permutation'])
            if not subset:
                continue
            choices = [r['selected_semantic_id'] for r in subset]
            per_case[case['id']] = {
                'permutations_completed': len(subset),
                'semantic_choices_in_lexicographic_order': choices,
                'gold_semantic_id': case['gold'],
                'correct': sum(r['correct'] for r in subset),
                'choice_changed_across_orders': len(set(choices)) > 1,
                'all_six_correct': len(subset) == 6 and all(r['correct'] for r in subset),
            }
        result[view] = {
            'correct': sum(r['correct'] for r in part), 'total': len(part),
            'changed_case_count': sum(c['choice_changed_across_orders'] for c in per_case.values()),
            'all_six_correct_cases': sum(c['all_six_correct'] for c in per_case.values()),
            'selected_label_counts': dict(Counter(r['selected_label'] for r in part)),
            'per_global_order': {''.join(map(str, p)): {
                'correct': sum(r['correct'] for r in part if r['permutation'] == list(p)),
                'total': sum(r['permutation'] == list(p) for r in part)} for p in PERMS},
            'per_case': per_case,
        }
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    base = load_base(args.base)
    selftest(base)
    if args.selftest:
        return 0
    if args.out is None:
        parser.error('--out is required for inference')
    args.out.mkdir(parents=True, exist_ok=False)
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    started = time.monotonic()
    rows: list[dict] = []
    report = {
        'protocol': 'answer-order-diagnostic-v1', 'planned_inferences': 144,
        'model': base.MODEL, 'revision': base.REVISION,
        'script_sha256': digest(Path(__file__).read_bytes()), 'base_script_sha256': BASE_SHA,
        'fixture_sha256': digest(json.dumps(base.CASES, sort_keys=True).encode()),
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'measurement': 'next-token A/B/C logits, semantic answers mapped back after permutation',
        'cpu_threads': 2, 'dtype': 'float32', 'sampling': False, 'gpu_used': False,
        'limits': ['reused eight authored development cases', 'one small model',
                   'no held-out evaluation', 'no free-form response or actual action',
                   'chronology shorter than edge views', 'oracle edge annotations',
                   'within-case repeated observations not independent cases',
                   'no independent replication or personal-memory claim'],
        'versions': {p: importlib.metadata.version(p) for p in
                     ['torch', 'transformers', 'huggingface-hub', 'tokenizers', 'safetensors']},
        'success': False,
    }
    prior_socket = (socket.socket.connect, socket.socket.connect_ex)
    try:
        path = Path(snapshot_download(base.MODEL, revision=base.REVISION, token=False, max_workers=2,
            allow_patterns=['config.json', 'generation_config.json', 'tokenizer.json',
              'tokenizer_config.json', 'vocab.json', 'merges.txt', 'model.safetensors', 'LICENSE']))
        report['weights_sha256'] = digest((path / 'model.safetensors').read_bytes())
        assert report['weights_sha256'] == WEIGHTS_SHA, 'Weight mismatch with first pilot'
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, torch_dtype=torch.float32, attn_implementation='eager').eval()
        assert next(model.parameters()).device.type == 'cpu'
        choices = [tokenizer.encode(letter, add_special_tokens=False) for letter in 'ABC']
        assert all(len(x) == 1 for x in choices)
        ids = [x[0] for x in choices]
        def blocked(*args, **kwargs):
            raise RuntimeError('Inference requires no network')
        socket.socket.connect = socket.socket.connect_ex = blocked
        order = [(i, view, list(p)) for i in range(8) for view in base.VIEWS for p in PERMS]
        random.Random(24092401).shuffle(order)
        report['execution_order'] = order
        infer_start = time.monotonic()
        with (args.out / 'raw.jsonl').open('w', encoding='utf-8') as raw:
            for ordinal, (i, view, p) in enumerate(order):
                case = base.CASES[i]
                messages = prepare(base, case, view, tuple(p))
                rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(rendered, return_tensors='pt')
                assert inputs.input_ids.shape[1] <= 768
                start = time.monotonic()
                with torch.inference_mode():
                    output = model(**inputs, use_cache=False)
                    logits = output.logits[0, -1].float()
                    logprobs = torch.log_softmax(logits, dim=-1)
                    values = logits[ids]
                    chosen = int(values.argmax())
                    semantic = p[chosen]
                    row = {'ordinal': ordinal, 'case': case['id'], 'view': view, 'permutation': p,
                        'messages': messages, 'rendered_prompt': rendered,
                        'input_ids_sha256': digest(json.dumps(inputs.input_ids[0].tolist()).encode()),
                        'input_tokens': int(inputs.input_ids.shape[1]), 'choice_ids': ids,
                        'choice_logits': values.tolist(), 'choice_logprobs_full_vocab': logprobs[ids].tolist(),
                        'conditional_choice_probabilities': torch.softmax(values, dim=-1).tolist(),
                        'choice_probability_mass': float(logprobs[ids].exp().sum()),
                        'unconstrained_next_token': tokenizer.decode([int(logits.argmax())]),
                        'selected_label': 'ABC'[chosen], 'selected_semantic_id': semantic,
                        'selected_answer': case['answers'][semantic], 'gold_semantic_id': case['gold'],
                        'expected_label': 'ABC'[p.index(case['gold'])], 'correct': semantic == case['gold'],
                        'elapsed_seconds': round(time.monotonic() - start, 3)}
                    del output, logits, logprobs, values
                rows.append(row)
                raw.write(json.dumps(row, ensure_ascii=False) + '\n')
                raw.flush()
                print('ORDER_ROW ' + json.dumps({k: row[k] for k in
                    ['ordinal', 'case', 'view', 'permutation', 'selected_semantic_id', 'correct']}), flush=True)
        report['inference_seconds'] = round(time.monotonic() - infer_start, 3)
        report['original_order_reproduced_count'] = sum(
            r['selected_semantic_id'] == EXPECTED_PRIOR[r['case']] for r in rows if r['permutation'] == [0, 1, 2])
        report['original_order_comparisons'] = 24
        report['success'] = len(rows) == 144
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:2000]}
    finally:
        socket.socket.connect, socket.socket.connect_ex = prior_socket
        report['completed_inferences'] = len(rows)
        report['summary'] = summarize(rows, base)
        report['total_seconds'] = round(time.monotonic() - started, 3)
        report['max_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('ORDER_SUMMARY ' + json.dumps({k: v for k, v in report.items() if k != 'execution_order'}), flush=True)
    return 0 if report['success'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
