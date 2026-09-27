"""Eight fixed diagnostic responses; not another feedback-effectiveness run.
--check uses only stdlib. --run uses pinned packages on a disposable hosted CPU.
No model outputs are executed. Existing task/scoring source stays unchanged.
"""
from pathlib import Path
import base64, gzip, hashlib, json, os, signal, socket, sys, time
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'v02'))
import observe as o

MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
REV = '7ae557604adf67be50417f59c2c2f167def9a775'
WEIGHTS = 'fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe'
FILES = ('config.json','generation_config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt','model.safetensors')
BAD = [0,1,2,3,4,5]
GOOD = {'G1':[0,1,0,1,0,1], 'G2':[0,1,2,1,2,0]}
COPY = [2,0,1,2,0,1]
FINAL = 'Return your final assignment for the original constraints. Keep an existing candidate only if it satisfies every constraint.'

def seed(a):
    return '```json\n{\n  "assignment": ['+', '.join(map(str,a))+']\n}\n```'

def cells():
    system={'role':'system','content':o.task.SYSTEM}
    rows=[{'id':'copy','case':{'id':'copy','edges':[]},'condition':'copy',
           'messages':[system,{'role':'user','content':'Copy this object exactly: '+json.dumps({'assignment':COPY})}]},
          {'id':'domain','case':{'id':'domain','edges':[]},'condition':'domain',
           'messages':[system,{'role':'user','content':'Construct a list of six integers. Each value must be 0, 1, or 2. Repetitions are allowed. There are no other constraints.'}]}]
    for index,case in enumerate(o.task.TASKS[:2]):
        for condition in (('fresh','bad_prior','valid_prior') if index==0 else ('valid_prior','bad_prior','fresh')):
            messages=[system,{'role':'user','content':o.task.prompt(case)}]
            if condition=='fresh':
                messages[-1]={'role':'user','content':messages[-1]['content']+'\n'+FINAL}
            else:
                messages += [{'role':'assistant','content':seed(BAD if condition=='bad_prior' else GOOD[case['id']])},
                             {'role':'user','content':FINAL}]
            rows.append({'id':case['id']+'/'+condition,'case':case,'condition':condition,'messages':messages})
    return rows

def check():
    rows=cells()
    assert len(rows)==len({x['id'] for x in rows})==8
    for case in o.task.TASKS[:2]:
        good=o.observe(seed(GOOD[case['id']]),case);bad=o.observe(seed(BAD),case)
        assert good['candidate_feasible'] and not bad['candidate_feasible']
        assert not good['strict']['feasible']  # fence is never silently accepted
        pair=[r for r in rows if r['case']['id']==case['id'] and r['condition']!='fresh']
        assert pair[0]['messages'][:2]==pair[1]['messages'][:2]
        assert pair[0]['messages'][3:]==pair[1]['messages'][3:]
        assert len(pair[0]['messages'][2]['content'].encode())==len(pair[1]['messages'][2]['content'].encode())
    assert o.observe(json.dumps({'assignment':COPY}),rows[0]['case'])['candidate_feasible']
    assert o.observe(json.dumps({'assignment':[0]*6}),rows[1]['case'])['candidate_feasible']
    assert o.observe(seed(BAD),rows[1]['case'])['out_of_domain']
    return {'cells':8,'fixed_valid_seeds_checked':2,'fixed_invalid_seeds_checked':2,
            'matched_prior_messages_except_values':True,'old_acceptance_retained':True}

def emit(kind,obj):
    print('ADEQUACY_'+kind+' '+json.dumps(obj,ensure_ascii=False,separators=(',',':')),flush=True)

def summarize(rows):
    expected={c['id'] for c in cells()}
    if len(rows)!=8 or {r['id'] for r in rows}!=expected:raise ValueError('Incomplete or duplicate inventory')
    by={r['id']:r for r in rows}
    return {'new_generations':8,'copy_candidate_exact':by['copy']['observation']['candidate']==COPY,
            'domain_control_feasible':by['domain']['observation']['candidate_feasible'],
            'graph_candidate_feasible':{c:sum(by[t+'/'+c]['observation']['candidate_feasible'] for t in GOOD)
                                         for c in ('fresh','bad_prior','valid_prior')},
            'denominator_per_graph_condition':2,
            'strict_feasible_by_id':{k:v['observation']['strict']['feasible'] for k,v in by.items()},
            'same_raw_for_valid_and_bad':{t:by[t+'/valid_prior']['raw']==by[t+'/bad_prior']['raw'] for t in GOOD}}

