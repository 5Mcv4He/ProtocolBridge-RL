"""Bounded restart-safe candidate production. Generation never implies admission."""
import argparse,hashlib,json,time
from pathlib import Path
from .contract import validate_domain,obligations
from .generate import generate,verify,sha,ROOT

def save(p,x):
 p=Path(p);t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2)+'\n');t.replace(p)
def run(planfile,out):
 planfile=Path(planfile);plan=json.loads(planfile.read_text());out=Path(out)
 if not 1<=len(plan['contracts'])<=30:raise ValueError('Batch size exceeds bounded production scope')
 if any(sha(ROOT/f)!=h for f,h in plan['producer_files'].items()):raise ValueError('Producer changed since plan freeze')
 required={'task_families/router_v2/batch.py','task_families/router_v2/contract.py','task_families/router_v2/generate.py','task_families/router_v1/generate.py','task_families/router_v1/scenarios.py.in'}
 if set(plan['producer_files'])!=required:raise ValueError('Missing producer dependency')
 seen=set();ids=set()
 for c in plan['contracts']:
  validate_domain(c);key=json.dumps(c['windows'])
  if key in seen or c['task_id'] in ids:raise ValueError('Duplicate contract or task identity')
  seen.add(key);ids.add(c['task_id'])
 out.mkdir(parents=True,exist_ok=True);freeze=out/'plan.json'
 if freeze.exists():
  if sha(freeze)!=sha(planfile):raise ValueError('Cannot resume a different frozen batch')
 else:freeze.write_bytes(planfile.read_bytes())
 rows=[]
 for c in plan['contracts']:
  dest=out/c['task_id'];record=out/(c['task_id']+'.json')
  if record.exists():
   row=json.loads(record.read_text())
   if row['status']=='generated':
    verify(dest)
    if sha(dest/'family-manifest.json')!=row['manifest_sha256']:raise ValueError('Completed candidate changed')
   rows.append(row);continue
  if dest.exists():raise ValueError('Interrupted candidate preserved; explicit diagnosis required before continuing: '+c['task_id'])
  start=time.monotonic()
  try:
   result=generate(c,dest);row=dict(task_id=c['task_id'],status='generated',manifest_sha256=result['manifest_sha256'],obligations=obligations(c),industrial_admission='not_run',model_trials=0)
  except Exception as e:
   row=dict(task_id=c['task_id'],status='generation_failed',error_type=type(e).__name__,industrial_admission='not_run',model_trials=0)
  row['generation_wall_seconds']=round(time.monotonic()-start,4);save(record,row);rows.append(row)
  save(out/'progress.json',{'plan_sha256':sha(freeze),'rows':rows})
  print(c['task_id'],row['status'],flush=True)
  if row['status']!='generated':break
 result={'schema':'router-production-batch-v2','plan_sha256':sha(freeze),'planned':len(plan['contracts']),'recorded':len(rows),'generated':sum(r['status']=='generated' for r in rows),'industrially_admitted':0,'model_trials':0,'rows':rows}
 save(out/'result.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');a=p.parse_args();r=run(a.plan,a.out);print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
