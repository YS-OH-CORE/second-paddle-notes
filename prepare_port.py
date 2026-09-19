"""Reproduce a narrow current-main port into a NEW directory only.

Uses pinned public source. Does not edit an existing checkout or contact models.
The proposed edit keeps the current reasoning branch, then wraps its final reply
with the original contribution's success type. Existing code and test notices
remain intact. All unexpected conflicts stop preparation.
"""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO='NousResearch/hermes-agent'
MAIN='3eb9712180ec60191edfb9d072ddb28ffe427e4b'
BASE='79445a496c86a19332ad786494b8384d2167e2d0'
HEAD='501be10cce7159a08279c89c724db602d9770601'
FILES=['gateway/run.py','gateway/run_inbound.py','gateway/slash_commands_model.py',
       'tests/gateway/test_model_confirmation_binding.py','tests/gateway/test_model_multiline_payload.py']
EXPECTED_MAIN={
 'gateway/run.py':'06fcfaf66d464e81a18d32ef114a8a5bf6ae01a622db5e8f45158d91827731c0',
 'gateway/run_inbound.py':'7a43c02ed1ee43e1df8922de1ff30c25b93b8a7db6c09bc43a177648b9fd820a',
 'gateway/slash_commands_model.py':'be08487cbfe324b37b9e169cfee9919c5457682ba70d54b48a56e4555d1254e2'}


def digest(data): return hashlib.sha256(data).hexdigest()


def get(ref,path):
    url='https://raw.githubusercontent.com/'+REPO+'/'+ref+'/'+path
    try:
        with urllib.request.urlopen(url,timeout=35) as r: return r.read()
    except urllib.error.HTTPError as e:
        if e.code==404: return None
        raise


def prepare(target):
    target=Path(target)
    target.mkdir(parents=True,exist_ok=False)
    patch=[]; identities=[]
    for path in FILES:
        versions={tag:get(ref,path) for tag,ref in [('main',MAIN),('base',BASE),('head',HEAD)]}
        if versions['head'] is None: raise ValueError('Missing head file: '+path)
        if path in EXPECTED_MAIN and digest(versions['main'])!=EXPECTED_MAIN[path]:
            raise ValueError('Pinned main identity mismatch: '+path)
        for tag,data in versions.items():
            if data is not None:
                p=target/'sources'/tag/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
        if versions['base'] is None:
            if versions['main'] not in (None,versions['head']): raise ValueError('Unexpected add/add conflict')
            candidate=versions['head']
        else:
            if versions['main'] is None: raise ValueError('Unexpected deleted current file')
            p=[target/'sources'/tag/path for tag in ['main','base','head']]
            run=subprocess.run(['git','merge-file','-p','--diff3','-L','current-main','-L','merge-base','-L','contributed-head',*map(str,p)],capture_output=True,timeout=20)
            text=run.stdout.decode('utf-8')
            if run.returncode:
                pattern=r'^<<<<<<< current-main\n(.*?)^\|\|\|\|\|\|\| merge-base\n(.*?)^=======\n(.*?)^>>>>>>> contributed-head\n'
                found=list(re.finditer(pattern,text,re.M|re.S))
                if path!='gateway/slash_commands_model.py' or run.returncode!=1 or len(found)!=1:
                    raise ValueError('Unexpected conflict scope: '+path)
                match=found[0]; ours,old,theirs=match.groups()
                if 'if ctx.reasoning_effort and not one_turn:' not in ours or ours.count('        return reply\n')!=1:
                    raise ValueError('Current reasoning branch does not match inspected source')
                if old.strip()!='return await self._model_switch_confirmation(result, ctx, one_turn=one_turn, picker=picker)':
                    raise ValueError('Unexpected ancestor')
                expected='        return ModelSwitchConfirmation(\n            await self._model_switch_confirmation(result, ctx, one_turn=one_turn, picker=picker)\n        )\n'
                if theirs!=expected: raise ValueError('Unexpected contribution branch')
                resolution=ours.replace('        return reply\n','        return ModelSwitchConfirmation(reply)\n')
                text=text[:match.start()]+resolution+text[match.end():]
            ast.parse(text,filename=path)
            candidate=text.encode('utf-8')
        dest=target/'candidate'/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(candidate)
        old=(versions['main'] or b'').decode('utf-8')
        lines=difflib.unified_diff(old.splitlines(keepends=True),candidate.decode().splitlines(keepends=True),fromfile=('a/'+path if versions['main'] is not None else '/dev/null'),tofile='b/'+path)
        patch.append(''.join(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n' for line in lines))
        identities.append({'path':path,'main':digest(versions['main']) if versions['main'] is not None else None,'base':digest(versions['base']) if versions['base'] is not None else None,'head':digest(versions['head']),'candidate':digest(candidate)})
    license_data=get(MAIN,'LICENSE')
    if license_data is None: raise ValueError('Missing upstream license')
    (target/'UPSTREAM_LICENSE').write_bytes(license_data)
    patch_bytes=''.join(patch).encode('utf-8')
    (target/'current-main-port.patch').write_bytes(patch_bytes)
    manifest={'repository':REPO,'main':MAIN,'head':HEAD,'base':BASE,'patch_sha256':digest(patch_bytes),'files':identities,'scope':'Source integration candidate; runtime validation recorded separately'}
    (target/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: python prepare_port.py NEW_OUTPUT_DIRECTORY')
    print(json.dumps(prepare(sys.argv[1]),indent=2))
