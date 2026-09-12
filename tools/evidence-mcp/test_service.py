"""Local tests do not require the SDK and do not stand in for MCP integration."""
import copy
import json
import unittest
from unittest.mock import patch
from service import InputProblem, check_trace, parse_result, project_result, source_identity, LIMIT


def trace(payload='  한글\n'):
    return {'schema':'approval-trace-v1', 'events':[
        {'type':'propose','request_id':'A','scope':'demo','payload':payload},
        {'type':'approve','request_id':'A','scope':'demo'},
        {'type':'execute','request_id':'A','scope':'demo','payload':payload}]}


class ServiceTests(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(len(source_identity()), 2)

    def test_valid_trace(self):
        report = check_trace(json.dumps(trace()))['report']
        self.assertEqual(report['status'], 'no_violation_observed')
        self.assertEqual(report['valid_execution_attempts'], 1)

    def test_mismatch_is_analysis_not_parser_failure(self):
        t = trace(); t['events'][-1]['payload'] = 'different'
        v = check_trace(json.dumps(t))
        self.assertTrue(v['ok'])
        self.assertEqual(v['report']['issues'][0]['code'], 'PAYLOAD_CHANGED')

    def test_duplicate_is_unassessed(self):
        raw = '{"schema":"approval-trace-v1","events":[],"events":[]}'
        v = check_trace(raw)
        self.assertFalse(v['ok']); self.assertEqual(v['error']['code'],'DUPLICATE_JSON_MEMBER')
        self.assertNotIn('report', v)

    def test_syntax_does_not_echo_input(self):
        v = check_trace('TOP_SECRET_CANARY invalid json')
        self.assertFalse(v['ok']); self.assertNotIn('TOP_SECRET', json.dumps(v))

    def test_no_execution_is_distinct(self):
        v=check_trace('{"schema":"approval-trace-v1","events":[]}')
        self.assertEqual(v['report']['status'],'no_execution_observed')

    def test_shell_looking_payload_stays_data(self):
        t=trace('$(touch /tmp/not-a-command); require("fs")')
        self.assertTrue(check_trace(json.dumps(t))['ok'])

    def test_size_and_unicode(self):
        for text in ('x'*(LIMIT+1), '\ud800'):
            with self.assertRaises(InputProblem): check_trace(text)

    def test_no_node_diagnostic(self):
        with patch('service.shutil.which', return_value=None):
            with self.assertRaisesRegex(InputProblem,'NODE_UNAVAILABLE'): check_trace('{}')

    def test_fallback_preserves_original(self):
        a={'content':[], 'structuredContent':{'result':[]}, 'isError':False}
        b=copy.deepcopy(a); v=project_result(parse_result(json.dumps(a)))
        self.assertEqual(v['result']['content'][0]['text'],'{"result":[]}')
        self.assertEqual(a,b); self.assertEqual(v['source'],'structured_content')

    def test_absent(self):
        self.assertEqual(project_result({'content':[]})['source'],'absent')

    def test_error(self):
        r=project_result({'content':[], 'structuredContent':{'error':'synthetic'}, 'isError':True})
        self.assertTrue(r['result']['isError'])

    def test_existing_empty_text_is_preserved(self):
        a={'content':[{'type':'text','text':''}], 'structuredContent':{'result':[]}}
        self.assertEqual(project_result(a)['result'],a)

    def test_duplicate_result_key_rejected(self):
        for raw in ('{"content":[],"content":[]}', '{"content":[],"cont\\u0065nt":[]}'):
            with self.assertRaisesRegex(InputProblem,'DUPLICATE_JSON_MEMBER'): parse_result(raw)

    def test_result_nonstandard_and_nonobject(self):
        for raw in ('[]','null','{"content":[],"structuredContent":{"n":NaN}}'):
            with self.assertRaises(InputProblem): parse_result(raw)

    def test_named_values_are_not_in_errors(self):
        with self.assertRaises(InputProblem) as cm:
            parse_result('{"sensitive_secret":1,"sensitive_secret":2}')
        self.assertNotIn('sensitive_secret', str(cm.exception))

if __name__=='__main__': unittest.main()
