"""Use the unchanged actual-source checker with the signature-adapted fixture.

No assertions, tests or production resolution are removed. The original runner
and its first attempt remain reproducible. Only the preparation function and
report labeling are adapted here; all selected tests are run by the same runner.
"""
import json
from pathlib import Path
import execute_port_check as runner
from prepare_port_v2 import prepare

original_emit = runner.emit


def emit(kind, **fields):
    if kind == 'final':
        fields['original_test_file_bytes_unchanged'] = fields.pop('old_tests_preserved')
        fields['fixture_compatibility'] = json.loads(Path('generated/MANIFEST.json').read_text())['fixture_compatibility']
        fields['revision'] = 'v2-fixture-signature'
        Path('PORT_RESULTS.v2.json').write_text(json.dumps(fields, indent=2)+'\n')
    original_emit(kind, **fields)


if __name__ == '__main__':
    runner.prepare = prepare
    runner.emit = emit
    runner.main()
