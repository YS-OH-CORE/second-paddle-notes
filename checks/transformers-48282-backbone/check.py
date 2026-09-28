# SPDX-License-Identifier: Apache-2.0
"""CPU-only, actual-CLI diagnostics for Transformers PR #48282.

Independent test and report by Zero × Youngseok Oh. No model execution.
"""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

HEAD = 'f3e3ad778c38990d38100c44c74f2054b9b2aae6'
TARGET = 'utils/get_pr_run_slow_jobs.py'
OLD = ('                if multimodal_parents := get_composite_files(get_composite_files):\n'
       '                    jobs_to_run.extend(multimodal_parents)\n')
FIX = ('                if item.startswith("models/"):\n'
       '                    jobs_to_run.extend(\n'
       '                        f"models/{parent}"\n'
       '                        for parent in get_composite_files(item.removeprefix("models/"))\n'
       '                        if f"models/{parent}" in repo_content\n'
       '                    )\n')


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()


def inventory(source, models=None):
    result = {}
    for filename, relative in [('tests_dir.txt', 'tests'),
                               ('tests_models_dir.txt', 'tests/models'),
                               ('tests_quantization_dir.txt', 'tests/quantization')]:
        result[filename] = [
            {'path': p.relative_to(source).as_posix(), 'type': 'dir'}
            for p in sorted((source / relative).iterdir())
            if p.is_dir() and (models is None or relative != 'tests/models' or p.name in models)
        ]
    return result


