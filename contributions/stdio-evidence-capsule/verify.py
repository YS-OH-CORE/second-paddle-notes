"""Offline inspection of retained PR35 records. Never imports the tested code."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile
import zlib

PAYLOAD_SHA256 = '153ac8bda6e62faf4c260611e41f85862c11525ceb1dd613bab170f57595facd'
PAYLOAD_BYTES = 134834
MAX_INPUT = 200_000
MAX_EXPANDED = 500_000
CASES = ('preserved', 'lost_server_state', 'replayed_initial', 'declined')
KEY = 'confirm-preview'
NOTE = '  원래 질문의 답\n    keep whitespace\n'
STAMP = {'io.modelcontextprotocol/serverInfo': {'name': 'stdio-round-restart-fixture', 'version': ''}}
SCHEMA = {'type': 'object', 'properties': {'yes': {'type': 'boolean'}, 'note': {'type': 'string'}}, 'required': ['yes', 'note']}
PINS = {'langchain': '1.4.0', 'langchain-core': '1.6.2', 'langgraph': '1.2.11',
        'fastmcp': '4.0.1', 'mcp': '2.1.1', 'langgraph-checkpoint-sqlite': '3.1.1'}
PROBE = 'contributions/stdio-round-restart/stdio_restart_probe.py'
GRAPH = 'contributions/preserved-mcp-rounds/round_graph.py'


def need(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def equal(a: object, b: object, code: str) -> None:
    # JSON booleans must not compare equal to numeric 0/1.
    need(canonical(a) == canonical(b), code)


def strict_json(raw: str | bytes) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def safe_name(name: str) -> None:
    path = PurePosixPath(name)
    need(bool(name) and not path.is_absolute() and str(path) == name and
         '..' not in path.parts and '\\' not in name and ':' not in name, 'UNSAFE_PATH')


def load_capsule(path: Path) -> dict:
    need(path.stat().st_size <= MAX_INPUT, 'CAPSULE_TOO_LARGE')
    outer = strict_json(path.read_bytes())
    need(set(outer) == {'format', 'encoding', 'payload_bytes', 'payload_sha256', 'notice', 'payload'}, 'CAPSULE_FIELDS')
    need(outer['format'] == 'second-paddle-record-members/v1' and outer['encoding'] == 'zlib+base64', 'CAPSULE_FORMAT')
    need(type(outer['payload_bytes']) is int and outer['payload_bytes'] == PAYLOAD_BYTES and
         outer['payload_sha256'] == PAYLOAD_SHA256, 'CAPSULE_PIN')
    packed = base64.b64decode(outer['payload'], validate=True)
    stream = zlib.decompressobj()
    raw = stream.decompress(packed, MAX_EXPANDED + 1)
    need(len(raw) <= MAX_EXPANDED, 'EXPANSION_LIMIT')
    need(stream.eof and not stream.unused_data and not stream.unconsumed_tail, 'COMPRESSED_STREAM')
    need(len(raw) == PAYLOAD_BYTES and digest(raw) == PAYLOAD_SHA256, 'PAYLOAD_IDENTITY')
    packet = strict_json(raw)
    need(packet['schema'] == 1 and packet['source_ref'] == 'f795eeaad68895d4aacd1955ac137335e7898eac', 'PACKET_IDENTITY')
    return packet


def verify_sources(packet: dict, repo: Path) -> dict:
    root = repo.resolve()
    result = {}
    need(len(packet['source_files']) == 5, 'SOURCE_COUNT')
    for name, pin in packet['source_files'].items():
        safe_name(name)
        path = (root / name).resolve()
        need(root in path.parents, 'SOURCE_OUTSIDE_ROOT')
        need(path.is_file() and path.stat().st_size == pin['bytes'], 'SOURCE_SIZE')
        raw = path.read_bytes()
        sha = digest(raw)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        need(sha == pin['sha256'] and blob == pin['git_blob'], 'SOURCE_IDENTITY')
        result[name] = sha
    return result


def verify_member_bytes(archive: dict) -> None:
    members = archive['members']
    need(set(members) == set(archive['member_sha256']), 'MEMBER_SET')
    for name, text in members.items():
        safe_name(name)
        need(type(text) is str, 'MEMBER_TEXT')
        need(digest(text.encode('utf-8')) == archive['member_sha256'][name], 'MEMBER_IDENTITY')
        if name.endswith('.json'):
            strict_json(text)
        elif name.endswith('.jsonl'):
            for line in text.splitlines():
                strict_json(line)


def positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def verify_case(row: dict, sources: dict) -> dict:
    case = row['case']
    need(case in CASES, 'CASE_NAME')
    a, b = row['client_a'], row['client_b']
    logs = row['server_logs']
    need(len(logs) == 2, 'SERVER_LOG_COUNT')
    pids = [a['pid'], b['pid'], logs[0][0]['pid'], logs[1][0]['pid']]
    need(all(positive_int(x) for x in pids) and len(set(pids)) == 4, 'PROCESS_IDS')
    times = [a['monotonic_ns'], logs[0][0]['monotonic_ns'], logs[0][-1]['monotonic_ns'],
             row['a_exited_monotonic_ns'], b['monotonic_ns'], logs[1][0]['monotonic_ns'], logs[1][-1]['monotonic_ns']]
    need(all(positive_int(x) for x in times) and all(x < y for x, y in zip(times, times[1:])), 'PROCESS_ORDER')
    equal(row['returncodes'], [0, 0], 'EXIT_CODES')
    need(row['verified'] is True, 'ROW_STATUS')
    for process in (a, b, logs[0][0], logs[1][0]):
        equal(process['versions'], PINS, 'PACKAGE_VERSIONS')
        need(process['probe_sha256'] == sources[PROBE], 'RECORDED_PROBE_SOURCE')
    for client in (a, b):
        need(client['graph_sha256'] == sources[GRAPH], 'RECORDED_GRAPH_SOURCE')
        need(client['protocol_version'] == '2026-07-28', 'PROTOCOL_VERSION')
        equal(client['network_attempts'], [], 'CLIENT_NETWORK')
    for index, log in enumerate(logs):
        expected = ['start', 'call', 'call', 'exit'] if case == 'replayed_initial' and index == 1 else ['start', 'call', 'exit']
        equal([entry['event'] for entry in log], expected, 'SERVER_EVENTS')
        need(all(entry['pid'] == log[0]['pid'] for entry in log), 'SERVER_PROCESS_ID')
        equal(log[-1]['network_attempts'], [], 'SERVER_NETWORK')
    equal(a['frame'], b['reopened_frame'], 'FRAME_CHANGED')
    frame = a['frame']['value']
    need(a['frame']['kind'] == 'input', 'FRAME_KIND')
    request = frame['inputRequests'][KEY]
    need(len(frame['inputRequests']) == 1, 'QUESTION_COUNT')
    equal(request, {'method': 'elicitation/create', 'params': {'mode': 'form',
          'message': 'Preview draft-1? 한글 표본', 'requestedSchema': SCHEMA}}, 'ORIGINAL_QUESTION')
    equal(a['shown'], {'type': 'mcp_form_review', 'tool_name': 'preview', 'round_index': 1,
          'requests': [{'key': KEY, 'mode': 'form', 'message': 'Preview draft-1? 한글 표본', 'requested_schema': SCHEMA}]}, 'DISPLAYED_QUESTION')
    token = frame['requestState']
    need(type(token) is str and token.startswith('fixture-') and token not in canonical(a['shown']), 'OPAQUE_STATE')
    need(len(a['calls']) == 1 and len(b['calls']) == (2 if case == 'replayed_initial' else 1), 'CALL_COUNT')
    equal(a['calls'][0], {'name': 'preview', 'arguments': {'case': case}, 'request_state': None,
                         'input_responses': {}, 'result': frame}, 'INITIAL_CALL')
    answer = {KEY: {'action': 'decline'}} if case == 'declined' else {KEY: {'action': 'accept', 'content': {'yes': True, 'note': NOTE}}}
    equal(b['supplied_answer'], {'responses': answer}, 'SUPPLIED_ANSWER')
    equal(b['calls'][-1]['input_responses'], answer, 'TRANSMITTED_ANSWER')
    equal(b['result'], b['calls'][-1]['result'], 'TERMINAL_CALL_MISMATCH')
    calls = a['calls'] + b['calls']
    server_calls = [entry for log in logs for entry in log if entry['event'] == 'call']
    need(len(calls) == len(server_calls), 'WIRE_CALL_COUNT')
    for sent, received in zip(calls, server_calls):
        need(sent['name'] == 'preview', 'TOOL_NAME')
        equal(sent['arguments'], {'case': case}, 'TOOL_ARGUMENTS')
        for field in ('name', 'arguments', 'request_state', 'input_responses'):
            equal(sent[field], received[field], 'WIRE_REQUEST_' + field.upper())
        equal(sent['result'].get('_meta'), STAMP, 'SERVER_STAMP')
        need('_meta' not in received['result'], 'HANDLER_METADATA')
        equal({k: v for k, v in sent['result'].items() if k != '_meta'}, received['result'], 'WIRE_RESULT_BODY')
    equal(server_calls[0]['snapshot'], {'rounds': [[1, token, 'pending']], 'effects': []}, 'INITIAL_SERVER_RECORD')
    if case == 'replayed_initial':
        replacement = b['replacement_question']
        new_token = replacement['requestState']
        need(new_token != token and b['calls'][0]['request_state'] is None, 'REPLAY_CONTROL_STATE')
        equal(b['calls'][0]['input_responses'], {}, 'REPLAY_INITIAL_ANSWER')
        equal(b['calls'][0]['result'], replacement, 'REPLACEMENT_RESULT')
        equal(replacement['inputRequests'][KEY]['params'], {'mode': 'form', 'message': 'Preview draft-2? 한글 표본', 'requestedSchema': SCHEMA}, 'REPLACEMENT_QUESTION')
        need(b['calls'][1]['request_state'] == new_token, 'REPLAY_CONTINUATION')
        expected_snapshot = {'rounds': [[1, token, 'pending'], [2, new_token, 'accept']], 'effects': [[new_token, 'draft-2']]}
        text, error, status = 'previewed:draft-2', False, 'naive_control_returned'
    else:
        need(b['calls'][0]['request_state'] == token, 'ORIGINAL_CONTINUATION')
        text, error, status = {'preserved': ('previewed:draft-1', False, 'completed'),
                              'lost_server_state': ('UNKNOWN_ROUND', True, 'tool_error'),
                              'declined': ('skipped:decline', False, 'completed')}[case]
        expected_snapshot = {'rounds': [], 'effects': []} if case == 'lost_server_state' else {
            'rounds': [[1, token, 'decline' if case == 'declined' else 'accept']],
            'effects': [] if case == 'declined' else [[token, 'draft-1']]}
    equal(server_calls[-1]['snapshot'], expected_snapshot, 'FINAL_SERVER_RECORD')
    equal(b['result'], {'_meta': STAMP, 'content': [{'type': 'text', 'text': text}], 'isError': error, 'resultType': 'complete'}, 'TERMINAL_RESULT')
    need(b['status'] == status, 'TERMINAL_STATUS')
    return {'case': case, 'tool_calls': len(calls), 'terminal_text': text, 'is_error': error,
            'labels': len(expected_snapshot['effects']), 'pids': pids}


def verify_packet(packet: dict, repo: Path) -> dict:
    sources = verify_sources(packet, repo)
    for archive in packet['archives'].values():
        verify_member_bytes(archive)
    success, failed = packet['archives']['successful'], packet['archives']['first_failed']
    need(len(success['members']) == 32 and len(failed['members']) == 10, 'ARCHIVE_MEMBER_COUNTS')
    members = success['members']
    report = strict_json(members['stdio-evidence/observations.json'])
    need(report['status'] == 'verified', 'SUCCESS_REPORT_STATUS')
    equal([r['case'] for r in report['cases']], list(CASES), 'CASE_ORDER')
    results = []
    for row in report['cases']:
        prefix = 'stdio-evidence/' + row['case'] + '/'
        for phase in ('a', 'b'):
            equal(row['client_' + phase], strict_json(members[prefix + 'client-' + phase + '.json']), 'CLIENT_SUMMARY')
            equal(row['server_logs'][0 if phase == 'a' else 1], [strict_json(line) for line in members[prefix + 'server-' + phase + '.jsonl'].splitlines()], 'SERVER_SUMMARY')
        equal(strict_json(members[prefix + 'process-order.json']), {'a_exited_monotonic_ns': row['a_exited_monotonic_ns'], 'returncodes': row['returncodes']}, 'ORDER_SUMMARY')
        results.append(verify_case(row, sources))
    dependencies = members['stdio-dependencies.txt'].splitlines()
    need(all(name + '==' + version in dependencies for name, version in PINS.items()), 'DEPENDENCY_LOG')
    need('Ran 19 tests' in members['stdio-unit.log'] and members['stdio-unit.log'].rstrip().endswith('OK'), 'HISTORICAL_UNIT_LOG')
    failure = strict_json(failed['members']['stdio-evidence/observations.json'])
    need(failure['status'] == 'failed' and failure['cases'] == [], 'FAILURE_RELABELED')
    failed_b = strict_json(failed['members']['stdio-evidence/preserved/client-b.json'])
    need(failed_b['result']['content'][0]['text'] == 'previewed:draft-1', 'FAILURE_PARTIAL_RESULT')
    return {'status': 'verified', 'scope': 'Offline evidence inspection, not a new MCP experiment or independent certification',
            'retained_members': 42, 'source_files_checked': len(sources), 'cases': results,
            'historical_tool_calls': sum(x['tool_calls'] for x in results), 'historical_unit_tests': 19,
            'failure_preserved_as_failure': True, 'source_ref': packet['source_ref'], 'payload_sha256': PAYLOAD_SHA256}


def compare_original_zip(packet: dict, path: Path) -> int:
    need(path.stat().st_size <= MAX_INPUT, 'ZIP_TOO_LARGE')
    raw = path.read_bytes()
    matches = [a for a in packet['archives'].values() if a['original_zip_sha256'] == digest(raw)]
    need(len(matches) == 1, 'UNKNOWN_ORIGINAL_ZIP')
    archive = matches[0]
    need(len(raw) == archive['original_zip_bytes'], 'ZIP_SIZE')
    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
        names = zipped.namelist()
        need(len(names) == len(set(names)) and set(names) == set(archive['members']), 'ZIP_MEMBER_SET')
        need(sum(info.file_size for info in zipped.infolist()) < MAX_EXPANDED, 'ZIP_EXPANSION_LIMIT')
        need(zipped.testzip() is None, 'ZIP_CRC')
        for name in names:
            need(zipped.read(name) == archive['members'][name].encode('utf-8'), 'ZIP_MEMBER_BYTES')
    return archive['artifact_id']


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capsule', type=Path, default=Path(__file__).with_name('records.capsule.json'))
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--original-zip', action='append', type=Path, default=[])
    args = parser.parse_args()
    try:
        packet = load_capsule(args.capsule)
        result = verify_packet(packet, args.repo_root)
        result['original_zip_ids_compared'] = [compare_original_zip(packet, path) for path in args.original_zip]
    except (ValueError, KeyError, TypeError, OSError, RecursionError, zlib.error, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'rejected', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
