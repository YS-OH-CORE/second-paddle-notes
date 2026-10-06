#!/usr/bin/env python3
"""Compile the real resolver module in a bounded standalone Rust harness.

Zero x Youngseok Oh. Exact public source/type declarations, not a Python model.
This is deliberately not a full mnemo-core build or a storage/recall integration test.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import urllib.request

REF = '3d26401f73bc41eaa352372fdb00bf41d0209565'
PATHS = {
    'crates/mnemo-core/src/query/current_fact_resolver.rs': '34a8b93458cf82318cf9d4ec06b8fe3536d8489b',
    'crates/mnemo-core/src/query/recall.rs': '5d19d0409dc66c53d325b8987c83c63e6745de46',
    'crates/mnemo-core/src/model/memory.rs': '3549a5680b9691601a93e5d561c6c8495d6168a3',
}
CANDIDATE_SHA = 'b37b59625c31ad3353cca5467ea15256c61fdd9d141c3353e3582e1802913dcd'
PATCH_SHA = 'e6d2d8891ee47b3bfbe8b9d67435e71a1f905eba42a841f4e113d82b7115dfb4'
NEW_TESTS = {
    'different_json_types_with_equal_text_remain_separate_facts',
    'supersession_stays_inside_each_json_identity_type',
    'noncolliding_equal_score_groups_keep_legacy_lexical_order',
    'unsupported_fact_value_types_continue_to_pass_through',
    'equal_boolean_fact_ids_still_resolve_to_the_newest_record',
}
EXPECTED_FAILURES = {
    'different_json_types_with_equal_text_remain_separate_facts',
    'supersession_stays_inside_each_json_identity_type',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(path):
    url = 'https://raw.githubusercontent.com/sattyamjjain/mnemo/' + REF + '/' + path
    with urllib.request.urlopen(url, timeout=30) as reply:
        raw = reply.read(2_000_001)
    assert len(raw) <= 2_000_000, 'Source exceeds bounded size'
    return raw


def declaration(text, kind, name):
    pattern = r'(?m)^((?:#\[[^\n]*\]\n)+pub ' + kind + ' ' + name + r' \{[\s\S]*?^\})'
    matches = re.findall(pattern, text)
    assert len(matches) == 1, 'Unexpected declaration: ' + name
    return matches[0] + '\n'


def run(cmd, cwd, log, expected=(0,), timeout=180):
    env = {k: v for k, v in os.environ.items() if k in {
        'PATH', 'HOME', 'RUSTUP_HOME', 'CARGO_HOME', 'LD_LIBRARY_PATH', 'TMPDIR',
    }}
    env.update(CARGO_BUILD_JOBS='2', CARGO_TERM_COLOR='never', RUST_BACKTRACE='0')
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding='utf-8', timeout=timeout)
    log.write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode in expected, (cmd, result.returncode, str(log))
    return result


def parse_tests(text):
    rows = re.findall(r'^test query::current_fact_resolver::tests::(\w+) \.\.\. (ok|FAILED)$', text, re.M)
    assert len(rows) == 11 and len(dict(rows)) == 11, 'Expected eleven actually executed tests'
    assert '11 filtered out' not in text
    return dict(rows)


def main():
    here = Path(__file__).resolve().parent
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = out / 'source'
    sources.mkdir()
    texts, manifest = {}, {}
    for path, blob in PATHS.items():
        raw = fetch(path)
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert actual == blob, path
        target = sources / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        texts[path] = raw.decode('utf-8')
        manifest[path] = {'git_blob': blob, 'sha256': sha(raw)}
    (sources / 'LICENSE').write_bytes(fetch('LICENSE'))
    original = texts['crates/mnemo-core/src/query/current_fact_resolver.rs']
    patch = (here / 'candidate.patch').read_bytes()
    assert sha(patch) == PATCH_SHA
    patch_tree = out / 'patched-source'
    resolver_rel = Path('crates/mnemo-core/src/query/current_fact_resolver.rs')
    target = patch_tree / resolver_rel
    target.parent.mkdir(parents=True)
    target.write_bytes(original.encode('utf-8'))
    run(['git', 'apply', '--whitespace=error', '--check', str(here / 'candidate.patch')],
        patch_tree, out / 'patch-check.log')
    run(['git', 'apply', str(here / 'candidate.patch')], patch_tree, out / 'patch-apply.log')
    candidate = target.read_text(encoding='utf-8')
    assert sha(candidate.encode('utf-8')) == CANDIDATE_SHA
    marker = '    // Proposed type-sensitive identity policy, pending maintainer confirmation.'
    assert candidate.count(marker) == 1 and candidate.endswith('\n}\n')
    new_tests = candidate[candidate.index(marker):-2]
    assert new_tests.count('#[test]') == 5 and original.endswith('\n}\n')
    baseline = original[:-2] + '\n' + new_tests + '}\n'
    memory_text = texts['crates/mnemo-core/src/model/memory.rs']
    recall_text = texts['crates/mnemo-core/src/query/recall.rs']
    copied = {name: declaration(memory_text, 'enum', name) for name in ['MemoryType', 'Scope']}
    copied.update({name: declaration(recall_text, 'struct', name)
                   for name in ['ScoredMemory', 'SupersededRecord', 'ScoreBreakdown']})
    shared = {
        'src/lib.rs': 'pub mod model { pub mod memory; }\npub mod query { pub mod recall; pub mod current_fact_resolver; }\n',
        'src/model/memory.rs': 'use serde::{Deserialize, Serialize};\n' + copied['MemoryType'] + copied['Scope'],
        'src/query/recall.rs': 'use serde::{Deserialize, Serialize};\nuse uuid::Uuid;\nuse crate::model::memory::{MemoryType, Scope};\n'
                               + copied['ScoredMemory'] + copied['SupersededRecord'] + copied['ScoreBreakdown'],
        'Cargo.toml': '[package]\nname="mnemo-resolver-module-probe"\nversion="0.0.0"\nedition="2021"\nrust-version="1.85"\n'
                      '\n[dependencies]\nserde={version="=1.0.228",features=["derive"]}\nserde_json="=1.0.145"\n'
                      'uuid={version="=1.18.1",features=["v7","serde"]}\n',
    }
    for label, module in [('baseline', baseline), ('candidate', candidate)]:
        crate = out / label
        for path, content in {**shared, 'src/query/current_fact_resolver.rs': module}.items():
            dst = crate / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(content.encode('utf-8'))
    run(['cargo', 'generate-lockfile'], out / 'candidate', out / 'lock-setup.log')
    lock = (out / 'candidate/Cargo.lock').read_bytes()
    (out / 'baseline/Cargo.lock').write_bytes(lock)
    (out / 'Cargo.lock').write_bytes(lock)
    results = {}
    for label in ['baseline', 'candidate']:
        crate = out / label
        # Different target directories prevent the second build reusing the first crate's binary.
        run(['cargo', 'test', '--locked', '--lib', '--', '--test-threads=1'], crate,
            out / (label + '.log'), expected=(0, 101))
        text = (out / (label + '.log')).read_text(encoding='utf-8')
        results[label] = parse_tests(text)
        assert (crate / 'Cargo.lock').read_bytes() == lock
        expected_module = baseline if label == 'baseline' else candidate
        assert (crate / 'src/query/current_fact_resolver.rs').read_bytes() == expected_module.encode()
    before, after = results['baseline'], results['candidate']
    assert set(before) == set(after) and NEW_TESTS <= set(before)
    assert {name for name, status in before.items() if status == 'FAILED'} == EXPECTED_FAILURES
    assert all(status == 'ok' for status in after.values())
    assert all(before[name] == 'ok' for name in set(before) - NEW_TESTS)
    original_block = original[original.index('#[cfg(test)]'):-2]
    assert original_block in baseline and original_block in candidate
    versions = subprocess.check_output(['rustc', '--version', '--verbose'], text=True)
    receipt = {
        'scope': 'Exact Rust resolver module and exact extracted public data declarations; not full mnemo-core or DB/recall integration.',
        'source_commit': REF, 'sources': manifest, 'candidate_sha256': CANDIDATE_SHA,
        'patch_sha256': PATCH_SHA, 'cargo_lock_sha256': sha(lock),
        'copied_declarations_sha256': {n: sha(v.encode()) for n, v in copied.items()},
        'rustc': versions, 'platform': platform.platform(), 'test_outcomes': results,
        'baseline': {'passed': 9, 'failed': 2}, 'candidate': {'passed': 11, 'failed': 0},
        'original_six_tests_unchanged_and_passed': True, 'same_five_proposed_tests': True,
        'comparison_passed': True, 'maintainer_identity_policy_confirmed': False,
        'full_project_built': False, 'storage_or_recall_integration_run': False,
        'upstream_patch_adopted': False, 'code_execution': 'Native Rust tests on a hosted Linux runner, not a Python simulation.',
    }
    (out / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Remove only generated build outputs, not test evidence or compiler logs.
    for label in ['baseline', 'candidate']:
        shutil.rmtree(out / label / 'target')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
