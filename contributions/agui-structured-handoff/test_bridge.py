from copy import deepcopy
import unittest
from bridge import KEY, result_metadata

class BridgeTests(unittest.TestCase):
    def test_retains_empty_object(self):
        self.assertEqual(result_metadata({'structuredContent': {}})[KEY]['structuredContent'], {})
    def test_preserves_values(self):
        value={'a': [], 'b':False,'c':0,'d':None,'e':'  한글\n    keep\n'}
        self.assertEqual(result_metadata({'structuredContent':value})[KEY]['structuredContent'],value)
    def test_preserves_error(self):
        self.assertIs(result_metadata({'structuredContent':{},'isError':True})[KEY]['isError'],True)
    def test_absence_is_not_empty(self):
        self.assertNotIn(KEY,result_metadata({'content':[]}))
    def test_selects_not_whole_response(self):
        m=result_metadata({'structuredContent':{},'_meta':{'secret':'PRIVATE'},'other':'PRIVATE'})
        self.assertNotIn('PRIVATE',str(m))
    def test_source_is_independent(self):
        r={'structuredContent':{'x':[1]}}; e={'app':{'x':[2]}}; before=deepcopy((r,e))
        m=result_metadata(r,e);m[KEY]['structuredContent']['x'].append(3);m['app']['x'].append(4)
        self.assertEqual((r,e),before)
    def test_collision_rejected(self):
        with self.assertRaises(ValueError):result_metadata({'structuredContent':{}},{KEY:{}})
    def test_invalid_result_rejected(self):
        for r in [{'structuredContent':[]},{'structuredContent':{'n':float('nan')}},{'isError':'false'}]:
            with self.subTest(result=r),self.assertRaises(ValueError):result_metadata(r)
if __name__=='__main__':unittest.main()
