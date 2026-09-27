"""Pinned vLLM helper plus installed real Mistral request validators, CPU only."""
from pathlib import Path
from copy import deepcopy
from typing import Any,cast
import ast,hashlib,json
from mistral_common.protocol.instruct.converters import convert_openai_messages
from mistral_common.protocol.instruct.validator import MistralRequestValidatorV13,MistralRequestValidatorV15,ValidationMode
ROOT=Path(__file__).resolve().parent
source=(ROOT/'mistral.py').read_text(encoding='utf-8')
assert hashlib.sha256((ROOT/'mistral.py').read_bytes()).hexdigest()=='74fa5093b91ed69d79ff402f0f86633be8017f110455f0843513404d6799b6d0'
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_adapt_tool_images_for_mistral')
ns={'Any':Any,'cast':cast,'ChatCompletionMessageParam':dict}
exec(compile(ast.Module(body=[node],type_ignores=[]),'pinned_mistral_helper','exec'),ns)
adapt=ns['_adapt_tool_images_for_mistral']
IMAGE={'type':'image_url','image_url':{'url':'https://example.invalid/test.png'}}
def call(identifier):return {'id':identifier,'type':'function','function':{'name':'inspect','arguments':'{}'}}
def tool(identifier,content):return {'role':'tool','tool_call_id':identifier,'content':content}
def conversation(content,tail=None):
    messages=[{'role':'user','content':'Use both tools.'},{'role':'assistant','content':None,'tool_calls':[call('abc123XYZ'),call('def456UVW')]},tool('abc123XYZ',content),tool('def456UVW','Second result')]
    return messages+([] if tail is None else tail)
def check(messages,version):
    validator=(MistralRequestValidatorV13 if version==13 else MistralRequestValidatorV15)(mode=ValidationMode.serving)
    try:
        validator.validate_messages(convert_openai_messages(messages),continue_final_message=False)
        return {'accepted':True}
    except Exception as exc:return {'accepted':False,'error':type(exc).__name__,'message':str(exc)}
