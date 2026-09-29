"""Pinned UCD assignment audit, official NFC checks, and real tokenizer comparison.

Zero × Youngseok Oh. All runtime changes are disposable test files, not fixes.
"""
import gzip, hashlib, json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path
HEAD='cde465c9580a0b3f6831318539e3ff2360c7fb09'
DATA_REV='5f5c6524084c42a35c28c0184bea37ec2530fd7c'
PINS={
 '9.0.0-UnicodeData.txt':'68dfc414d28257b9b5d6ddbb8b466c768c00ebdf6cbf7784364a9b6cad55ee8f',
 '17.0.0-UnicodeData.txt':'2e1efc1dcb59c575eedf5ccae60f95229f706ee6d031835247d843c11d96470c',
 '17.0.0-DerivedAge.txt':'f8ecdf768bdc210f201abd271d9bc587825618a86a7046a8146cc816393f1998',
 '9.0.0-NormalizationTest.txt':'2d48d848656b3cf889df59980ab13551988950c4ca8c5190a17c691a17f8b9bb',
 '17.0.0-NormalizationTest.txt':'5019ffd530751a741900c849c0e010332f142a3612234639bd200b82138a87db',
}
PAIRS=[(0xEB9,0xEBA),(0x1DF8,0x1DF9),(0x10F84,0x10F85),(0x11839,0x1183A),(0x1611E,0x1611F),(0x16D67,0x16D68),(0x1E5EE,0x1E5EF)]
def save(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def read_ucd(path):
    table={};pending=None
    for line in path.read_text(encoding='utf-8').splitlines():
        row=line.split(';');cp=int(row[0],16)
        if row[1].endswith(', First>'):pending=(cp,row);continue
        if row[1].endswith(', Last>'):
            start,fields=pending;pending=None
            table.update((n,fields) for n in range(start,cp+1))
        else:table[cp]=row
    assert pending is None
    return table

def main():
    source,out=map(lambda s:Path(s).resolve(),sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
    here=Path(__file__).resolve().parent
    def git(*a):return subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
    assert git('rev-parse','HEAD')==HEAD and not git('status','--porcelain')
    provenance=[]
    for name,digest in PINS.items():
        version,file=name.split('-',1);url=f'https://www.unicode.org/Public/{version}/ucd/{file}'
        with urllib.request.urlopen(url,timeout=90) as r:raw=r.read()
        assert hashlib.sha256(raw).hexdigest()==digest,(name,'source bytes changed')
        (out/name).write_bytes(raw);provenance.append({'name':name,'url':url,'bytes':len(raw),'sha256':digest})
    u9,u17=read_ucd(out/'9.0.0-UnicodeData.txt'),read_ucd(out/'17.0.0-UnicodeData.txt')
    assert u9.keys()<=u17.keys()
    ages={}
    for line in (out/'17.0.0-DerivedAge.txt').read_text().splitlines():
        line=line.split('#')[0].strip()
        if not line:continue
        span,age=map(str.strip,line.split(';')[:2]);b=[int(x,16) for x in span.split('..')]
        ages.update((n,age) for n in range(b[0],b[-1]+1))
    assigned=''.join(chr(n) for n in sorted(u9) if not 0xD800<=n<=0xDFFF)
    assert len(assigned)==265705
    (out/'assigned9.txt').write_text(assigned,encoding='utf-8')
    classification=[]
    for pair in PAIRS:
        chars=[{'codepoint':f'U+{n:04X}','name':u17[n][1],'first_unicode_version':ages[n],'assigned9':n in u9,'ccc9':int(u9[n][3]) if n in u9 else 0,'ccc17':int(u17[n][3]),'decomposition17':u17[n][5]} for n in pair]
        assert any(not c['assigned9'] for c in chars)
        classification.append(chars)
    save(out/'assignment-audit.json',{'pairs':classification,'all_seven_include_post9_assignment':True,'assigned9_scalar_count':len(assigned),'definition':'UnicodeData9 entries expanded including private-use and controls, excluding surrogates; not all valid codepoints','sources':provenance})
    for file,digest in [('gpt2.json','8414cab924d8b9b33013f0d221c5862f365ee9be39c5c2bfae8a5a9e970478a6'),('fixtures/models/modernbert-base.json','9fd55248d51d33976b324fc11592e28071da7d41e0e9401dfb7082e30574b7b1')]:
        url=f'https://huggingface.co/datasets/hf-internal-testing/tokenizers-test-data/resolve/{DATA_REV}/{file}'
        with urllib.request.urlopen(url,timeout=90) as r:raw=r.read()
        assert hashlib.sha256(raw).hexdigest()==digest
        dest=source/'tokenizers/data'/file;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        provenance.append({'name':file,'url':url,'bytes':len(raw),'sha256':digest})
    env=dict(os.environ,ZERO_INPUTS=str(out),RAYON_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',CARGO_INCREMENTAL='0',CARGO_PROFILE_TEST_OPT_LEVEL='1',CARGO_PROFILE_TEST_DEBUG='0')
    commands=[]
    def run(label,cmd,cwd):
        with (out/(label+'.stdout')).open('wb') as o,(out/(label+'.stderr')).open('wb') as e:
            p=subprocess.run(cmd,cwd=cwd,env=env,stdout=o,stderr=e,timeout=1000)
        commands.append({'label':label,'command':cmd,'exit_code':p.returncode})
        return p.returncode
    gates={}
    test_path=source/'tokenizers/tk-convert/tests/zero_assigned9_probe.rs'
    assert not test_path.exists()
    try:
        gates['nfc']=run('normalization',['cargo','+1.93.1','run','--quiet'],here/'normalizer-control')
        if (out/'normalization.stdout').stat().st_size:
            nfc=json.loads((out/'normalization.stdout').read_text());save(out/'normalization-result.json',nfc)
        shutil.copyfile(here/'probe.rs',test_path)
        gates['tokenizer']=run('tokenizer',['cargo','+1.93.1','test','-p','tk-convert','--features','bench-baseline','--test','zero_assigned9_probe','--','--test-threads=1','--nocapture'],source/'tokenizers')
    finally:
        if test_path.exists():test_path.unlink()
        for label in ['normalization','tokenizer']:
            for stream in ['stdout','stderr']:
                p=out/(label+'.'+stream)
                if not p.exists():continue
                raw=p.read_bytes();(out/(p.name+'.gz')).write_bytes(gzip.compress(raw,mtime=0))
                (out/(p.name+'.tail')).write_text(raw[-12000:].decode('utf-8',errors='replace'),encoding='utf-8')
                save(out/(p.name+'.meta.json'),{'original_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'tail_is_excerpt':True})
                p.unlink()
        for src,dst in [(source/'tokenizers/Cargo.lock','tokenizer-Cargo.lock'),(here/'normalizer-control/Cargo.lock','normalizer-Cargo.lock')]:
            if src.exists():shutil.copyfile(src,out/dst)
    clean=not git('diff','--name-only')
    summary={'source_ref':HEAD,'source_tree':git('rev-parse','HEAD^{tree}'),'rustc':subprocess.check_output(['rustc','+1.93.1','-Vv'],text=True),'sources':provenance,'gates':gates,'commands':commands,'production_files_restored':clean,'results':{n:json.loads((out/(n+'.json')).read_text()) for n in ['modernbert','gpt2','normalization-result'] if (out/(n+'.json')).exists()}}
    save(out/'SUMMARY.json',summary)
    print(json.dumps(summary,indent=2),flush=True)
    assert clean and gates=={'nfc':0,'tokenizer':0}
    assert set(summary['results'])=={'modernbert','gpt2','normalization-result'}
if __name__=='__main__':main()
