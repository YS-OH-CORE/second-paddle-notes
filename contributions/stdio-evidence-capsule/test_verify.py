"""Local verifier tests; no MCP graph/session or retained source is executed."""
from copy import deepcopy
import base64
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zlib
import verify as v

ROOT = Path(__file__).resolve().parents[2]
CAPSULE = Path(__file__).with_name('records.capsule.json')


class RetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = v.load_capsule(CAPSULE)
        cls.sources = v.verify_sources(cls.packet, ROOT)
        cls.rows = v.strict_json(cls.packet['archives']['successful']['members']['stdio-evidence/observations.json'])['cases']

    def test_actual_capsule(self):
        result = v.verify_packet(self.packet, ROOT)
        self.assertEqual(result['retained_members'], 42)
        self.assertEqual(result['historical_tool_calls'], 9)
        self.assertTrue(result['failure_preserved_as_failure'])

    def test_no_embedded_source_import_even_with_site_disabled(self):
        command = [sys.executable, '-S', str(Path(v.__file__))]
        run = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'], 'verified')

    def test_optimization_does_not_disable_checks(self):
        run = subprocess.run([sys.executable, '-O', '-S', str(Path(v.__file__))], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        code = "import verify; verify.equal(True, 1, 'BOOLEAN_DIFFER')"
        failed = subprocess.run([sys.executable, '-O', '-S', '-c', code], cwd=CAPSULE.parent, capture_output=True, timeout=10)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn(b'BOOLEAN_DIFFER', failed.stderr)

    def test_duplicate_json_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            v.strict_json('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        for word in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(word=word), self.assertRaisesRegex(ValueError, 'NONFINITE_JSON'):
                v.strict_json('{"a":' + word + '}')

    def test_unsafe_names_rejected(self):
        for name in ('../escape', '/absolute', 'a/../b', 'a\\b', 'C:/file', 'a//b', './file', ''):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
                v.safe_name(name)

    def test_missing_source_fails_without_running_anything(self):
        with TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, 'SOURCE_SIZE'):
            v.verify_sources(self.packet, Path(tmp))

    def test_changed_source_bytes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in self.packet['source_files']:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / name).read_bytes())
            path = root / v.GRAPH
            raw = path.read_bytes()
            path.write_bytes(b'X' + raw[1:])
            with self.assertRaisesRegex(ValueError, 'SOURCE_IDENTITY'):
                v.verify_sources(self.packet, root)

    def test_changed_member(self):
        archive = deepcopy(self.packet['archives']['successful'])
        archive['members']['stdio-unit.log'] += 'changed'
        with self.assertRaisesRegex(ValueError, 'MEMBER_IDENTITY'):
            v.verify_member_bytes(archive)

    def test_missing_member_hash(self):
        archive = deepcopy(self.packet['archives']['successful'])
        archive['member_sha256'].pop('stdio-unit.log')
        with self.assertRaisesRegex(ValueError, 'MEMBER_SET'):
            v.verify_member_bytes(archive)

    def test_compressed_loader_failures(self):
        outer = json.loads(CAPSULE.read_text())
        mutations = {
            'pin': lambda x: x.update(payload_sha256='0' * 64),
            'wrong_body': lambda x: x.update(payload=base64.b64encode(zlib.compress(b'{}')).decode()),
            'invalid_base64': lambda x: x.update(payload='!!!!'),
            'truncated': lambda x: x.update(payload=base64.b64encode(base64.b64decode(x['payload'])[:-4]).decode()),
            'trailing': lambda x: x.update(payload=base64.b64encode(base64.b64decode(x['payload']) + b'x').decode()),
            'expansion': lambda x: x.update(payload=base64.b64encode(zlib.compress(b'x' * (v.MAX_EXPANDED + 1))).decode()),
            'extra_field': lambda x: x.update(extra=True),
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            for label, mutate in mutations.items():
                bad = deepcopy(outer)
                mutate(bad)
                path.write_text(json.dumps(bad))
                with self.subTest(case=label), self.assertRaises((ValueError, zlib.error)):
                    v.load_capsule(path)

    def test_failure_cannot_be_presented_as_full_success(self):
        packet = deepcopy(self.packet)
        failed = packet['archives']['first_failed']
        name = 'stdio-evidence/observations.json'
        data = json.loads(failed['members'][name])
        data['status'] = 'verified'
        failed['members'][name] = json.dumps(data)
        failed['member_sha256'][name] = v.digest(failed['members'][name].encode())
        with self.assertRaisesRegex(ValueError, 'FAILURE_RELABELED'):
            v.verify_packet(packet, ROOT)


def change_graph_hash(row):
    row['client_a']['graph_sha256'] = '0' * 64
    row['client_b']['graph_sha256'] = '0' * 64


def number_for_boolean(row):
    answer = {v.KEY: {'action': 'accept', 'content': {'yes': 1, 'note': v.NOTE}}}
    row['client_b']['supplied_answer'] = {'responses': deepcopy(answer)}
    row['client_b']['calls'][-1]['input_responses'] = deepcopy(answer)
    row['server_logs'][1][1]['input_responses'] = deepcopy(answer)


MUTATIONS = {
    'graph_hash_changed_in_both_clients': change_graph_hash,
    'numeric_one_instead_of_boolean': number_for_boolean,
    'terminal_detached_from_last_call': lambda r: r['client_b']['result']['content'][0].update(text='previewed:different'),
    'changed_displayed_question': lambda r: r['client_a']['shown']['requests'][0].update(message='Different question'),
    'changed_displayed_schema': lambda r: r['client_a']['shown']['requests'][0]['requested_schema'].update(required=[]),
    'changed_displayed_key': lambda r: r['client_a']['shown']['requests'][0].update(key='different'),
    'changed_saved_frame': lambda r: r['client_b']['reopened_frame']['value'].update(requestState='fixture-replacement'),
    'same_client_pid': lambda r: r['client_b'].update(pid=r['client_a']['pid']),
    'boolean_pid': lambda r: r['client_a'].update(pid=True),
    'reversed_process_order': lambda r: r.update(a_exited_monotonic_ns=r['client_b']['monotonic_ns'] + 1),
    'nonzero_child_exit': lambda r: r.update(returncodes=[0, 1]),
    'boolean_child_exit': lambda r: r.update(returncodes=[False, 0]),
    'client_network_attempt': lambda r: r['client_b'].update(network_attempts=['example.invalid']),
    'server_network_attempt': lambda r: r['server_logs'][1][-1].update(network_attempts=['example.invalid']),
    'changed_package_pin': lambda r: r['client_b']['versions'].update(mcp='different'),
    'changed_probe_hash': lambda r: r['client_b'].update(probe_sha256='0' * 64),
    'changed_protocol': lambda r: r['client_b'].update(protocol_version='different'),
    'extra_runtime_metadata': lambda r: r['client_b']['calls'][0]['result']['_meta'].update(extra='not ignored'),
    'changed_wire_state': lambda r: r['server_logs'][1][1].update(request_state='fixture-different'),
    'repeated_tool_call': lambda r: r['client_b']['calls'].append(deepcopy(r['client_b']['calls'][0])),
    'unexpected_effect': lambda r: r['server_logs'][1][1]['snapshot']['effects'].append(['other', 'draft-2']),
}


def mutation_test(mutate):
    def test(self):
        row = deepcopy(self.rows[0])
        mutate(row)
        with self.assertRaises(ValueError):
            v.verify_case(row, self.sources)
    return test


for name, mutate in MUTATIONS.items():
    setattr(RetentionTests, 'test_record_' + name, mutation_test(mutate))


if __name__ == '__main__':
    unittest.main()
