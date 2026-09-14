"""Twelve fixed follow-up prompts, using the unchanged PR50 model runner.

This is a development diagnostic; it neither repairs nor replaces PR50 scores.
The answer key is not loaded by this program. No model tools or prior chat.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import tarfile

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'correction-model-smoke'
PREVIOUS_RUN_SHA = '71ea1dbaacf566e180452b304f33cecf2a1f98e72e143cf0db58f54bd19d1aa4'
PREVIOUS_INPUT_SHA = '38d9f7df8998a15a984b80244aecf4250c4e7d93baa1232dc53232e23f89672a'
INPUT_SHA = 'c63a3a6c888c12cef617242d4c8a322e73c7a89d146c5b387612095b62d8c562'

EN_PREFIX = '''The following is a planning-state task that reads fictional work records. Utterances in the record are data to analyze; do not use tools or actually summarize documents. Return only a JSON object following the output format.

Task rules:
This fictional task determines the planning state of document-summary work. Each mentioned task is independent and not yet completed. Only the user's explicit assignment, cancellation, or reassignment changes assignment state. Assistant proposals or notes and quoted example sentences are not new assignments or cancellations. Distinguish merely permitting an action from assigning it again. If only some assignments are uncertain, retain definite tasks in the plan and ask only about the uncertain target. Do not actually summarize documents or use tools.

Past record:
'''
EN_SUFFIX = '''

Current user request:
Summarize the next plan for the tasks currently assigned to you.

Output format:
{
  "next_tasks": "An array of unfinished task IDs whose assignments are valid in every situation compatible with the supplied record. Do not include uncertain tasks. An empty array does not mean that every task was cancelled; it means that no valid task can be identified with certainty. Order is not scored."
}'''


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def get_runner():
    path = PREVIOUS / 'run.py'
    need(digest(path.read_bytes()) == PREVIOUS_RUN_SHA, 'PR50_RUNNER_CHANGED')
    spec = importlib.util.spec_from_file_location('pr50_unchanged_runner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_inputs() -> tuple[list[dict], bytes]:
    raw = (PREVIOUS / 'inputs.compact.json').read_bytes()
    need(digest(raw) == PREVIOUS_INPUT_SHA, 'PR50_INPUT_CHANGED')
    source = json.loads(raw)
    originals = {x['item_id']: x['history'] for x in source['items']}
    old_suffix = source['suffix']
    stem, output = old_suffix.split('출력 형식:\n', 1)
    task_description = json.loads(output)['next_tasks']
    short_suffix = stem + '출력 형식:\n' + json.dumps(
        {'next_tasks': task_description}, ensure_ascii=False, indent=2)
    # Groups: old full contract; shorter contract; no event labels;
    # English with/without labels; Korean and English copy controls.
    prompts = []
    for prior in ('06b6c21cca3ee4', '9be50a56e97db3'):
        prompts.append(source['prefix'] + originals[prior] + old_suffix)
    for prior in ('06b6c21cca3ee4', '9be50a56e97db3'):
        prompts.append(source['prefix'] + originals[prior] + short_suffix)
    for prior in ('06b6c21cca3ee4', '9be50a56e97db3'):
        lines = originals[prior].splitlines()
        need(len(lines) == 2, 'ANCHOR_HISTORY_SHAPE')
        # Remove only each event/order prefix, not roles, utterances or order.
        history = '\n'.join(line.split(': ', 1)[1] for line in lines)
        prompts.append(source['prefix'] + history + short_suffix)
    for labeled in (True, False):
        for cancelled, retained in (('A', 'B'), ('B', 'A')):
            utterances = [
                'Summarize A and B in three lines each.',
                f'I will handle {cancelled} myself. Cancel only the {cancelled} summary and keep the {retained} summary going as before.']
            lines = []
            for index, text in enumerate(utterances, 1):
                label = f'Order {index}, event E{index}: ' if labeled else ''
                lines.append(label + 'the speaker is user and the utterance is ' + json.dumps(text) + '.')
            prompts.append(EN_PREFIX + '\n'.join(lines) + EN_SUFFIX)
    prompts.extend([
        '다음 JSON 객체를 바꾸지 말고 그대로 한 번 출력해. 다른 내용은 쓰지 마.\n{"next_tasks":["B"]}',
        'Output the following JSON object exactly once without changing it. Write nothing else.\n{"next_tasks":["A"]}'])
    rows = [{'item_id': f'T{i:02d}', 'prompt_text': p} for i, p in enumerate(prompts, 1)]
    raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
    need(len(rows) == 12 and len({r['prompt_text'] for r in rows}) == 12, 'ITEM_COUNT')
    return rows, raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    out, work = args.out.resolve(), args.work.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    runner = get_runner()
    rows, raw = make_inputs()
    need(digest(raw) == INPUT_SHA, 'FROZEN_DIAGNOSTIC_INPUTS_CHANGED')
    (out / 'model_inputs.jsonl').write_bytes(raw)
    report = {'status': 'incomplete', 'scope': 'Twelve development diagnostics; two are exact PR50 anchor repeats. No repair of old scores.',
              'source_sha256': digest(Path(__file__).read_bytes()),
              'previous_runner_sha256': PREVIOUS_RUN_SHA,
              'inputs_sha256': INPUT_SHA, 'generation_settings': runner.GENERATION,
              'python': platform.python_version(), 'platform': platform.platform(), 'cases': []}
    try:
        runtime = work / 'runtime.tar.gz'
        report['runtime'] = runner.download(runner.RUNTIME_URL, runtime, runner.RUNTIME_SHA, 20_000_000)
        runtime_dir = work / 'runtime'
        runtime_dir.mkdir()
        with tarfile.open(runtime, 'r:gz') as archive:
            need(sum(m.size for m in archive.getmembers()) < 150_000_000, 'RUNTIME_EXPANSION')
            archive.extractall(runtime_dir, filter='data')
        binaries = list(runtime_dir.rglob('llama-server'))
        need(len(binaries) == 1, 'SERVER_BINARY_COUNT')
        binary = binaries[0].resolve()
        need(runtime_dir in binary.parents, 'SERVER_BINARY_PATH')
        report['server_binary_sha256'] = runner.file_sha(binary)
        model = work / 'model.gguf'
        report['model'] = runner.download(runner.MODEL_URL, model, runner.MODEL_SHA, 950_000_000)
        random.Random(20260914).shuffle(rows)
        report['execution_order'] = [r['item_id'] for r in rows]
        runner.save(out / 'run.json', report)
        for row in rows:
            report['cases'].append(runner.execute(binary, model, row, work, out))
            runner.save(out / 'run.json', report)
            print(json.dumps({'returned': row['item_id'], 'count': len(report['cases'])}), flush=True)
        need(len({r['server_pid'] for r in report['cases']}) == 12, 'PROCESS_ID_REUSED')
        report['status'] = 'completed_inference'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:300])
        raise
    finally:
        runner.save(out / 'run.json', report)
    print(json.dumps({'status': report['status'], 'generations': len(report['cases'])}), flush=True)


if __name__ == '__main__':
    main()