def invoke(source, out, label, files, metadata, arguments=(), interpreter=None, isolated=False):
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH'] = str(source / 'src')
    if isolated:
        env.pop('PYTHONPATH', None)
        env['PYTHONNOUSERSITE'] = '1'
    command = [str(interpreter or sys.executable)] + (['-I'] if isolated else [])
    command += [str(source / TARGET), *arguments]
    with tempfile.TemporaryDirectory(prefix='job-metadata-') as directory:
        working = Path(directory)
        save(working / 'pr_files.txt', files)
        for filename, data in metadata.items():
            save(working / filename, data)
        run = subprocess.run(command, cwd=working, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    (out / f'{label}.stdout').write_text(run.stdout, encoding='utf-8')
    (out / f'{label}.stderr').write_text(run.stderr, encoding='utf-8')
    return {'command': command, 'changed_files': files, 'arguments': list(arguments),
            'exit_code': run.returncode, 'stdout': run.stdout.strip(),
            'stderr_file': f'{label}.stderr', 'isolated_interpreter': isolated}


def phase(source, out):
    import transformers
    assert Path(transformers.__file__).resolve().is_relative_to(source / 'src')
    spec = importlib.util.spec_from_file_location('actual_suggester', source / TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parents = sorted(module.get_composite_files('clip'))
    assert 'llava' in parents, ('Required existing CLIP -> LLaVA control missing', parents)
    full = inventory(source)
    available = {entry['path'].removeprefix('tests/')
                 for entries in full.values() for entry in entries}
    for path in ('src/transformers/models/clip/modeling_clip.py',
                 'src/transformers/models/clip/configuration_clip.py',
                 'tests/models/clip/test_modeling_clip.py',
                 'src/transformers/quantizers/quantizer_awq.py'):
        assert (source / path).is_file(), path
    assert {'models/clip', 'models/llava', 'quantization/autoawq'} <= available
    expected_jobs = sorted({'models/clip'} | {f'models/{p}' for p in parents
                                            if f'models/{p}' in available})
    expected_full = ', '.join(p.removeprefix('models/') for p in expected_jobs[:module.MAX_NUM_JOBS_TO_SUGGEST])
    changed = lambda path, status='modified': [{'filename': path, 'status': status}]
    clip = 'src/transformers/models/clip/modeling_clip.py'
    cases = [
        ('clip_model', changed(clip), full, (), expected_full),
        ('clip_config', changed('src/transformers/models/clip/configuration_clip.py'), full, (), expected_full),
        ('clip_test', changed('tests/models/clip/test_modeling_clip.py'), full, (), expected_full),
        ('clip_and_llava_inventory', changed(clip), inventory(source, {'clip', 'llava'}), (), 'clip, llava'),
        ('clip_only_inventory', changed(clip), inventory(source, {'clip'}), (), 'clip'),
        ('removed_clip', changed(clip, 'removed'), full, (), ''),
        ('unrelated_docs', changed('docs/source/en/testing.md'), full, (), ''),
        ('explicit_models', [], full, ('--message', 'run-slow: clip, llava, _bad, nonexistent_synthetic_model'), "['models/clip', 'models/llava']"),
        ('explicit_quantizer', [], full, ('--message', 'run-slow: autoawq', '--quantization'), "['quantization/autoawq']"),
        ('changed_quantizer', changed('src/transformers/quantizers/quantizer_awq.py'), full, (), ''),
    ]
    records = [{'case': 'actual_registry_clip_to_llava', 'passed': True, 'parents': parents}]
    for name, files, metadata, arguments, expected in cases:
        item = invoke(source, out, name, files, metadata, arguments)
        item.update(case=name, expected_stdout=expected,
                    passed=item['exit_code'] == 0 and item['stdout'] == expected,
                    inventory_sizes={key: len(value) for key, value in metadata.items()})
        records.append(item)
    result = {'head': git(source, 'rev-parse', 'HEAD'),
              'source_module': transformers.__file__, 'python': sys.version,
              'transformers': transformers.__version__, 'target_sha256': sha((source / TARGET).read_bytes()),
              'cases': len(records), 'passed': sum(r['passed'] for r in records),
              'failed': [r['case'] for r in records if not r['passed']],
              'registry_parents': parents, 'expected_full_jobs': expected_jobs,
              'records': records, 'scope': 'Actual CLI and real config registry; synthetic changed-file inputs, no CI dispatch or model execution'}
    save(out / 'result.json', result)
    print(json.dumps({key: result[key] for key in ('cases', 'passed', 'failed')}, indent=2))
    return 0 if all(r['passed'] for r in records) else 1


def compare(source, out):
    assert git(source, 'rev-parse', 'HEAD') == HEAD
    assert not git(source, 'status', '--porcelain')
    target = source / TARGET
    original = target.read_bytes()
    text = original.decode('utf-8')
    assert text.count(OLD) == 1
    save(out / 'source.json', {'head': HEAD, 'target': TARGET, 'sha256': sha(original),
                             'git_blob': git(source, 'hash-object', str(target)),
                             'workflow_sha256': sha((source / '.github/workflows/pr_slow_ci_suggestion.yml').read_bytes())})
    # A clean interpreter probes the new startup dependency, not the runner image's installed packages.
    with tempfile.TemporaryDirectory(prefix='stdlib-probe-') as directory:
        venv.EnvBuilder(with_pip=False).create(directory)
        interpreter = Path(directory) / 'bin/python'
        probe = invoke(source, out, 'clean_environment', [], inventory(source),
                       ('--message', 'run-slow: clip'), interpreter, isolated=True)
    save(out / 'clean_environment.json', probe)
    variants = {'original': text,
                'argument_only': text.replace('get_composite_files(get_composite_files)',
                                              'get_composite_files(item.removeprefix("models/"))', 1),
                'normalized_filtered': text.replace(OLD, FIX, 1)}
    results = {}
    try:
        for label, contents in variants.items():
            target.write_text(contents, encoding='utf-8')
            directory = out / label
            directory.mkdir()
            if label != 'original':
                patch = ''.join(difflib.unified_diff(text.splitlines(True), contents.splitlines(True),
                                                   fromfile='a/' + TARGET, tofile='b/' + TARGET))
                (directory / 'diagnostic.patch').write_text(patch, encoding='utf-8')
            env = dict(os.environ, PYTHONPATH=str(source / 'src'), PYTHONDONTWRITEBYTECODE='1')
            run = subprocess.run([sys.executable, __file__, '--source', str(source),
                                  '--output', str(directory), '--phase'], env=env, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
            (directory / 'driver.stdout').write_text(run.stdout, encoding='utf-8')
            (directory / 'driver.stderr').write_text(run.stderr, encoding='utf-8')
            result_path = directory / 'result.json'
            results[label] = json.loads(result_path.read_text()) if result_path.exists() else {'setup_failed': True}
            results[label]['process_exit_code'] = run.returncode
    finally:
        target.write_bytes(original)
    assert not git(source, 'status', '--porcelain')
    summary = {'head': HEAD, 'source_restored': target.read_bytes() == original,
               'clean_environment': probe, 'phases': results}
    save(out / 'SUMMARY.json', summary)
    for label, result in results.items():
        print(label, {key: result.get(key) for key in ('cases', 'passed', 'failed', 'process_exit_code')})
    # Accept only the specific call-site/inventory effects; import failures are not feature failures.
    assert set(results['original']['failed']) == {'clip_model', 'clip_config', 'clip_test', 'clip_and_llava_inventory'}
    assert set(results['argument_only']['failed']) == {'clip_model', 'clip_config', 'clip_test', 'clip_and_llava_inventory', 'clip_only_inventory'}
    assert results['normalized_filtered']['passed'] == 11
    assert all(r['process_exit_code'] == (0 if k == 'normalized_filtered' else 1) for k, r in results.items())
    print('Expected targeted comparison observed. This is not full upstream CI validation.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--phase', action='store_true')
    args = parser.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.phase:
        return phase(source, out)
    compare(source, out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
