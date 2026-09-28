"""Run actual Rust differential tests in a disposable source checkout."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

REFS = {'base': 'bbccb0513ff9afda385ca5c85c66eddb1318cfc7', 'candidate': 'cde465c9580a0b3f6831318539e3ff2360c7fb09'}
DATA_REV = '5f5c6524084c42a35c28c0184bea37ec2530fd7c'

def save(p, x):
    p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def main():
    lane, source, output = sys.argv[1:]
    source, out = Path(source).resolve(), Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    assert git('rev-parse', 'HEAD') == REFS[lane]
    assert not git('status', '--porcelain')
    fixtures = []
    for file in ['gpt2.json', 'fixtures/models/modernbert-base.json']:
        url = f'https://huggingface.co/datasets/hf-internal-testing/tokenizers-test-data/resolve/{DATA_REV}/{file}'
        dest = source / 'tokenizers/data' / file
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=90) as response:
            raw = response.read()
        json.loads(raw)
        dest.write_bytes(raw)
        fixtures.append({'path':file, 'url':url, 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()})
    probe = Path(__file__).with_name('reduce.rs')
    target = source/'tokenizers/tk-convert/tests/zero_unicode_probe.rs'
    assert not target.exists()
    shutil.copyfile(probe, target)
    env = dict(os.environ, ZERO_RECEIPTS=str(out), RAYON_NUM_THREADS='2', TOKENIZERS_PARALLELISM='false', CARGO_INCREMENTAL='0', CARGO_PROFILE_TEST_OPT_LEVEL='1', CARGO_PROFILE_TEST_DEBUG='0')
    cmd=['cargo','test','-p','tk-convert','--features','bench-baseline','--test','zero_unicode_probe','--','--test-threads=1','--nocapture']
    info={'lane':lane,'source_ref':REFS[lane],'tree':git('rev-parse','HEAD^{tree}'),'fixtures':fixtures,'probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),'rustc':subprocess.check_output(['rustc','-Vv'],text=True),'cargo':subprocess.check_output(['cargo','-V'],text=True),'command':cmd,'started_at':time.time(),'scope':'Exact-ids and release-ids decode comparison; generated valid-scalar blocks, not arbitrary-string coverage; no model execution'}
    save(out/'inputs.json',info)
    exit_code=None
    error=None
    try:
        with (out/'cargo.stdout').open('wb') as stdout, (out/'cargo.stderr').open('wb') as stderr:
            p=subprocess.run(cmd,cwd=source/'tokenizers',env=env,stdout=stdout,stderr=stderr,timeout=1000)
            exit_code=p.returncode
    except subprocess.TimeoutExpired:
        error='cargo timeout after 1000 seconds'
    finally:
        for name in ['cargo.stdout','cargo.stderr']:
            path=out/name
            if path.exists():
                raw=path.read_bytes()
                (out/(name+'.tail')).write_text(raw[-12000:].decode('utf-8', errors='replace'),encoding='utf-8')
                (out/(name+'.gz')).write_bytes(gzip.compress(raw,mtime=0))
                save(out/(name+'.meta.json'),{'original_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'compressed_bytes':(out/(name+'.gz')).stat().st_size,'tail_only_is_excerpt':True})
                path.unlink()
        lock=source/'tokenizers/Cargo.lock'
        if lock.exists(): shutil.copyfile(lock,out/'Cargo.lock')
        target.unlink()
    results={name:json.loads((out/f'{name}.json').read_text()) for name in ['reduction'] if (out/f'{name}.json').is_file()}
    info.update(exit_code=exit_code,error=error,finished_at=time.time(),results=results,tracked_diff=git('diff','--stat'))
    save(out/'SUMMARY.json',info)
    print('REPLAY_SUMMARY '+json.dumps(info,ensure_ascii=False),flush=True)
    assert lane == 'candidate' and exit_code == 0 and 'reduction' in results
    assert len(results['reduction']['comparisons']) == 7
    assert all(r['one_deletion_minimal'] for r in results['reduction']['comparisons'])
    assert not git('diff','--name-only')
    print('EXPECTED_MATRIX_CONFIRMED',lane)

if __name__=='__main__': main()
