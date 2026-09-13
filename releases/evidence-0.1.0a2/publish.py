"""Publish the already-executed visibility correction without replacing old assets."""
from __future__ import annotations
import argparse, base64, csv, hashlib, io, json, os, subprocess, zipfile
from pathlib import Path
from urllib.request import urlopen

REPO='YS-OH-CORE/second-paddle-notes'
TAG='evidence-v0.1.0a2'
TARGET='fabb5375056dc51500183d3ec510aeb4ac94defb'
WHEEL='second_paddle_evidence-0.1.0a2-py3-none-any.whl'
WHEEL_SHA='b801b9f2f8fe6973c980161d0ee2ff0241eada55b313c1b635a90d13eb6425ff'
OLD_WHEEL_SHA='0e509a17ee164189abea151996cb084de6fc55990ee0ce4d8a9a70bed5b984bd'
ORIGINALS={
 'visibility':(10314727546,26193,'d76bb8798a3f74bf330c0e44692a040586c47527f337f52b9afd6f795002e19d','evidence_visibility_34748252871.zip'),
 'linux':(10314971439,21368,'63f954a99ba412511e02b6d29edd09ff570be102f9d29f73c999cee2ab5a2467','evidence_a2_linux_34748252840.zip'),
 'windows':(10315026242,21475,'7c5bc31c44b9b24e578b968f384692acfd32ab24b9da7c09855607e9092953cc','evidence_a2_windows_34748252840.zip')}
NAMES=[WHEEL,'ORIGINAL-visibility.zip','ORIGINAL-linux.zip','ORIGINAL-windows.zip','PROVENANCE.json','SHA256SUMS']

def require(ok,message):
 if not ok:raise RuntimeError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def gh(*args):return subprocess.check_output(['gh',*args],timeout=90)
def patch_release(number,body):
 p=subprocess.run(['gh','api','--method','PATCH',f'repos/{REPO}/releases/{number}','--input','-'],
   input=json.dumps(body).encode(),capture_output=True,timeout=40,check=True)
 return json.loads(p.stdout)
def releases():
 return [r for page in json.loads(gh('api','--paginate','--slurp',f'repos/{REPO}/releases?per_page=100')) for r in page]
def inspect_wheel(b):
 require(len(b)==35543 and sha(b)==WHEEL_SHA,'Unexpected wheel')
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  require(z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==16,'Invalid wheel structure')
  record=next(n for n in z.namelist() if n.endswith('.dist-info/RECORD'))
  rows=list(csv.reader(io.StringIO(z.read(record).decode())))
  require({r[0] for r in rows}==set(z.namelist()),'Incomplete RECORD')
  for n,h,s in rows:
   if n==record:require(h==s=='','Invalid RECORD self entry');continue
   b=z.read(n);digest=base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b'=').decode()
   require(h=='sha256='+digest and int(s)==len(b),'Incorrect RECORD entry')
  manifest=json.loads(z.read('second_paddle_evidence/bundle.json'))
  require(manifest['source_commit']=='e40eba4b7b985c716644ec736ac72288f8e6cdd7','Incorrect bundle source')
  require(len(manifest['sha256'])==8,'Incorrect bundle count')
  for n,h in manifest['sha256'].items():require(sha(z.read('second_paddle_evidence/_bundle/'+n))==h,'Bundle mismatch')
def original(data,kind):
 artifact,size,digest,_=ORIGINALS[kind]
 require(len(data)==size and sha(data)==digest,f'Artifact {artifact} mismatch')
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  require(z.testzip() is None,'Artifact CRC mismatch')
  if kind=='visibility':
   r=json.loads(z.read('visibility-results/visibility.json'))
   require(r['status']=='verified' and len(r['cases'])==24 and len(r['old_marker_cases'])==6 and r['new_marker_cases']==[],'Comparison incomplete')
   require('Ran 21 tests' in z.read('visibility-unit.log').decode(),'Unit result missing')
   wheel=z.read('visibility-dist/'+WHEEL)
  else:
   r=json.loads(z.read('wheel-evidence/summary.json'));calls=json.loads(z.read('wheel-evidence/calls.json'))
   require(r['status']=='verified-installed-wheel' and r['calls']==calls and calls['status']=='passed' and len(calls['cases'])==5,'Installation incomplete')
   wheel=z.read('wheel-dist/'+WHEEL)
 inspect_wheel(wheel)
 return wheel

