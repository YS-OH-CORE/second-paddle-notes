"""Exact official-tokenizer check of a modern-response to HF-template boundary.

All response-shaped messages are synthetic fixtures, not generated answers.
Youngseok Oh x Zero, AI collaboration partners.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import unittest
from history_bridge import to_hf_template_message

MODEL = 'Qwen/Qwen3.8-27B'
REVISION = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
OLD = 'OLD_TRACE_SENTINEL: Earlier the user requested publication.'
CURRENT = 'CURRENT_TRACE_SENTINEL: Check the stored status before answering.'
CORRECTION = 'I withdraw publication permission. Keep this item private.'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class AdapterTests(unittest.TestCase):
    def test_modern(self):
        self.assertEqual(to_hf_template_message({'role':'assistant','reasoning':'x','content':'y'}),
                         {'role':'assistant','reasoning_content':'x','content':'y'})
    def test_legacy(self):
        m={'role':'assistant','reasoning_content':'x','content':'y'}
        self.assertEqual(to_hf_template_message(m),m)
    def test_same_aliases(self):
        self.assertEqual(to_hf_template_message({'role':'assistant','reasoning':'x','reasoning_content':'x'})['reasoning_content'],'x')
    def test_conflict(self):
        with self.assertRaises(ValueError):
            to_hf_template_message({'role':'assistant','reasoning':'x','reasoning_content':'z'})
    def test_empty_and_missing(self):
        for value in ('',None):
            self.assertEqual(to_hf_template_message({'role':'assistant','reasoning':value})['reasoning_content'],'')
        self.assertEqual(to_hf_template_message({'role':'assistant','content':'x'}),{'role':'assistant','content':'x'})
    def test_no_input_mutation(self):
        m={'role':'assistant','reasoning':'x','tool_calls':[{'id':'1'}]}; original=deepcopy(m)
        n=to_hf_template_message(m);n['tool_calls'][0]['id']='2'
        self.assertEqual(m,original)
    def test_non_assistant(self):
        m={'role':'user','content':CORRECTION}
        self.assertEqual(to_hf_template_message(m),m)
    def test_structured_not_silently_flattened(self):
        with self.assertRaises(TypeError):
            to_hf_template_message({'role':'assistant','reasoning':[{'text':'x'}]})
    def test_content_and_tools_preserved(self):
        m={'role':'assistant','content':'answer','reasoning':'x','tool_calls':[{'id':'call','function':{'name':'read_status','arguments':{}}}]}
        n=to_hf_template_message(m)
        self.assertEqual(n['content'],m['content']);self.assertEqual(n['tool_calls'],m['tool_calls'])


def fixtures(tool_turn):
    messages=[{'role':'system','content':'Track the latest user decision. This is a synthetic input-format test.'},
              {'role':'user','content':'Prepare publication of the fictional note.'},
              {'role':'assistant','content':'Publication is planned.','reasoning':OLD},
              {'role':'user','content':CORRECTION}]
    if tool_turn:
        messages += [{'role':'assistant','content':'','reasoning':CURRENT,
                      'tool_calls':[{'id':'call_status','type':'function',
                                     'function':{'name':'read_status','arguments':{}}}]},
                     {'role':'tool','tool_call_id':'call_status','content':'{"status":"PUBLIC"}'}]
    return messages


def render_matrix(render):
    rows=[]
    for tool_turn in (False,True):
        for preserve in (False,True):
            modern=fixtures(tool_turn)
            legacy=deepcopy(modern)
            for m in legacy:
                if 'reasoning' in m:m['reasoning_content']=m.pop('reasoning')
            adapted=[to_hf_template_message(m) for m in modern]
            assert adapted==legacy
            for representation,messages in [('modern_direct',modern),('legacy_direct',legacy),('adapted',adapted)]:
                text,ids=render(messages,preserve)
                rows.append({'tool_turn':tool_turn,'preserve':preserve,'representation':representation,
                             'old_reasoning_retained':OLD in text,'current_reasoning_retained':CURRENT in text,
                             'latest_correction_count':text.count(CORRECTION),
                             'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                             'messages':messages,'rendered':text,'token_ids':ids})
    return rows


def analyze(rows):
    assert len(rows)==12
    for row in rows:
        assert row['latest_correction_count']==1
        assert row['text_sha256']==hashlib.sha256(row['rendered'].encode()).hexdigest()
    groups=[]
    for tool_turn in (False,True):
        for preserve in (False,True):
            group={r['representation']:r for r in rows if r['tool_turn']==tool_turn and r['preserve']==preserve}
            modern,legacy,adapted=[group[k] for k in ('modern_direct','legacy_direct','adapted')]
            assert legacy['rendered']==adapted['rendered'] and legacy['token_ids']==adapted['token_ids']
            assert legacy['old_reasoning_retained']==preserve
            assert legacy['current_reasoning_retained']==tool_turn
            groups.append({'tool_turn':tool_turn,'preserve':preserve,
                           'modern_old_retained':modern['old_reasoning_retained'],
                           'modern_current_retained':modern['current_reasoning_retained'],
                           'adapted_old_retained':adapted['old_reasoning_retained'],
                           'adapted_current_retained':adapted['current_reasoning_retained'],
                           'adapted_equals_legacy_text_and_tokens':True})
    return {'renderings':12,'fixtures':2,'adapter_matches_expected_legacy_representation':True,
            'all_latest_corrections_preserved':True,'groups':groups,
            'model_forward_passes':0,'actual_generated_responses':0}


def run(out):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    out.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests))
    assert result.wasSuccessful()
    save(out/'UNIT_TESTS.json',{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)})
    assets=Path(snapshot_download(MODEL,revision=REVISION,token=False,local_dir=out/'assets',
        allow_patterns=['tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','config.json','chat_template.jinja','LICENSE'],max_workers=2))
    tokenizer=AutoTokenizer.from_pretrained(assets,local_files_only=True,trust_remote_code=False)
    assets_record={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.iterdir() if p.is_file()}
    attempts=[]
    def deny(*args,**kwargs):
        attempts.append('socket_or_dns');raise RuntimeError('No network during input construction')
    socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.getaddrinfo=deny
    def render(messages,preserve):
        kwargs={'add_generation_prompt':True,'enable_thinking':False,'preserve_thinking':preserve}
        text=tokenizer.apply_chat_template(messages,tokenize=False,**kwargs)
        tokens=tokenizer.apply_chat_template(messages,tokenize=True,return_dict=True,**kwargs)['input_ids']
        assert tokens==tokenizer.encode(text,add_special_tokens=False)
        return text,tokens
    rows=render_matrix(render)
    save(out/'OBSERVATIONS.json',rows);save(out/'SUMMARY.json',analyze(rows))
    save(out/'RUN.json',{'model':MODEL,'revision':REVISION,'run_id':os.getenv('GITHUB_RUN_ID'),
        'workflow_commit':os.getenv('GITHUB_SHA'),'assets':assets_record,'model_forward_passes':0,
        'versions':{p:importlib.metadata.version(p) for p in ('transformers','tokenizers','huggingface-hub','jinja2')},
        'network_attempts_during_rendering':attempts})
    print(json.dumps(analyze(rows)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    run(p.parse_args().out)
