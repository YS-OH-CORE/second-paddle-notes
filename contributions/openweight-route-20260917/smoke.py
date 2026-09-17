"""Bounded, synthetic open-weight inference/handoff smoke test.

Prepared by Zero (ChatGPT) for Youngseok Oh. MIT for this new harness.
Not a held-out benchmark, independent review, or autonomous tool-use agent.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile
import time
import urllib.request

RUNTIME_URL = 'https://github.com/ggml-org/llama.cpp/releases/download/b10964/llama-b10964-bin-ubuntu-x64.tar.gz'
RUNTIME_SHA = '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443'
MODEL_REPO = 'Qwen/Qwen3-4B-GGUF'
MODEL_REV = 'bc640142c66e1fdd12af0bd68f40445458f3869b'
MODEL_FILE = 'Qwen3-4B-Q4_K_M.gguf'
MODEL_SHA = '7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5'
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REV}/{MODEL_FILE}'
BASE = 'http://127.0.0.1:18473'
SYSTEM = ('Follow the currently accepted user task. An assistant proposal is not user acceptance. '
          'Return only one JSON object with exactly criterion, selected, retained. '
          'criterion must be latency or reproducibility; selected is an option name; '
          'retained is an array of record names the task requires preserving. No explanation. /no_think')
WRITER = ('For this turn, do not produce the final decision JSON. Instead write only a plain-text '
          'handoff of at most 100 whitespace-separated words for a fresh executor. '
          'Include the currently accepted criterion, both options and their measured values, '
          'unaccepted proposals if any, and independently required records. '
          'Do not introduce a new goal. The executor will not see this conversation. /no_think')
PARAMS = {'temperature': 0.0, 'seed': 17, 'max_tokens': 256, 'cache_prompt': False,
          'chat_template_kwargs': {'enable_thinking': False}}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cases() -> list[dict]:
    result = []
    for renamed in (False, True):
        fast, repeatable = ('Vela', 'Tarin') if renamed else ('Aster', 'Beryl')
        rows = [(fast, 8, '3/10'), (repeatable, 12, '9/10')]
        if renamed:
            rows.reverse()
        initial = ('Select one option using the lowest latency_ms. Also retain both existing '
                   'records named observations and source_register. The source register is a '
                   'separate continuing obligation. The measured data are:\n' +
                   '\n'.join(f'{n}: latency_ms={ms}; successful_reproductions={r}' for n, ms, r in rows))
        revision = ('Change only the primary criterion to the highest successful_reproductions '
                    'fraction. Keep both options and both existing records.')
        for revised in (True, False):
            history = [{'role': 'user', 'content': initial}]
            if revised:
                history += [{'role': 'assistant', 'content': 'The lowest-latency option is ' + fast + '.'},
                            {'role': 'user', 'content': revision + ' Complete the decision now.'}]
            else:
                history += [{'role': 'assistant', 'content': 'I propose: ' + revision},
                            {'role': 'user', 'content': 'I have not adopted that proposal. Complete my original request.'}]
            result.append({'id': ('renamed' if renamed else 'original') + ('-revision' if revised else '-proposal'),
                           'history': history,
                           'expected': {'criterion': 'reproducibility' if revised else 'latency',
                                        'selected': repeatable if revised else fast,
                                        'retained': ['observations', 'source_register']}})
    return result


def parse_decision(text: str, expected: dict) -> dict:
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    try:
        value = json.loads(text, object_pairs_hook=pairs)
        exact = isinstance(value, dict) and set(value) == set(expected)
        retained = value.get('retained') if isinstance(value, dict) else None
        retained_ok = (isinstance(retained, list) and all(isinstance(x, str) for x in retained)
                       and len(retained) == 2 and set(retained) == set(expected['retained']))
        passed = (exact and value['criterion'] == expected['criterion'] and
                  value['selected'] == expected['selected'] and retained_ok)
        return {'parsed': value, 'smoke_match': passed,
                'note': 'retained is a declaration, not a verified file-preservation action'}
    except (ValueError, TypeError) as error:
        return {'smoke_match': False, 'parse_error': str(error)}


def download(url: str, target: Path, sha: str, maximum: int) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'zero-public-model-smoke/1.0'})
    h, size, start = hashlib.sha256(), 0, time.monotonic()
    with urllib.request.urlopen(req, timeout=90) as response, target.open('xb') as output:
        while data := response.read(1024 * 1024):
            size += len(data)
            if size > maximum or time.monotonic() - start > 420:
                raise RuntimeError('bounded download exceeded size/time allowance')
            h.update(data)
            output.write(data)
    if h.hexdigest() != sha:
        raise RuntimeError('download digest mismatch: ' + target.name)
    return {'url': url, 'sha256': h.hexdigest(), 'bytes': size,
            'seconds': round(time.monotonic() - start, 3)}


def call(messages: list[dict], label: str, out: Path, records: list[dict]) -> dict:
    request = dict(PARAMS, model='qwen3-4b-q4km-pinned', messages=messages, stream=False)
    raw = json.dumps(request, ensure_ascii=False, sort_keys=True).encode()
    record = {'id': label, 'request': request, 'request_sha256': digest(raw)}
    start = time.monotonic()
    try:
        req = urllib.request.Request(BASE + '/v1/chat/completions', data=raw,
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=180) as response:
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise ValueError('response size limit exceeded')
            result = json.loads(body)
        record.update(status='returned', response=result, response_sha256=digest(body),
                      response_model=result.get('model'), usage=result.get('usage'))
        choice = result['choices'][0]
        record['content'] = choice['message'].get('content') or ''
        record['finish_reason'] = choice.get('finish_reason')
        if not isinstance(record['content'], str):
            raise ValueError('non-string content')
    except Exception as error:
        record.update(status='transport_or_response_error', error=type(error).__name__ + ': ' + str(error))
    record['seconds'] = round(time.monotonic() - start, 3)
    records.append(record)
    (out / (label + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print('CALL_RESULT ' + json.dumps({k: record[k] for k in ('id', 'status', 'seconds')}), flush=True)
    return record


def content_ok(record: dict) -> bool:
    return record['status'] == 'returned' and record.get('finish_reason') == 'stop' and bool(record.get('content'))


def run(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'zero-openweight-route-smoke-v1', 'status': 'not_started',
               'scope': 'New synthetic execution smoke only; no model ranking or independent semantic review.',
               'model': {'repository': MODEL_REPO, 'revision': MODEL_REV, 'file': MODEL_FILE, 'sha256': MODEL_SHA},
               'runtime_tag': 'b10964', 'parameters': PARAMS,
               'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                               'cpus': os.cpu_count(), 'workflow_commit': os.environ.get('GITHUB_SHA'),
                               'workflow_run': os.environ.get('GITHUB_RUN_ID')},
               'calls': [], 'decisions': []}
    fixtures = cases()
    (out / 'fixtures.json').write_text(json.dumps(fixtures, indent=2))
    receipt['fixture_sha256'] = digest((out / 'fixtures.json').read_bytes())
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix='zero-inference-') as temporary:
            work = Path(temporary)
            receipt['runtime_download'] = download(RUNTIME_URL, work / 'runtime.tar.gz', RUNTIME_SHA, 100_000_000)
            receipt['model_download'] = download(MODEL_URL, work / 'model.gguf', MODEL_SHA, 3_000_000_000)
            runtime = work / 'runtime'
            runtime.mkdir()
            with tarfile.open(work / 'runtime.tar.gz') as archive:
                archive.extractall(runtime, filter='data')
            servers = list(runtime.rglob('llama-server'))
            if len(servers) != 1:
                raise RuntimeError('expected exactly one runtime server executable')
            server = servers[0]
            env = {k: v for k, v in os.environ.items()
                   if k in ('PATH', 'LANG', 'LC_ALL', 'SYSTEMROOT')}
            env['HOME'] = str(work)
            env['LD_LIBRARY_PATH'] = str(server.parent)
            receipt['runtime_version'] = subprocess.check_output([str(server), '--version'], env=env,
                                        stderr=subprocess.STDOUT, text=True, timeout=20).strip()
            command = [str(server), '-m', str(work / 'model.gguf'), '--host', '127.0.0.1',
                       '--port', '18473', '-c', '4096', '-t', '4', '-tb', '4', '-ngl', '0',
                       '--parallel', '1', '--jinja', '--reasoning', 'off',
                       '--chat-template-kwargs', '{"enable_thinking":false}', '--no-cache-prompt',
                       '--no-webui', '--no-agent', '--offline', '--alias', 'qwen3-4b-q4km-pinned']
            receipt['server_arguments'] = [x.replace(str(work), '<TEMP>') for x in command]
            with (out / 'server.log').open('w') as log:
                process = subprocess.Popen(command, env=env, cwd=work, stdout=log, stderr=subprocess.STDOUT)
                ready = False
                for _ in range(90):
                    if process.poll() is not None:
                        raise RuntimeError('inference server exited during startup')
                    try:
                        with urllib.request.urlopen(BASE + '/health', timeout=2) as r:
                            ready = r.status == 200
                        if ready:
                            break
                    except Exception:
                        time.sleep(1)
                if not ready:
                    raise RuntimeError('server readiness timed out')
                copy = call([{'role': 'system', 'content': 'Reply only with the exact requested JSON. /no_think'},
                             {'role': 'user', 'content': 'Reply with {"ready":true} and no other text.'}],
                            'copy-control', out, receipt['calls'])
                try:
                    receipt['copy_control_match'] = content_ok(copy) and json.loads(copy['content']) == {'ready': True}
                except (ValueError, KeyError):
                    receipt['copy_control_match'] = False
                for case in fixtures:
                    record = call([{'role': 'system', 'content': SYSTEM}] + case['history'],
                                  case['id'] + '-direct', out, receipt['calls'])
                    score = parse_decision(record.get('content', ''), case['expected'])
                    score['smoke_match'] = content_ok(record) and score['smoke_match']
                    receipt['decisions'].append(dict(id=record['id'], **score))
                for case in fixtures[:2]:
                    writer = call([{'role': 'system', 'content': 'Write faithful task handoffs. /no_think'}]
                                  + case['history'] + [{'role': 'user', 'content': WRITER}],
                                  case['id'] + '-writer', out, receipt['calls'])
                    text = writer.get('content', '')
                    valid = content_ok(writer) and len(text.split()) <= 100
                    if not valid:
                        receipt['decisions'].append({'id': case['id'] + '-handoff',
                                                     'smoke_match': False, 'not_executed': 'writer contract failed'})
                        continue
                    forwarded = 'Complete the task from this handoff. The original conversation is unavailable.\n' + text
                    successor = call([{'role': 'system', 'content': SYSTEM},
                                      {'role': 'user', 'content': forwarded}],
                                     case['id'] + '-handoff', out, receipt['calls'])
                    score = parse_decision(successor.get('content', ''), case['expected'])
                    score['smoke_match'] = content_ok(successor) and score['smoke_match']
                    score.update(memory_words=len(text.split()), forwarded_memory_sha256=digest(text.encode()),
                                 original_history_supplied=False)
                    receipt['decisions'].append(dict(id=successor['id'], **score))
                receipt['status'] = 'execution_completed'
                receipt['returned_calls'] = sum(x['status'] == 'returned' for x in receipt['calls'])
                receipt['matched_decisions'] = sum(x['smoke_match'] for x in receipt['decisions'])
                process.terminate()
                process.wait(timeout=20)
                process = None
    except Exception as error:
        receipt.update(status='execution_error', error=type(error).__name__ + ': ' + str(error))
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
        (out / 'receipt.json').write_text(encoded + '\n')
        print('ZERO_MODEL_RECEIPT ' + encoded, flush=True)
        print('RECEIPT_SHA256 ' + digest((encoded + '\n').encode()), flush=True)
        if receipt['status'] != 'execution_completed' and (out / 'server.log').exists():
            print('SERVER_FAILURE_TAIL\n' + (out / 'server.log').read_text()[-4000:], flush=True)
    return 0 if receipt['status'] == 'execution_completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.out))