def prepare(out,original_dir=None):
 out.mkdir(parents=True,exist_ok=False);wheels=[]
 for kind,(aid,_,_,filename) in ORIGINALS.items():
  data=(original_dir/filename).read_bytes() if original_dir else gh('api',f'repos/{REPO}/actions/artifacts/{aid}/zip')
  wheels.append(original(data,kind));(out/f'ORIGINAL-{kind}.zip').write_bytes(data)
 require(all(w==wheels[0] for w in wheels),'Platform wheels differ')
 (out/WHEEL).write_bytes(wheels[0])
 provenance={'version':'0.1.0a2','tag':TAG,'source_commit':TARGET,'wheel':{'bytes':35543,'sha256':WHEEL_SHA},
  'comparison_run':34748252871,'install_run':34748252840,
  'originals':{k:{'id':a,'bytes':s,'sha256':h} for k,(a,s,h,_) in ORIGINALS.items()},
  'scope':'Exact previously executed wheel and original returned evidence. No rebuild, model call or private-input experiment.'}
 (out/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
 (out/'SHA256SUMS').write_text(''.join(f'{sha((out/n).read_bytes())}  {n}\n' for n in NAMES[:-1]),encoding='utf-8')
 validate(out)
def validate(out):
 require({p.name for p in out.iterdir()}==set(NAMES),'Unexpected asset set')
 wheel=(out/WHEEL).read_bytes();inspect_wheel(wheel)
 for kind in ORIGINALS:require(original((out/f'ORIGINAL-{kind}.zip').read_bytes(),kind)==wheel,'Evidence differs')
 p=json.loads((out/'PROVENANCE.json').read_text());require(p['source_commit']==TARGET and p['wheel']['sha256']==WHEEL_SHA,'Incorrect provenance')
 expected=''.join(f'{sha((out/n).read_bytes())}  {n}\n' for n in NAMES[:-1])
 require((out/'SHA256SUMS').read_text()==expected,'Checksum list mismatch')
 return {n:sha((out/n).read_bytes()) for n in NAMES}
def identity(r,out,hashes):
 require(r['tag_name']==TAG and r['target_commitish']==TARGET and r['prerelease'],'Wrong release identity')
 require({a['name']:a.get('digest') for a in r['assets']}=={n:'sha256:'+h for n,h in hashes.items()},'Asset digest mismatch')
 require(all(a['state']=='uploaded' and a['size']==(out/a['name']).stat().st_size for a in r['assets']),'Asset incomplete')

def publish(out,notes,report_path):
 require(os.environ.get('GITHUB_REPOSITORY')==REPO and os.environ.get('GITHUB_REF')=='refs/heads/main','Wrong publication context')
 report={'status':'incomplete','tag':TAG,'public_downloads':[]}
 try:
  hashes=validate(out)
  found=[r for r in releases() if r['tag_name']==TAG]
  require(len(found)<=1,'Ambiguous release')
  if found:
   r=found[0];require(not r['draft'],'Existing draft needs explicit reconciliation; no asset replacement')
  else:
   gh('release','create',TAG,'--repo',REPO,'--target',TARGET,'--draft','--prerelease','--latest=false',
      '--title','Evidence Tools 0.1.0a2: model-view boundary correction','--notes-file',str(notes))
   gh('release','upload',TAG,*[str(out/n) for n in NAMES],'--repo',REPO)
   found=[r for r in releases() if r['tag_name']==TAG];require(len(found)==1,'New draft not unique')
   r=found[0]
  r=json.loads(gh('api',f'repos/{REPO}/releases/{r["id"]}'));identity(r,out,hashes)
  if r['draft']:r=patch_release(r['id'],{'draft':False,'prerelease':True,'make_latest':'false'})
  identity(r,out,hashes);require(not r['draft'],'Release remains a draft')
  report.update(release_id=r['id'],url=r['html_url'],release_published=True)
  # Default urllib requests contain no GH token, credentials or browser cookies.
  for a in r['assets']:
   expected=f'https://github.com/{REPO}/releases/download/{TAG}/{a["name"]}'
   require(a['browser_download_url']==expected,'Unexpected public asset URL')
   with urlopen(expected,timeout=30) as response:
    data=response.read(2_000_000);require(response.status==200,'Public download failed')
   require(data==(out/a['name']).read_bytes(),'Public bytes differ')
   report['public_downloads'].append({'name':a['name'],'status':200,'bytes':len(data),'sha256':sha(data)})
  old=json.loads(gh('api',f'repos/{REPO}/releases/387682815'))
  require(old['tag_name']=='evidence-v0.1.0a1' and not old['draft'],'Old release identity changed')
  old_asset={a['name']:(a['id'],a['size'],a.get('digest')) for a in old['assets']}
  require(old_asset['second_paddle_evidence-0.1.0a1-py3-none-any.whl'][2]=='sha256:'+OLD_WHEEL_SHA,'Old wheel changed')
  prefix=f'> **Superseded for model-facing projection:** use [0.1.0a2](https://github.com/{REPO}/releases/tag/{TAG}). Version 0.1.0a1 may copy protocol metadata into ordinary output. Select model-visible inputs before calling either version; output filtering cannot undo input disclosure. Original assets below remain unchanged.\n\n'
  body=old.get('body') or ''
  if not body.startswith(prefix):
   new=patch_release(old['id'],{'body':prefix+body})
   require(new['body']==prefix+body,'Warning readback mismatch')
  else:new=old
  require({a['name']:(a['id'],a['size'],a.get('digest')) for a in new['assets']}==old_asset,'Old assets changed')
  report.update(status='published_and_publicly_verified',old_release_warning=True,old_assets_unchanged=True)
 except BaseException as exc:
  report['error']=type(exc).__name__+': '+str(exc);raise
 finally:
  report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','publish']);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--originals',type=Path);p.add_argument('--notes',type=Path);p.add_argument('--report',type=Path)
 a=p.parse_args()
 if a.mode=='prepare':prepare(a.out,a.originals)
 else:
  if a.notes is None or a.report is None:p.error('publish requires --notes and --report')
  publish(a.out,a.notes,a.report)
