"""Compatibility follow-up: preserve assertions, adapt the old fixture signature.

The first actual-source test run reached the dispatch cleanup, where current
main supplies run_generation to a formerly one-argument fixture lambda. Do not
remove the production keyword or skip failing tests. Preserve original source
snapshots and change only this fixture signature in the candidate copy.
"""
from __future__ import annotations
import ast
import difflib
import json
from pathlib import Path
import sys
from prepare_port import prepare as prepare_v1, digest, MAIN, BASE, HEAD, FILES


def prepare(target):
    manifest = prepare_v1(target)
    target = Path(target)
    (target / 'MANIFEST.v1.json').write_bytes((target / 'MANIFEST.json').read_bytes())
    (target / 'current-main-port.v1.patch').write_bytes((target / 'current-main-port.patch').read_bytes())
    name = 'tests/gateway/test_model_multiline_payload.py'
    path = target / 'candidate' / name
    original = path.read_bytes()
    old = '    runner._release_running_agent_state = lambda key: runner._running_agents.pop(key, None)\n'
    new = '    runner._release_running_agent_state = lambda key, *, run_generation=None: runner._running_agents.pop(key, None)\n'
    text = original.decode('utf-8')
    if text.count(old) != 1:
        raise ValueError('Expected fixture signature is not unique; do not guess')
    replacement = text.replace(old, new)
    # The fixture's behavior is unchanged; test assertions are not relaxed.
    before = ast.parse(text)
    after = ast.parse(replacement)
    checks = lambda tree: [ast.dump(n, include_attributes=False) for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    if checks(before) != checks(after):
        raise ValueError('Fixture update changed an assertion')
    path.write_bytes(replacement.encode('utf-8'))
    manifest['fixture_compatibility'] = {
        'path': name, 'before_sha256': digest(original),
        'after_sha256': digest(path.read_bytes()), 'old_line': old.rstrip(),
        'new_line': new.rstrip(), 'assertion_ast_unchanged': True,
        'purpose': 'Accept current cleanup keyword in the existing test double; no generation-correctness claim.'}
    patches = []
    for item in manifest['files']:
        name = item['path']
        candidate = (target / 'candidate' / name).read_bytes()
        source = target / 'sources' / 'main' / name
        current = source.read_bytes() if source.exists() else b''
        item['candidate'] = digest(candidate)
        delta = difflib.unified_diff(current.decode().splitlines(keepends=True), candidate.decode().splitlines(keepends=True),
                                    fromfile='a/'+name if source.exists() else '/dev/null', tofile='b/'+name)
        patches.append(''.join(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n' for line in delta))
    patch = ''.join(patches).encode()
    (target / 'current-main-port.patch').write_bytes(patch)
    manifest['patch_sha256'] = digest(patch)
    manifest['revision'] = 'v2-fixture-signature'
    (target / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python prepare_port_v2.py NEW_DIRECTORY')
    print(json.dumps(prepare(sys.argv[1]), indent=2))
