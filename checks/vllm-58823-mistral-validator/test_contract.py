"""Regression suggestions using real mistral-common 1.11.7 validators."""
from copy import deepcopy
import probe

def test_image_only_v13_rejects_before_accepts_after():
    messages=probe.conversation([deepcopy(probe.IMAGE)])
    assert probe.check(messages,13)['error']=='InvalidToolMessageException'
    adapted=probe.adapt(messages,13)
    assert probe.check(adapted,13)=={'accepted':True}
    assert adapted[2]['content']==[]
    assert adapted[-1]['content']==[probe.IMAGE]

def test_v15_is_identity_and_validates_image_in_tool():
    messages=probe.conversation([deepcopy(probe.IMAGE)])
    assert probe.adapt(messages,15) is messages
    assert probe.check(messages,15)=={'accepted':True}

def test_mixed_content_retains_existing_user_text():
    parts=[{'type':'text','text':'before'},deepcopy(probe.IMAGE),{'type':'text','text':'after'}]
    messages=probe.conversation(parts,[{'role':'user','content':'Compare the results.'}])
    adapted=probe.adapt(messages,13)
    assert probe.check(adapted,13)=={'accepted':True}
    assert adapted[2]['content']==[parts[0],parts[2]]
    assert adapted[-1]['content']==[probe.IMAGE,{'type':'text','text':'Compare the results.'}]

def test_repeat_adaptation_is_idempotent_without_source_mutation():
    messages=probe.conversation([deepcopy(probe.IMAGE)])
    snapshot=deepcopy(messages);adapted=probe.adapt(messages,13)
    assert messages==snapshot
    assert probe.adapt(adapted,13)==adapted

def test_duplicate_result_id_remains_rejected():
    messages=probe.conversation([deepcopy(probe.IMAGE)])
    messages[-1]['tool_call_id']='abc123XYZ'
    result=probe.check(probe.adapt(messages,13),13)
    assert not result['accepted']
    assert result['error']=='InvalidMessageStructureException'
    assert 'Duplicate tool call id' in result['message']

def test_missing_parallel_result_remains_rejected_in_serving_mode():
    messages=probe.conversation([deepcopy(probe.IMAGE)])[:-1]
    result=probe.check(probe.adapt(messages,13),13)
    assert not result['accepted']
    assert result['error']=='InvalidMessageStructureException'
    assert 'Not the same number' in result['message']

def test_unknown_tool_result_id_remains_rejected():
    messages=probe.conversation([deepcopy(probe.IMAGE)])
    messages[-1]['tool_call_id']='ghi789RST'
    result=probe.check(probe.adapt(messages,13),13)
    assert not result['accepted']
    assert 'Unexpected tool call id' in result['message']