def blocked(*_,**__):raise RuntimeError('Network blocked during evaluation')
def deadline(*_):raise TimeoutError('480-second run ceiling')

def run():
    signal.signal(signal.SIGALRM,deadline);signal.alarm(480)
    os.environ.update(HF_HUB_DISABLE_TELEMETRY='1',HF_HUB_DISABLE_XET='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',
                      DO_NOT_TRACK='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    for name in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','OPENAI_API_KEY'):os.environ.pop(name,None)
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for name,digest in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Source drift')
    emit('CHECK',check())
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer,AutoModelForCausalLM,GenerationConfig
    from importlib.metadata import version
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(2709)
    local=Path(snapshot_download(MODEL,revision=REV,allow_patterns=list(FILES),token=False,max_workers=2,
               local_dir=Path(os.environ['RUNNER_TEMP'])/'adequacy-model'))
    if sum((local/n).stat().st_size for n in FILES)>1150000000:raise ValueError('Download bound')
    if hashlib.sha256((local/'model.safetensors').read_bytes()).hexdigest()!=WEIGHTS:raise ValueError('Weight drift')
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    tokenizer=AutoTokenizer.from_pretrained(local,local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(local,local_files_only=True,trust_remote_code=False,
          use_safetensors=True,torch_dtype=torch.float32,attn_implementation='eager').eval()
    config=GenerationConfig(do_sample=False,max_new_tokens=96,use_cache=True,
        bos_token_id=model.generation_config.bos_token_id,eos_token_id=model.generation_config.eos_token_id,
        pad_token_id=tokenizer.pad_token_id)
    prepared=[]
    for cell in cells():
        text=tokenizer.apply_chat_template(cell['messages'],tokenize=False,add_generation_prompt=True)
        inputs=tokenizer(text,return_tensors='pt',add_special_tokens=False)
        if inputs['input_ids'].shape[1]>1200:raise ValueError('Input bound')
        prepared.append((cell,text,inputs))
    sizes={c['id']:i['input_ids'].shape[1] for c,_,i in prepared}
    for t in GOOD:
        if sizes[t+'/bad_prior']!=sizes[t+'/valid_prior']:raise ValueError('Prior comparison token lengths differ')
    environment={'source_head':os.environ.get('EXPECTED_HEAD'),'model':MODEL,'revision':REV,'weight_sha256':WEIGHTS,
        'packages':{p:version(p) for p in ('torch','transformers','tokenizers','huggingface-hub','safetensors','numpy')},
        'generation_config':config.to_dict(),'input_token_counts':sizes,'prior_pairs_equal_token_count':True,
        'dtype':str(next(model.parameters()).dtype),'device':str(next(model.parameters()).device),'manifest':manifest}
    emit('ENVIRONMENT',environment);rows=[]
    with patch.object(socket.socket,'connect',blocked),patch.object(socket.socket,'connect_ex',blocked):
        for cell,text,inputs in prepared:
            started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
            with torch.inference_mode():sequence=model.generate(**inputs,generation_config=config)
            ids=sequence[0,inputs['input_ids'].shape[1]:].tolist()
            raw=tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            row={**cell,'raw':raw,'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),
                 'output_ids':ids,'input_tokens':sizes[cell['id']],'output_tokens':len(ids),'at_limit':len(ids)==96,
                 'started_utc':started,'seconds':round(time.monotonic()-clock,4),'observation':o.observe(raw,cell['case'])}
            rows.append(row);emit('RECORD',row)
    result={'environment':environment,'rows':rows,'summary':summarize(rows),'paid_model_api_calls':0,
            'user_pc_used':False,'model_weights_changed':False,'semantic_retries':0}
    emit('SUMMARY',result['summary'])
    data=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode()
    emit('DATA',{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
                 'gzip_base64':base64.b64encode(gzip.compress(data,mtime=0)).decode()})
    signal.alarm(0)

if __name__=='__main__':
    if sys.argv[1:]==['--check']:print(json.dumps(check(),indent=2))
    elif sys.argv[1:]==['--run']:
        try:run()
        except Exception as error:
            emit('ABORT',{'error_type':type(error).__name__,'message':str(error)[:300],'retain_all_outputs':True});raise
    else:raise SystemExit('Use --check or --run')
