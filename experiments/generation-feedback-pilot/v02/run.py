"""Twelve preplanned continuations of v0.1 public seeds. No regenerated seed,
training, paid API, user PC, tools, hidden-state claims, or semantic retries.
"""
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import base64
import gzip
import hashlib
import json
import os
import platform
import signal
import socket
import time
from unittest.mock import patch
import observe as o

ROOT = Path(__file__).resolve().parent
MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'
NAMES = ('config.json', 'generation_config.json', 'tokenizer.json',
         'tokenizer_config.json', 'vocab.json', 'merges.txt', 'model.safetensors')
EXPECTED_WEIGHTS = 'fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe'


def emit(kind, record):
    print('V02_' + kind + ' ' + json.dumps(record, ensure_ascii=False, separators=(',', ':')), flush=True)


def stop(*_):
    raise TimeoutError('540-second inference-process ceiling')


def blocked(*_, **__):
    raise RuntimeError('No network permitted during inference')


def main():
    signal.signal(signal.SIGALRM, stop); signal.alarm(540)
    os.environ.update(HF_HUB_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_XET='1',
                      HF_HUB_DISABLE_IMPLICIT_TOKEN='1', DO_NOT_TRACK='1',
                      TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    for key in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'OPENAI_API_KEY'):
        os.environ.pop(key, None)
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('Pre-run source or seed drift')
    observed = json.loads((ROOT.parent / 'OBSERVED.json').read_text())
    seeds = {r['case']: r for r in observed['rows'] if r['stage'] == 'initial'}
    if set(seeds) != {t['id'] for t in o.task.TASKS} or len(observed['rows']) != 12:
        raise ValueError('Unexpected frozen seed inventory')
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
    torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.manual_seed(2709)
    environment = {'model': MODEL, 'revision': REVISION, 'head': os.environ['EXPECTED_HEAD'],
                   'python': platform.python_version(), 'source_manifest': manifest,
                   'packages': {p: version(p) for p in ('torch','transformers','tokenizers','huggingface-hub','safetensors','numpy')}}
    emit('START', environment)
    local = Path(snapshot_download(MODEL, revision=REVISION, allow_patterns=list(NAMES),
                 token=False, max_workers=2, local_dir=Path(os.environ['RUNNER_TEMP']) / 'v02-model'))
    total = sum((local / n).stat().st_size for n in NAMES)
    if total > 1150000000: raise ValueError('Size ceiling')
    hashes = {n: hashlib.sha256((local / n).read_bytes()).hexdigest() for n in NAMES}
    if hashes['model.safetensors'] != EXPECTED_WEIGHTS: raise ValueError('Baseline weights differ')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    tokenizer = AutoTokenizer.from_pretrained(local, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(local, local_files_only=True, trust_remote_code=False,
             use_safetensors=True, torch_dtype=torch.float32, attn_implementation='eager').eval()
    config = GenerationConfig(do_sample=False, max_new_tokens=96, use_cache=True,
             bos_token_id=model.generation_config.bos_token_id, eos_token_id=model.generation_config.eos_token_id,
             pad_token_id=tokenizer.pad_token_id)
    environment.update(model_file_sha256=hashes, bytes=total, generation_config=config.to_dict(),
                       device=str(next(model.parameters()).device), dtype=str(next(model.parameters()).dtype))
    emit('ENVIRONMENT', environment)
    rows = []
    with patch.object(socket.socket, 'connect', blocked), patch.object(socket.socket, 'connect_ex', blocked):
        for i, case in enumerate(o.task.TASKS):
            seed = seeds[case['id']]['raw_response']
            order = o.CONDITIONS[i % 3:] + o.CONDITIONS[:i % 3]
            for condition in order:
                if len(rows) >= 12: raise ValueError('Generation ceiling')
                messages = [{'role':'system','content':o.task.SYSTEM},
                            {'role':'user','content':o.task.prompt(case)},
                            {'role':'assistant','content':seed},
                            {'role':'user','content':o.cue(seed,case,condition)}]
                rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(rendered, return_tensors='pt', add_special_tokens=False)
                n = inputs['input_ids'].shape[1]
                if n > 1200: raise ValueError('Input token ceiling')
                started = datetime.now(timezone.utc).isoformat(); clock = time.monotonic()
                with torch.inference_mode(): seq = model.generate(**inputs, generation_config=config)
                ids = seq[0,n:].tolist()
                raw = tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                row = {'case':case['id'], 'condition':condition, 'messages':messages,
                       'rendered_prompt_sha256':hashlib.sha256(rendered.encode()).hexdigest(),
                       'input_tokens':n, 'raw_response':raw, 'output_token_ids':ids,
                       'token_ceiling_reached':len(ids)==96, 'started_utc':started,
                       'seconds':round(time.monotonic()-clock,4), 'observation':o.observe(raw,case)}
                rows.append(row); emit('RECORD', row)
    result = {'status':'completed_exploratory_continuations', 'environment':environment,
              'rows':rows, 'summary':o.summarize(rows), 'new_generations':12, 'semantic_retries':0,
              'seed_origin':'v0.1 four previously observed initial responses, not newly generated or hidden',
              'user_pc_used':False, 'paid_model_api_calls':0, 'weights_updated':False,
              'limits':['four related tasks, one grammar','greedy single trials','unmatched feedback token lengths',
                        'public reused seeds','diagnostic candidate acceptance is not original strict acceptance']}
    emit('SUMMARY', {k:v for k,v in result.items() if k not in ('rows','environment')})
    # Exact self-contained public JSON transport, not a manual transcription.
    data = json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode()
    emit('ENCODED_RESULT', {'sha256':hashlib.sha256(data).hexdigest(), 'json_bytes':len(data),
                           'gzip_base64':base64.b64encode(gzip.compress(data,mtime=0)).decode()})
    signal.alarm(0)

if __name__ == '__main__':
    try: main()
    except Exception as e:
        emit('ABORT', {'error_type':type(e).__name__, 'message':str(e)[:300], 'keep_prior_records':True})
        raise
