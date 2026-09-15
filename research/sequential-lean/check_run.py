"""Run the pinned Lean build and verify its declared trust boundary.

This program does not certify mathematical statements by itself. It records the
Lean compiler/kernel, leanchecker, transitive axiom list, and expected failures.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
root=Path(__file__).resolve().parent
out=Path(os.environ['ZERO_PROOF_OUTPUT']);out.mkdir(parents=True,exist_ok=True)
report={'status':'incomplete','commands':[],'source_files':{}}

def run(args,name,expected=0):
    p=subprocess.run(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=420)
    (out/(name+'.log')).write_text(p.stdout)
    report['commands'].append({'argv':args,'returncode':p.returncode,'log':name+'.log'})
    (out/'verification.json').write_text(json.dumps(report,indent=2))
    if expected==0 and p.returncode:raise RuntimeError(name+' failed')
    if expected!=0 and (p.returncode==0 or 'false' not in p.stdout.lower()):raise RuntimeError(name+' did not fail for the expected false theorem')
    return p.stdout
try:
    for p in root.rglob('*.lean'):
        if '.lake' in p.parts:continue
        text=p.read_text()
        if re.search(r'\b(sorry|admit|native_decide)\b|debug\.skipKernelTC|trustCompiler|ofReduceBool|decide\s*\+native|^\s*(axiom|unsafe)\b',text,re.M):
            raise RuntimeError('disallowed proof source construct in '+str(p))
        report['source_files'][str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    run(['lake','env','lean','--version'],'lean-version')
    build=run(['lake','build'],'build')
    axs={}
    for name,body in re.findall(r"['\"]?(ZeroAudit\.[A-Za-z0-9_]+)['\"]?\s+depends on axioms:\s*\[([^]]*)\]",build):
        vals=[x.strip() for x in body.split(',') if x.strip()]
        if set(vals)-{'propext','Classical.choice','Quot.sound'}:raise RuntimeError('unexpected axioms '+name+':'+body)
        axs[name]=vals
    for name in re.findall(r"['\"]?(ZeroAudit\.[A-Za-z0-9_]+)['\"]?\s+does not depend on any axioms",build):axs[name]=[]
    if len(axs)<11:raise RuntimeError('missing transitive axiom output; found '+str(len(axs)))
    report['axioms']=axs
    run(['lake','env','leanchecker','ZeroAudit'],'leanchecker')
    bad1='''import ZeroAudit.Concrete\nset_option maxRecDepth 1000000 in\nset_option maxHeartbeats 0 in\nexample : ∀ (p : ZeroAudit.Plan) (b : Bool), 101 * ZeroAudit.unsafeCost p b ≤ 100 * (6 * ZeroAudit.denominator) := by\n  decide +kernel\n'''
    bad2='''import ZeroAudit.Core\nexample : ZeroAudit.hitMass 20 (.leaf 20) ≤ (1 : ℝ) / 20 := by\n  norm_num [ZeroAudit.hitMass]\n'''
    for label,source in [('overscaled_score',bad1),('missing_root_contract',bad2)]:
        path=out/(label+'.lean');path.write_text(source)
        run(['lake','env','lean',str(path)],label,expected=1)
    report['status']='passed_declared_formal_scope'
except Exception as exc:
    report['status']='failed';report['error']=str(exc);raise
finally:
    report['lean_toolchain']=(root/'lean-toolchain').read_text().strip()
    if (root/'lake-manifest.json').exists():
        (out/'lake-manifest.json').write_bytes((root/'lake-manifest.json').read_bytes())
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
