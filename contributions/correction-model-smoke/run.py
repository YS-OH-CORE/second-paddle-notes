"""One bounded CPU smoke run of fixed synthetic prompts, with no answer key.

Downloads pinned public weights/runtime, then restarts a loopback-only model
server for every item. Generation has no tools and no conversation context.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import tarfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
INPUT_SHA = '0335c83c4d9bef8fd52d800381a8e9fe4e0362611b94692657dd562ac7fd54c3'
RUNTIME_URL = 'https://github.com/ggml-org/llama.cpp/releases/download/b10809/llama-b10809-bin-ubuntu-x64.tar.gz'
RUNTIME_SHA = '5e34434ddc6d03cd1584f403201aff0d4bd1a5793a72ff7e286532dfd1e4b941'
MODEL_URL = 'https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/resolve/8fea620810c4afa23dd6443f999a48574c1611a3/Qwen3.5-0.8B-Q8_0.gguf'
MODEL_SHA = '37ae482d336108d23516fa35e8e0c4126688d81018b87178a18d752a1357814f'
ENDPOINT = 'http://127.0.0.1:18082'
GENERATION = {'temperature': 0.0, 'top_p': 1.0, 'top_k': 1, 'min_p': 0.0,
              'repeat_penalty': 1.0, 'presence_penalty': 0.0,
              'max_tokens': 256, 'seed': 20260914, 'stream': False,
              'cache_prompt': False, 'chat_template_kwargs': {'enable_thinking': False}}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_inputs(path: Path) -> tuple[list[dict], bytes]:
    data = json.loads(path.read_text(encoding='utf-8'))
    need(set(data) == {'prefix', 'suffix', 'items'}, 'INPUT_FIELDS')
    rows = []
    for item in data['items']:
        need(set(item) == {'item_id', 'history'}, 'ITEM_FIELDS')
        rows.append({'item_id': item['item_id'],
                     'prompt_text': data['prefix'] + item['history'] + data['suffix']})
    raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode('utf-8')
    need(len(rows) == len({r['item_id'] for r in rows}) == 16 and sha(raw) == INPUT_SHA, 'FROZEN_INPUTS_DIFFER')
    return rows, raw


def download(url: str, path: Path, expected: str, limit: int) -> dict:
    h, size = hashlib.sha256(), 0
    req = urllib.request.Request(url, headers={'User-Agent': 'second-paddle-development-smoke/1'})
    with urllib.request.urlopen(req, timeout=120) as response, path.open('xb') as out:
        need(response.url.startswith('https://'), 'DOWNLOAD_REDIRECT')
        while block := response.read(1024 * 1024):
            size += len(block)
            need(size <= limit, 'DOWNLOAD_LIMIT')
            h.update(block)
            out.write(block)
    need(h.hexdigest() == expected, 'DOWNLOAD_IDENTITY')
    return {'url': url, 'bytes': size, 'sha256': h.hexdigest()}


def local_json(path: str, body: dict | None = None, timeout: int = 5) -> tuple[dict, bytes]:
    raw = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
    req = urllib.request.Request(ENDPOINT + path, data=raw,
        headers={'Content-Type': 'application/json'}, method='POST' if raw is not None else 'GET')
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as response:
        value = response.read(1024 * 1024 + 1)
        need(len(value) <= 1024 * 1024, 'RESPONSE_LIMIT')
    return json.loads(value), value


def execute(binary: Path, model: Path, row: dict, work: Path, out: Path) -> dict:
    item = row['item_id']
    home = work / item
    home.mkdir()
    env = {'PATH': os.defpath, 'HOME': str(home), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
           'LD_LIBRARY_PATH': str(binary.parent), 'OMP_NUM_THREADS': '4'}
    command = [str(binary), '--model', str(model), '--host', '127.0.0.1', '--port', '18082',
               '--ctx-size', '4096', '--parallel', '1', '--threads', '4', '--threads-batch', '4',
               '--n-gpu-layers', '0', '--jinja', '--chat-template-kwargs', '{"enable_thinking":false}']
    request = dict(GENERATION, model='Qwen3.5-0.8B-Q8_0',
                   messages=[{'role': 'user', 'content': row['prompt_text']}])
    save(out / (item + '.request.json'), request)
    started = time.monotonic_ns()
    record = {'item_id': item, 'prompt_sha256': sha(row['prompt_text'].encode()),
              'started_monotonic_ns': started, 'request_sha256': file_sha(out / (item + '.request.json')),
              'state': 'incomplete'}
    with (out / (item + '.server.log')).open('wb') as log:
        process = subprocess.Popen(command, cwd=home, env=env, stdout=log, stderr=subprocess.STDOUT)
        record['server_pid'] = process.pid
        try:
            deadline = time.monotonic() + 35
            while True:
                need(process.poll() is None, 'SERVER_EXITED_DURING_START')
                try:
                    health, _ = local_json('/health')
                    if health.get('status') == 'ok':
                        break
                except (urllib.error.URLError, TimeoutError, OSError):
                    pass
                need(time.monotonic() < deadline, 'SERVER_START_TIMEOUT')
                time.sleep(0.2)
            props, _ = local_json('/props')
            save(out / (item + '.props.json'), props)
            response, raw = local_json('/v1/chat/completions', request, timeout=90)
            (out / (item + '.response.json')).write_bytes(raw)
            need(isinstance(response.get('choices'), list) and len(response['choices']) == 1, 'RESPONSE_SHAPE')
            record.update(state='returned', response_sha256=sha(raw),
                          finish_reason=response['choices'][0].get('finish_reason'),
                          usage=response.get('usage'), response_model=response.get('model'))
        except Exception as exc:
            record.update(state='infrastructure_error', error_type=type(exc).__name__, error=str(exc)[:300])
            raise
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            record.update(server_returncode=process.returncode, finished_monotonic_ns=time.monotonic_ns())
            save(out / (item + '.record.json'), record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    out, work = args.out.resolve(), args.work.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    report = {'status': 'incomplete', 'scope': '16 development generations, not a held-out benchmark or independent expert review',
              'generation_settings': GENERATION, 'cases': [], 'python': platform.python_version(),
              'platform': platform.platform(), 'cpus': os.cpu_count(),
              'runner_source_sha256': file_sha(Path(__file__)), 'inputs_sha256': INPUT_SHA}
    try:
        rows, raw = load_inputs(HERE / 'inputs.compact.json')
        (out / 'model_inputs.jsonl').write_bytes(raw)
        runtime = work / 'runtime.tar.gz'
        report['runtime'] = download(RUNTIME_URL, runtime, RUNTIME_SHA, 20_000_000)
        runtime_dir = work / 'runtime'
        runtime_dir.mkdir()
        with tarfile.open(runtime, 'r:gz') as archive:
            need(sum(m.size for m in archive.getmembers()) < 150_000_000, 'RUNTIME_EXPANSION')
            archive.extractall(runtime_dir, filter='data')
        matches = list(runtime_dir.rglob('llama-server'))
        need(len(matches) == 1, 'SERVER_BINARY_COUNT')
        binary = matches[0].resolve()
        need(runtime_dir in binary.parents, 'SERVER_BINARY_PATH')
        report['server_binary_sha256'] = file_sha(binary)
        model = work / 'model.gguf'
        report['model'] = download(MODEL_URL, model, MODEL_SHA, 950_000_000)
        random.Random(20260914).shuffle(rows)
        report['execution_order'] = [r['item_id'] for r in rows]
        save(out / 'run.json', report)
        for row in rows:
            report['cases'].append(execute(binary, model, row, work, out))
            save(out / 'run.json', report)
            print(json.dumps({'returned': row['item_id'], 'count': len(report['cases'])}), flush=True)
        need(len({r['server_pid'] for r in report['cases']}) == 16, 'PROCESS_ID_REUSED')
        report['status'] = 'completed_inference'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:300])
        raise
    finally:
        save(out / 'run.json', report)
    print(json.dumps({'status': report['status'], 'generations': len(report['cases'])}), flush=True)


if __name__ == '__main__':
    main()
