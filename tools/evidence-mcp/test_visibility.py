"""Protocol-position checks, not a classifier for arbitrary secret content."""
from copy import deepcopy
import json
import unittest
from service import InputProblem, project_result

CANARY = 'HOST_BOUNDARY_SYNTHETIC_CANARY'

def base():
    return {'content': [], 'structuredContent': {'result': [], 'name': '  한글\n'}, 'isError': False}

def cases():
    top = base(); top['_meta'] = {'private': CANARY}
    block = {'content':[{'type':'text','text':'public','_meta':{'private':CANARY}}]}
    resource = {'content':[{'type':'resource','resource':{'uri':'memory://fixture','text':'public','_meta':{'private':CANARY}}}]}
    extra = base();extra['application_private_debug']=CANARY
    audience = {'content':[{'type':'text','text':CANARY,'annotations':{'audience':['user']}}]}
    annotation_extra = {'content':[{'type':'text','text':'public','annotations':{'private':CANARY}}]}
    literal = base();literal['structuredContent']={'_meta':{'public':'ordinary application key'},'text':'  한글\n','null':None,'zero':0,'false':False}
    quote = {'content':[{'type':'text','text':'{"_meta":"ordinary quoted text"}'}]}
    both = {'content':[{'type':'text','text':'public','annotations':{'audience':['user','assistant'],'priority':0.5}}]}
    error = base();error['isError']=True
    return [
        ('result_metadata',top,'HOST_METADATA_NOT_PROJECTABLE'),
        ('block_metadata',block,'HOST_METADATA_NOT_PROJECTABLE'),
        ('resource_metadata',resource,'HOST_METADATA_NOT_PROJECTABLE'),
        ('unselected_extra',extra,'NON_CONTENT_FIELDS'),
        ('user_only',audience,'NON_MODEL_AUDIENCE'),
        ('annotation_extra',annotation_extra,'NON_CONTENT_FIELDS'),
        ('normal',base(),None),('ordinary_meta_key',literal,None),('quoted_meta',quote,None),
        ('both_audiences',both,None),('absent',{'content':[]},None),('upstream_error',error,None),
    ]

class VisibilityTests(unittest.TestCase):
    def test_all_positions_and_positive_controls(self):
        for label, source, code in cases():
            with self.subTest(case=label):
                before=deepcopy(source)
                if code:
                    with self.assertRaises(InputProblem) as cm:project_result(source)
                    self.assertEqual(str(cm.exception),code)
                    self.assertNotIn(CANARY,str(cm.exception))
                else:
                    result=project_result(source)['result']
                    for key in source:
                        if key!='content':self.assertEqual(result[key],source[key])
                    if source['content']:self.assertEqual(result['content'],source['content'])
                self.assertEqual(source,before)
    def test_empty_declared_audience_is_not_promoted(self):
        with self.assertRaisesRegex(InputProblem,'NON_MODEL_AUDIENCE'):
            project_result({'content':[{'type':'text','text':'private','annotations':{'audience':[]}}]})
    def test_unknown_content_kind_not_coerced(self):
        with self.assertRaisesRegex(InputProblem,'UNSUPPORTED_CONTENT_BLOCK'):
            project_result({'content':[{'type':'future','private':CANARY}]})
    def test_image_and_audio_public_fields_stay_unchanged(self):
        for kind in ['image','audio']:
            r={'content':[{'type':kind,'data':'cHVibGlj','mimeType':kind+'/example'}]}
            self.assertEqual(project_result(r)['result'],r)
    def test_resource_link_and_embedded_resource(self):
        for r in [{'content':[{'type':'resource_link','name':'fixture','uri':'memory://fixture'}]},
                  {'content':[{'type':'resource','resource':{'uri':'memory://fixture','text':'public'}}]}]:
            self.assertEqual(project_result(r)['result'],r)

if __name__=='__main__':unittest.main()
