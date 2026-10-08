"""Function-chain reproduction of Hermes #133922 service attribution, not memory leakage.
Exact registration callback extracted by AST; real registration, home resolver and
inventory code. OS/job/ledger boundaries mocked. No web server or model starts.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import ast,hashlib,importlib.util,io,json,os,tempfile,types,difflib
from contextlib import redirect_stdout
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
UP=HERE/'upstream'
REF='a50406d9b7474b060450d2dcaff8743c977d296a'
EXPECTED={
'hermes_cli/web_server.py':'3557c4213f416eae814e893143e540fc4a82b7b0f0848bdc9f7fb1c412061a3b',
'hermes_cli/process_identity.py':'c833451067d5dca9cf93cb70c5e4b13d4035c8ecf787654b23c6b8db94b27093',
'hermes_cli/update_inventory.py':'66af456cf5cd07050032dcce9993d8550b7e6bb0718db17bd644df0fa528775d',
'hermes_constants.py':'5d43e6102c69748a2e64fc91623a49e1b0d76623416ce4ec37f23f216c3ce91f'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def callback(text):
 ns=[n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name=='_register_identity']
 assert len(ns)==1
 return compile(ast.fix_missing_locations(ast.Module(body=ns,type_ignores=[])),'web_server.py:_register_identity','exec')
for p,h in EXPECTED.items():assert sha(UP/p)==h,p
original=(UP/'hermes_cli/web_server.py').read_text(encoding='utf-8')
old='''    def _register_identity() -> None:
        from hermes_cli.process_identity import attach_self_to_kill_on_close_job, register_self

        register_self(
            "serve" if headless else "dashboard",
            detail={"host": host, "port": actual_port, "profile": initial_profile or "", "isolated": isolated},
        )
        attach_self_to_kill_on_close_job()
'''
new='''    def _register_identity() -> None:
        from hermes_constants import hermes_home_key, profile_name_for_home
        from hermes_cli.process_identity import attach_self_to_kill_on_close_job, register_self

        # initial_profile selects the UI; it need not own this backend. Match
        # the same resolved home that register_self records in the ledger.
        owner_profile = profile_name_for_home(hermes_home_key()) or ""
        register_self(
            "serve" if headless else "dashboard",
            detail={"host": host, "port": actual_port, "profile": owner_profile, "isolated": isolated},
        )
        attach_self_to_kill_on_close_job()
'''
assert original.count(old)==1
candidate=original.replace(old,new,1);assert candidate.replace(new,old,1)==original
ast.parse(candidate)
cp=HERE/'candidate/hermes_cli/web_server.py';cp.parent.mkdir(parents=True,exist_ok=True)
if cp.exists():assert cp.read_bytes()==candidate.encode()
else:cp.write_bytes(candidate.encode())
(HERE/'owner-profile.patch').write_bytes(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/hermes_cli/web_server.py',tofile='b/hermes_cli/web_server.py')).encode())
assert 'hermes_constants' not in sys.modules
utils=types.ModuleType('utils')
def no_write(*a,**k):raise AssertionError('Unexpected real ledger write')
utils.atomic_json_write=no_write
package=types.ModuleType('hermes_cli');package.__path__=[]
rows=[]
with tempfile.TemporaryDirectory(prefix='zero-hermes-ledger-fixture-') as folder:
 root=Path(folder)/'hermes-test-root';root.mkdir();(root/'config.yaml').write_text('{}\n')
 for name in ('profile-a','profile-b'):(root/'profiles'/name).mkdir(parents=True)
 env={'HERMES_HOME':str(root),'HERMES_SPAWN':'','HERMES_DATA_DIR_SUFFIX':'','LOCALAPPDATA':str(Path(folder)/'appdata'),'HOME':folder,'USERPROFILE':folder}
 with patch.dict(os.environ,env),patch.dict(sys.modules,{'utils':utils,'hermes_cli':package}):
  hc=load('hermes_constants',UP/'hermes_constants.py')
  pi=load('hermes_cli.process_identity',UP/'hermes_cli/process_identity.py')
  inv=load('hermes_cli.update_inventory',UP/'hermes_cli/update_inventory.py')
  package.process_identity=pi;package.update_inventory=inv
  cases=[('profile-a','','profile-a'),('profile-a','profile-b','profile-a'),('profile-a','profile-a','profile-a'),('default','profile-a','default'),('default','','default'),('profile-b','profile-b','profile-b')]
  for headless in (False,True):
   for owner,ui,expected in cases:
    home=root if owner=='default' else root/'profiles'/owner
    with patch.dict(os.environ,{'HERMES_HOME':str(home)}):
     hc.reset_hermes_home_key_cache()
     row={'kind':'serve' if headless else 'dashboard','owner':owner,'ui_profile':ui,'expected':expected}
     for label,text in (('before',original),('candidate',candidate)):
      ledger=[];jobs=[]
      def capture(entry):ledger.append(asdict(entry));return True
      with patch.object(pi,'_process_create_time',return_value=12345.0),patch.object(pi,'_desktop_spawner_identity',return_value=(42,123.0)),patch.object(pi,'_append_entry',side_effect=capture),patch.object(pi,'attach_self_to_kill_on_close_job',side_effect=lambda:jobs.append(1)),patch.object(pi,'ledger_entries',side_effect=lambda:list(ledger)),patch.object(pi,'spawner_is_dead',return_value=False),patch.object(inv,'_loaded_backend_launchd_jobs',return_value=[]),patch.object(inv,'_is_desktop_ssh_ledger_entry',return_value=False):
       ns={'headless':headless,'host':'127.0.0.1','actual_port':12345,'initial_profile':ui,'isolated':True}
       exec(callback(text),ns);ns['_register_identity']()
       assert len(ledger)==1 and jobs==[1]
       e=ledger[0];assert e['hermes_home']==hc.hermes_home_key(home)
       assert e['host']=='127.0.0.1' and e['port']==12345 and e['isolated'] is True and e['purpose']==row['kind']
       plan=inv.UpdatePlan();inv._collect_ledger_runtimes(plan,set());assert len(plan.runtimes)==1
       rt=plan.runtimes[0];assert rt.supervisor=='desktop' and rt.restart_via=='desktop'
       output=io.StringIO()
       with redirect_stdout(output):inv.print_update_plan(plan)
       assert f'[{rt.profile}]' in output.getvalue()
       row[label]={'ledger_profile':e['profile'],'plan_profile':rt.profile,'matched':rt.profile==expected,'other_registration_fields_unchanged':True}
     rows.append(row)
assert not Path(folder).exists()
assert len(rows)==12 and sum(r['before']['matched'] for r in rows)==6
assert all(r['candidate']['matched'] for r in rows)
for p,h in EXPECTED.items():assert sha(UP/p)==h,p
result={'schema':'zero-profile-ledger-reproduction/1','commit':REF,'issue':133922,
'scope':'Service-attribution function chain only; not original MEMORY/USER mixing cause or full-app end-to-end test.',
'cases':rows,'before_correct':6,'candidate_correct':12,'total':12,
'full_modules_used':['hermes_constants.py','hermes_cli/process_identity.py','hermes_cli/update_inventory.py'],
'ast_extracted_callback':'hermes_cli/web_server.py:_register_identity',
'mocked_boundaries':['ledger I/O','process birth/spawner identity','OS job attachment','supervisor discovery'],
'real_model_calls':0,'server_started':False,'private_memory_read':False,'installed_hermes_changed':False,
'fixture_removed':True,'candidate_sha256':sha(cp),'source_sha256':EXPECTED,'completed_at':datetime.now(timezone.utc).isoformat()}
(HERE/'RESULT.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(result,ensure_ascii=False,indent=2))
