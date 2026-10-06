#!/usr/bin/env python3
"""Actual Mem0 EvidenceStore, synthetic files, no hook/backend. Zero x Youngseok Oh."""
import hashlib, importlib.util, json, os, platform, sqlite3, subprocess, sys, tempfile, urllib.request
from contextlib import closing
from pathlib import Path

ROOT = Path('results').resolve()
REF = 'c93420c49a6b14c3d446bdb156d96811908fd90a'
SOURCES = {'original.py': ('integrations/agent-plugin-core/python/memory_core.py','9b420a0634f9c81656233b3fde7540a500ea1a4f'), 'telemetry.py': ('integrations/claude-code-plugin/core/telemetry.py','c1fc0084c0783e80b6e4ca15fdb599fc3bbbe2d1'), 'LICENSE.mem0': ('LICENSE','d20d5102c3cf97ecbee54afd65893de4a11d26fe')}


def inspect_db(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as c:
        return {'check':c.execute('PRAGMA quick_check').fetchone()[0], 'rows':c.execute('SELECT COUNT(*) FROM events').fetchone()[0]}


def one(label, case):
    os.environ['MEM0_TELEMETRY']='false'
    def deny(event,args):
        if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('No network during probe')
    sys.addaudithook(deny)
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('memory_core',ROOT/(label+'.py'))
    m=importlib.util.module_from_spec(spec);sys.modules['memory_core']=m;spec.loader.exec_module(m)
    assert not m.telemetry.is_enabled()
    # Only disabled telemetry is observed. No SQLite/path method is replaced.
    telemetry=[];m.telemetry.record=lambda name:telemetry.append(name)
    with tempfile.TemporaryDirectory(prefix='zero-evidence-') as d:
        p=Path(d)/'evidence.sqlite3';holder=None;store=None;before=None
        if case=='notadb': p.write_bytes(b'INTENTIONAL_NON_DATABASE_TEST_FIXTURE\n')
        else:
            seed=m.EvidenceStore(p)
            seed.conn.execute('INSERT INTO events(repo_id,app_id,session_id,created_at,kind,payload_json) VALUES(?,?,?,?,?,?)',('r','a','s','2026-01-01','user_prompt','{"text":"SYNTHETIC_SENTINEL"}'))
            seed.conn.commit();seed.close()
            with closing(sqlite3.connect(p)) as c:
                c.execute('PRAGMA journal_mode=DELETE').fetchone()
                if case=='schema':c.execute('CREATE VIEW sidekick_calls AS SELECT 1');c.commit()
            before=inspect_db(p)
        initial=p.read_bytes()
        if case=='busy':
            holder=sqlite3.connect(p);holder.execute('BEGIN EXCLUSIVE')
        outcome='opened';error=None
        try: store=m.EvidenceStore(p)
        except sqlite3.DatabaseError as e:
            outcome='raised';error={'code':getattr(e,'sqlite_errorcode',None),'name':getattr(e,'sqlite_errorname',None),'message':str(e)}
        finally:
            if holder is not None:holder.rollback();holder.close()
            if store is not None:store.close()
        parked=[x for x in p.parent.glob('evidence.sqlite3.corrupt-*') if not x.name.endswith(('-wal','-shm'))]
        after=inspect_db(p)
        r={'variant':label,'case':case,'before':before,'after':after,'outcome':outcome,'error':error,'parked_main_files':len(parked),'telemetry':telemetry}
        if case=='normal':assert after['rows']==1 and outcome=='opened' and not parked
        elif case=='notadb':
            r['fixture_preserved']=len(parked)==1 and parked[0].read_bytes()==initial
            assert outcome=='opened' and after['rows']==0 and r['fixture_preserved']
        elif label=='original':
            assert outcome=='opened' and after['rows']==0 and len(parked)==1
            r['parked_database']=inspect_db(parked[0]);assert r['parked_database']=={'check':'ok','rows':1}
        else:
            assert outcome=='raised' and after=={'check':'ok','rows':1} and not parked and not telemetry
            assert error['code']==(sqlite3.SQLITE_BUSY if case=='busy' else sqlite3.SQLITE_ERROR)
            if case=='busy':
                retry=m.EvidenceStore(p);retry.close();r['retry_after_release']=inspect_db(p);assert r['retry_after_release']['rows']==1
            else:
                with closing(sqlite3.connect(p)) as c:assert c.execute("SELECT type FROM sqlite_master WHERE name='sidekick_calls'").fetchone()==('view',)
        return r


def main():
    if len(sys.argv)==3:
        print(json.dumps(one(*sys.argv[1:]),indent=2));return
    ROOT.mkdir(exist_ok=False)
    for name,(path,blob) in SOURCES.items():
        with urllib.request.urlopen(f'https://raw.githubusercontent.com/mem0ai/mem0/{REF}/{path}',timeout=30) as r:raw=r.read(1000001)
        assert len(raw)<=1000000 and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob
        (ROOT/name).write_bytes(raw)
    original=(ROOT/'original.py').read_text()
    old='        except sqlite3.DatabaseError:\n            self._quarantine()\n            self._open()'
    new='''        except sqlite3.DatabaseError as exc:
            code = getattr(exc, "sqlite_errorcode", None)
            if not isinstance(code, int) or (code & 0xFF) not in (
                sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB
            ):
                raise
            self._quarantine()
            self._open()'''
    assert original.count(old)==1
    candidate=original.replace(old,new,1);(ROOT/'candidate.py').write_text(candidate)
    expected={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('original.py','candidate.py','telemetry.py')}
    rows=[]
    for case in ('normal','busy','schema','notadb'):
        for label in ('original','candidate'):
            r=subprocess.run([sys.executable,__file__,label,case],capture_output=True,text=True,timeout=40)
            (ROOT/f'{case}-{label}.log').write_text(r.stdout+r.stderr)
            assert r.returncode==0,(label,case,r.stderr)
            rows.append(json.loads(r.stdout))
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==v for name,v in expected.items())
    report={'source_commit':REF,'source_blobs':SOURCES,'source_sha256':expected,'python':sys.version,'sqlite':sqlite3.sqlite_version,'platform':platform.platform(),'scenarios':rows,'observations_passed':8,'source_unchanged_after_run':True,'scope':'Full memory_core module imported; actual EvidenceStore on synthetic SQLite files. Only disabled telemetry observed. No Claude hook, Windows, remote memory service, user data, or upstream PR.'}
    (ROOT/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
