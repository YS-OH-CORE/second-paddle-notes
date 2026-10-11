"""One bounded exploratory generation/feedback run. No executable model outputs.
Only fictional channel assignments. No user PC, private data, keys, or paid APIs.
Every first output and both revisions are retained, including invalid proposals.
"""
from pathlib import Path
from datetime import datetime,timezone
from importlib.metadata import version
import hashlib,json,os,platform,signal,socket,sys,time
from unittest.mock import patch
import task

ROOT=Path(__file__).resolve().parent
MODEL='Qwen/Qwen2.5-0.5B-Instruct'
REVISION='7ae557604adf67be50417f59c2c2f167def9a775'
MAX_NEW=96
NAMES=('config.json','generation_config.json','tokenizer.json','tokenizer_config.json',
       'vocab.json','merges.txt','model.safetensors')

def emit(kind,value):
    print('ZERO_'+kind+' '+json.dumps(value,ensure_ascii=False,separators=(',',':')),flush=True)

def timeout_handler(*_):raise TimeoutError('Registered 540-second run ceiling reached')
def blocked(*_args,**_kwargs):raise RuntimeError('Network disabled during model evaluation')
def utc():return datetime.now(timezone.utc).isoformat()

def main():
    signal.signal(signal.SIGALRM,timeout_handler);signal.alarm(540)
    os.environ.update(HF_HUB_DISABLE_TELEMETRY='1',HF_HUB_DISABLE_XET='1',DO_NOT_TRACK='1',
                      TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    for key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','OPENAI_API_KEY'):os.environ.pop(key,None)
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM,AutoTokenizer,GenerationConfig
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for filename,wanted in manifest['files'].items():
        if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()!=wanted:raise ValueError('Source manifest differs')
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(2709)
    emit('START',{'utc':utc(),'model':MODEL,'revision':REVISION,'max_generations':12,
        'max_new_tokens_per_generation':MAX_NEW,'workflow_head':os.environ.get('EXPECTED_HEAD'),
        'source_manifest':manifest,'python':platform.python_version(),
        'packages':{p:version(p) for p in ('torch','transformers','tokenizers','huggingface-hub','safetensors','numpy')}})
    model_dir=Path(snapshot_download(MODEL,revision=REVISION,allow_patterns=list(NAMES),
                                    token=False,max_workers=2,local_dir=Path(os.environ['RUNNER_TEMP'])/'pilot-model'))
    total=sum((model_dir/n).stat().st_size for n in NAMES)
    if total>1_150_000_000:raise ValueError('Model download exceeds registered size bound')
    model_hashes={n:hashlib.sha256((model_dir/n).read_bytes()).hexdigest() for n in NAMES}
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    tokenizer=AutoTokenizer.from_pretrained(model_dir,local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(model_dir,local_files_only=True,
        trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float32,attn_implementation='eager').eval()
    generation=GenerationConfig(do_sample=False,max_new_tokens=MAX_NEW,use_cache=True,
        bos_token_id=model.generation_config.bos_token_id,eos_token_id=model.generation_config.eos_token_id,
        pad_token_id=tokenizer.pad_token_id)
    emit('ENVIRONMENT',{'model_file_sha256':model_hashes,'bytes':total,
        'generation_config':generation.to_dict(),'dtype':str(next(model.parameters()).dtype),
        'device':str(next(model.parameters()).device),'threads':torch.get_num_threads(),
        'candidate_space_per_task':729,'feasible_assignments':{t['id']:len(task.solutions(t)) for t in task.TASKS}})
    records=[]
    def generate(messages,case,stage):
        if len(records)>=12:raise RuntimeError('Generation ceiling')
        text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        inputs=tokenizer(text,return_tensors='pt',add_special_tokens=False)
        if inputs['input_ids'].shape[1]>1200:raise ValueError('Input token ceiling')
        started=utc();clock=time.monotonic()
        with torch.inference_mode():seq=model.generate(**inputs,generation_config=generation)
        ids=seq[0,inputs['input_ids'].shape[1]:].tolist()
        raw=tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        evaluation=task.evaluate(raw,case)
        row={'case':case['id'],'stage':stage,'started_utc':started,'finished_utc':utc(),
             'seconds':round(time.monotonic()-clock,4),'messages':messages,'rendered_prompt':text,
             'input_token_ids':inputs['input_ids'][0].tolist(),'output_token_ids':ids,
             'raw_response':raw,'evaluation':evaluation,'output_token_count':len(ids),
             'token_ceiling_reached':len(ids)==MAX_NEW}
        records.append(row);emit('RECORD',row)
        return row
    with patch.object(socket.socket,'connect',blocked),patch.object(socket.socket,'connect_ex',blocked):
        for index,t in enumerate(task.TASKS):
            messages=[{'role':'system','content':task.SYSTEM},{'role':'user','content':task.prompt(t)}]
            first=generate(messages,t,'initial')
            for condition in (('neutral','feedback') if index%2==0 else ('feedback','neutral')):
                cue=task.NEUTRAL if condition=='neutral' else task.feedback(first['evaluation'])
                branch=messages+[{'role':'assistant','content':first['raw_response']},{'role':'user','content':cue}]
                result=generate(branch,t,condition)
                emit('TRANSITION',{'case':t['id'],'stage':condition,
                    **task.compare(first['evaluation'],result['evaluation'],t)})
    if len(records)!=12 or len({(r['case'],r['stage']) for r in records})!=12:raise ValueError('Incomplete inventory')
    summary={'status':'completed_exploratory_model_run','utc':utc(),'model':MODEL,'revision':REVISION,
             'generations':len(records),'tasks':4,'independent_task_families':1,'semantic_retries':0,
             'counts':{s:{'format_valid':sum(r['evaluation']['format_valid'] for r in records if r['stage']==s),
                         'feasible':sum(r['evaluation']['feasible'] for r in records if r['stage']==s),
                         'denominator':4} for s in ('initial','neutral','feedback')},
             'not_measured':['creativity in general','neural mechanism','AGI','persistent self-improvement',
                            'new scientific discovery','statistical generalization','equal feedback input tokens'],
             'weights_updated':False,'paid_api_calls':0,'personal_computer_used':False}
    emit('SUMMARY',summary);signal.alarm(0)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        emit('ABORT',{'utc':utc(),'status':'aborted_keep_all_prior_records','error_type':type(error).__name__,
                      'message':str(error)[:400]})
        raise
