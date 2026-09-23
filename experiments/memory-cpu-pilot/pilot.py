"""Development feasibility pilot for Second Paddle Note 14, NOT its full study.

Frozen before inference: one Qwen2.5-0.5B-Instruct revision, eight authored
English fictional cases, three views each, one forced-choice forward pass per
case/view (24 total). No model fitting, sampling, prompt edits, exclusions, or
retries after answers. Stop on any runtime failure and retain prior records.

Views: chronological statements alone; SAME statements plus correct authored
interaction edges; SAME statements plus deliberately reversed edges. Reversing
edges is a corrupt-metadata stress test, not a realistic factual summary.
Edges are oracle annotations, not predictions by a memory encoder. Chronology
and edge conditions are NOT token matched. Report token counts; claim no causal
benefit, statistical significance, compression success, frontier-model result,
or personal-memory reconstruction. These public development cases cannot later
be labelled held-out. Primary outcome is execution feasibility; accuracies are
descriptive only. Public inferences use no real user's conversations or API key.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import resource
import socket
import sys
import time

MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'
VIEWS = ('chronology', 'correct_edges', 'reversed_edges')
SYSTEM = ('Read the fictional conversation and select the answer best supported '
          'by the USER statements. Assistant suggestions are not user choices. '
          'Later explicit user corrections replace earlier choices. Do not invent '
          'missing facts. Optional relationship metadata may be imperfect; the '
          'statements are the source. Reply with only A, B, or C.')

# Statements, options and labels are authored fixtures, not memories of a person.
CASES = [
 {'id':'permission_cancel','messages':[
  ['user','Publish the project note after formatting it.'],
  ['assistant','I plan to publish it.'],
  ['user','I changed my mind. Do not publish the note. Keep it private.'],
  ['assistant','My earlier plan still says to publish.']],
  'edge':['e3','supersedes','e1'],
  'question':'What is the current user decision about publishing the note?',
  'answers':['Keep the note private.','Publish the note.','No decision was ever given.'],'gold':0},
 {'id':'permission_restore','messages':[
  ['user','Keep the project note private.'],
  ['assistant','I suggest publishing it.'],
  ['user','I changed my mind. Publish the note after formatting it.'],
  ['assistant','My earlier plan still says to keep it private.']],
  'edge':['e3','supersedes','e1'],
  'question':'What is the current user decision about publishing the note?',
  'answers':['Keep the note private.','Publish the note.','No decision was ever given.'],'gold':1},
 {'id':'suggestion_rejected','messages':[
  ['user','I have not chosen a meeting time.'],
  ['assistant','I recommend the morning.'],
  ['user','That is only your suggestion. I have not selected a time.']],
  'edge':['e3','rejects','e2'],
  'question':'What meeting time has the user selected?',
  'answers':['Morning.','Afternoon.','No time has been selected.'],'gold':2},
 {'id':'suggestion_adopted','messages':[
  ['user','I have not chosen a meeting time.'],
  ['assistant','I recommend the morning.'],
  ['user','I accept that suggestion. I select the morning.']],
  'edge':['e3','accepts','e2'],
  'question':'What meeting time has the user selected?',
  'answers':['Morning.','Afternoon.','No time has been selected.'],'gold':0},
 {'id':'temporary_step','messages':[
  ['user','Create the slides and then send them to the team.'],
  ['assistant','I could stop after an outline.'],
  ['user','Make the outline first, but then finish the slides and send them.'],
  ['assistant','The outline is complete.']],
  'edge':['e3','retains','e1'],
  'question':'After the outline, what does the user still want done?',
  'answers':['Stop with the outline only.','Finish the slides and send them.','Delete the outline.'],'gold':1},
 {'id':'goal_replaced','messages':[
  ['user','Create the slides and then send them to the team.'],
  ['assistant','I could stop after an outline.'],
  ['user','Change the task: only make an outline. Do not make or send slides.'],
  ['assistant','The outline is complete.']],
  'edge':['e3','supersedes','e1'],
  'question':'After the outline, what does the user still want done?',
  'answers':['Send full slides now.','Delete the outline.','Nothing further; keep only the outline.'],'gold':2},
 {'id':'past_preference_unknown','messages':[
  ['user','I have not told you which instrument I preferred as a child.'],
  ['assistant','My guess is the violin.'],
  ['user','That guess is not evidence about my past.']],
  'edge':['e3','rejects','e2'],
  'question':'Which childhood instrument preference is established by the user?',
  'answers':['It is not established.','Violin.','Piano.'],'gold':0},
 {'id':'past_preference_confirmed','messages':[
  ['user','I have not told you which instrument I preferred as a child.'],
  ['assistant','My guess is the violin.'],
  ['user','I can confirm it now: I preferred the violin as a child.']],
  'edge':['e3','confirms','e2'],
  'question':'Which childhood instrument preference is established by the user?',
  'answers':['It is not established.','Violin.','Piano.'],'gold':1},
]

def digest(value: bytes) -> str:
 return hashlib.sha256(value).hexdigest()

def prompts(case: dict, view: str) -> list[dict]:
 lines = [f'e{i} {role.upper()}: {text}' for i,(role,text) in enumerate(case['messages'],1)]
 memory = '\n'.join(lines)
 if view != 'chronology':
  left, relation, right = case['edge']
  if view == 'reversed_edges':
   left, right = right, left
  memory += f'\nRelationship metadata: {left} {relation} {right}.'
 options = '\n'.join(f'{letter}. {answer}' for letter,answer in zip('ABC',case['answers']))
 return [{'role':'system','content':SYSTEM},
         {'role':'user','content':f'Conversation in time order:\n{memory}\n\nQuestion: {case["question"]}\n{options}\nSelect one letter.'}]

def selftest() -> None:
 assert len(CASES)==8 and len({c['id'] for c in CASES})==8
 assert Counter(c['gold'] for c in CASES)=={0:3,1:3,2:2}
 for case in CASES:
  assert len(case['answers'])==3 and 0<=case['gold']<3
  ids={f'e{i}' for i in range(1,len(case['messages'])+1)}
  assert case['edge'][0] in ids and case['edge'][2] in ids
  for view in VIEWS:
   text=prompts(case,view)[1]['content']
   for role,statement in case['messages']:
    assert text.count(statement)==1
   assert 'gold' not in text and case['id'] not in text
 print('FIXTURE_SELFTEST_OK',flush=True)

def main() -> int:
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--selftest',action='store_true')
 parser.add_argument('--out',type=Path,default=Path('pilot-output'))
 args=parser.parse_args()
 selftest()
 if args.selftest: return 0
 import torch
 from huggingface_hub import snapshot_download
 from transformers import AutoTokenizer, AutoModelForCausalLM
 torch.set_num_threads(2)
 torch.set_num_interop_threads(1)
 torch.manual_seed(0)
 torch.use_deterministic_algorithms(True)
 args.out.mkdir(parents=True,exist_ok=False)
 started=time.monotonic()
 report={'model':MODEL,'revision':REVISION,'protocol':'development-feasibility-v1',
  'started_utc':datetime.now(timezone.utc).isoformat(),'planned_inferences':24,
  'cpu_threads':2,'dtype':'float32','gpu_used':False,'sampling':False,'seed':0,
  'measurement':'next-token choice among A/B/C, not unconstrained generated answers',
  'script_sha256':digest(Path(__file__).read_bytes()),
  'fixture_sha256':digest(json.dumps(CASES,sort_keys=True).encode()),
  'versions':{p:importlib.metadata.version(p) for p in ['torch','transformers','huggingface-hub','tokenizers','safetensors']},
  'rows':[],'success':False,
  'limits':['eight author-created development cases','one small model','no hidden set',
   'oracle rather than extracted edges','views not token-matched','fixed answer order',
   'corrupt edges are a stress test','no independence or real-user-memory claim']}
 try:
  path=snapshot_download(MODEL,revision=REVISION,token=False,max_workers=2,
   allow_patterns=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','model.safetensors','LICENSE'])
  report['weight_sha256']=digest((Path(path)/'model.safetensors').read_bytes())
  tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
  model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,
    use_safetensors=True,torch_dtype=torch.float32,attn_implementation='eager').eval()
  assert next(model.parameters()).device.type=='cpu'
  report['parameter_count']=sum(p.numel() for p in model.parameters())
  choices=[tokenizer.encode(letter,add_special_tokens=False) for letter in 'ABC']
  assert all(len(x)==1 for x in choices)
  choice_ids=[x[0] for x in choices]
  def block_network(*unused,**unused_kw):
   raise RuntimeError('No network is needed during inference')
  socket.socket.connect=socket.socket.connect_ex=block_network
  order=[(i,view) for i in range(8) for view in VIEWS]
  random.Random(20260924).shuffle(order)
  report['execution_order']=order
  inference_start=time.monotonic()
  with (args.out/'raw.jsonl').open('w',encoding='utf-8') as raw:
   for number,(i,view) in enumerate(order):
    case=CASES[i]
    messages=prompts(case,view)
    rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    inputs=tokenizer(rendered,return_tensors='pt')
    assert inputs.input_ids.shape[1]<=768
    t=time.monotonic()
    with torch.inference_mode():
     output=model(**inputs,use_cache=False)
     logits=output.logits[0,-1].float()
     logprobs=torch.log_softmax(logits,dim=-1)
     values=logits[choice_ids]
     probabilities=torch.softmax(values,dim=-1).tolist()
     selected=int(values.argmax())
     row={'ordinal':number,'case':case['id'],'view':view,'messages':messages,
      'rendered_prompt':rendered,'input_ids_sha256':digest(json.dumps(inputs.input_ids[0].tolist()).encode()),
      'input_tokens':int(inputs.input_ids.shape[1]),'choice_ids':choice_ids,
      'choice_logits':values.tolist(),'choice_logprobs_full_vocab':logprobs[choice_ids].tolist(),
      'conditional_choice_probabilities':probabilities,
      'choice_probability_mass':float(logprobs[choice_ids].exp().sum()),
      'unconstrained_next_token':tokenizer.decode([int(logits.argmax())]),
      'selected':'ABC'[selected],'expected':'ABC'[case['gold']],
      'correct':selected==case['gold'],'elapsed_seconds':round(time.monotonic()-t,3)}
     del output,logits,logprobs,values
    report['rows'].append(row)
    raw.write(json.dumps(row,ensure_ascii=False)+'\n');raw.flush()
    print('MEMORY_PILOT_ROW '+json.dumps(row,ensure_ascii=False),flush=True)
  report['inference_seconds']=round(time.monotonic()-inference_start,3)
  report['counts']={view:{'correct':sum(r['correct'] for r in report['rows'] if r['view']==view),
   'total':sum(r['view']==view for r in report['rows'])} for view in VIEWS}
  report['success']=len(report['rows'])==24
 except Exception as exc:
  report['error']={'type':type(exc).__name__,'message':str(exc)[:2000]}
 finally:
  report['total_seconds']=round(time.monotonic()-started,3)
  report['max_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  report['ended_utc']=datetime.now(timezone.utc).isoformat()
  (args.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
  summary={k:v for k,v in report.items() if k!='rows'}
  print('MEMORY_PILOT_SUMMARY '+json.dumps(summary,ensure_ascii=False),flush=True)
 return 0 if report['success'] else 1

if __name__=='__main__':
 raise SystemExit(main())
