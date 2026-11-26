"""Source-bound admission summaries for trusted generated task families."""
import argparse,hashlib,json
from pathlib import Path
from task_families.package import verify
from environment.control_bank import bundle
from task_families.router_v1.report import numeric_cost
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def report(package,gate,job=None):
 package=Path(package);gate=Path(gate);m=verify(package);r=json.loads((gate/'result.json').read_text());f=json.loads((gate/'freeze.json').read_text());tid=m['task_id']
 if not r.get('accepted') or r['task_id']!=tid or f['task_id']!=tid or r['freeze_sha256']!=sha(gate/'freeze.json'):raise ValueError('Admission identity mismatch')
 expected={k:v for k,v in m['files'].items() if k.startswith('tasks/'+tid+'/') or k.split('/')[0] in ('environment','verifier','fixtures','tests')}
 if f['files']!=expected:raise ValueError('Runtime snapshot differs from admission')
 q=json.loads((package/'tasks'/tid/'task.json').read_text())['quality'];entries=q['references']+[x['source'] for x in q['negative_controls']]
 if sha(ROOT/'environment/control_bank.py')!=m['files']['environment/control_bank.py']:raise ValueError('Bank builder changed')
 bank_hash=hashlib.sha256(bundle([package/x for x in entries]).encode()).hexdigest()
 if bank_hash!=sha(gate/'control_bank.sv'):raise ValueError('Compiled control bank differs')
 controls={};selected={Path(entry).stem:(i,entry) for i,entry in enumerate(entries)}
 if not set(selected).issubset(r['results']):raise ValueError('Missing control result')
 for name,v in r['results'].items():
  controls[name]=dict(v)
  selection=selected.get(name[:-7] if name.endswith('-public') else name)
  if selection:
   i,entry=selection
   if v['source_sha256']!=bank_hash:raise ValueError('Control provenance mismatch')
   controls[name].update(variant=i,fixture_sha256=sha(package/entry))
 if r['results']['initial']['source_sha256']!=sha(package/'tasks'/tid/'workspace/bridge.sv'):raise ValueError('Initial RTL provenance mismatch')
 timings=[e for p in gate.rglob('timing.json') for e in json.loads(p.read_text())]
 j=json.loads(Path(job).read_text()) if job else None
 if j and (j.get('status')!='finished' or j.get('exit_code')!=0):raise ValueError('Unfinished gate job')
 return {'schema':'family-admission-summary-v1','task_id':tid,'accepted':True,'manifest_sha256':sha(package/'family-manifest.json'),'gate_freeze_sha256':sha(gate/'freeze.json'),'gate_result_sha256':sha(gate/'result.json'),'reporter_sha256':sha(__file__),'toolchain':f['toolchain'],'positive_count':r['positive_count'],'negative_count':r['negative_count'],'mechanism_checks':r['mechanism_checks'],'isolation':r['isolation_probe_accepted'],'controls':controls,'source_file_count':len(m['files']),'source_bytes':sum((package/x).stat().st_size for x in m['files']),'wall_seconds':j['ended']-j['started'] if j else None,'instrumented_subprocess_seconds':{k:sum(e['wall_seconds'] for e in timings if e['kind']==k) for k in ('compile','simulate','io')} if timings else None,'timing_scope':'Instrumented control and session calls only; classification/initial checks without timing are excluded. These measurements are subsets of gate wall time.','numeric_eda_cost':numeric_cost(gate),'limitations':r['limitations']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('gate');p.add_argument('--job');p.add_argument('--out',required=True);a=p.parse_args()
 value=report(a.package,a.gate,a.job)
 with Path(a.out).open('x') as f:f.write(json.dumps(value,indent=2)+'\n')
