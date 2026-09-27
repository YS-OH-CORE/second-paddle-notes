"""Run the pinned CPU-only regression kit; no network or credentials required.
Dependency installation is separate. This does not import the full vLLM stack.
"""
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE_HASH = '74fa5093b91ed69d79ff402f0f86633be8017f110455f0843513404d6799b6d0'
REQUIRED = {'mistral-common': '1.11.7', 'pydantic': '2.13.5', 'pytest': '9.1.1'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='New JSON receipt; existing files are not overwritten')
    args = parser.parse_args()
    if args.out and args.out.exists():
        raise ValueError('Choose a new receipt path')
    if sys.flags.optimize:
        raise ValueError('Assertions must be enabled for this test kit')
    actual = {name: version(name) for name in REQUIRED}
    if actual != REQUIRED:
        raise ValueError('Install the exact versions in requirements.txt')
    if hashlib.sha256((HERE / 'mistral.py').read_bytes()).hexdigest() != SOURCE_HASH:
        raise ValueError('Pinned upstream source differs')
    with tempfile.TemporaryDirectory(prefix='mistral-validator-review-') as temp:
        report = Path(temp) / 'tests.xml'
        command = [sys.executable, '-B', '-m', 'pytest', '-c', 'pytest.ini',
                   '--confcutdir', str(HERE), '-p', 'no:cacheprovider',
                   'test_contract.py', 'test_provenance_boundary.py', '-q',
                   '--junitxml', str(report)]
        done = subprocess.run(command, cwd=HERE, capture_output=True, text=True,
                              encoding='utf-8', timeout=60,
                              env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                                   'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})
        if not report.is_file():
            raise RuntimeError('The test runner did not produce a report')
        suite = ET.parse(report).getroot().find('testsuite')
        counts = {key: int(suite.attrib[key]) for key in ('tests', 'failures', 'errors', 'skipped')}
        good = done.returncode == 0 and counts == {'tests': 8, 'failures': 0, 'errors': 0, 'skipped': 0}
        results = [{'name': case.attrib['name'], 'outcome':
                    ('failed' if case.find('failure') is not None else
                     'error' if case.find('error') is not None else
                     'skipped' if case.find('skipped') is not None else 'passed')}
                   for case in suite.findall('testcase')]
    receipt = {'schema': 'mistral-validator-review/1', 'status': 'passed' if good else 'failed',
               'checked_utc': datetime.now(timezone.utc).isoformat(),
               'environment': {'python': platform.python_version(), 'os': platform.system(), 'packages': actual},
               'source_commit': 'a9cdfa3b645773684b40359e11e78fb49f4c57e8',
               'source_sha256': SOURCE_HASH, 'counts': counts, 'cases': results,
               'scope': 'Pinned extracted helper and real Mistral message validators in serving mode.',
               'not_tested': ['full vLLM import', 'image decoding', 'tokenizer', 'endpoint',
                              'model generation', 'real user traffic', 'cross-platform equivalence'],
               'interpretation': 'Seven regression checks plus one characterization of documented attribution loss; not eight bugs.'}
    if args.out:
        with args.out.open('x', encoding='utf-8') as out:
            json.dump(receipt, out, ensure_ascii=False, indent=2)
            out.write('\n')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if good else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'not_run', 'error_type': type(error).__name__}), file=sys.stderr)
        raise SystemExit(2)
