"""Source-bound execution-package production; industrial qualification is separate."""
import argparse,json,time
from pathlib import Path
from task_families.production_lock import exclusive
from task_families.router_v2.generate import verify,sha
from task_families.router_v2.batch import save
from .materialize import materialize
ROOT=Path(__file__).resolve().parents[2]
DEPENDENCIES=('task_families/production_lock.py','task_families/router_v3/batch.py',
              'task_families/router_v3/materialize.py','task_families/router_v3/qualification.py',
              'task_families/router_v2/generate.py','task_families/router_v2/batch.py')


def run(planfile,out):
    planfile=Path(planfile).resolve();plan=json.loads(planfile.read_text());out=Path(out)
    if set(plan)!= {'schema','producer_files','parents'} or plan['schema']!='router-execution-batch-v1':
        raise ValueError('Unsupported production plan')
    if set(plan['producer_files'])!=set(DEPENDENCIES) or any(sha(ROOT/f)!=h for f,h in plan['producer_files'].items()):
        raise ValueError('Incomplete or changed producer dependency set')
    if not 1<=len(plan['parents'])<=30:raise ValueError('Bounded batch size required')
    identities=set()
    for row in plan['parents']:
        if set(row)!= {'path','manifest_sha256'}:raise ValueError('Invalid parent descriptor')
        source=Path(row['path'])
        if not source.is_absolute():raise ValueError('Parent paths must be explicit absolute paths')
        m=verify(source)
        if sha(source/'family-manifest.json')!=row['manifest_sha256']:raise ValueError('Parent changed')
        if m['task_id'] in identities:raise ValueError('Duplicate contract identity')
        identities.add(m['task_id'])
    with exclusive(out):
        freeze=out/'plan.json'
        if freeze.exists():
            if sha(freeze)!=sha(planfile):raise ValueError('Different plan cannot resume this batch')
        else:freeze.write_bytes(planfile.read_bytes())
        records=[]
        for row in plan['parents']:
            parent=Path(row['path']);tid=verify(parent)['task_id'];dest=out/tid;record=out/(tid+'.json')
            if record.exists():
                result=json.loads(record.read_text())
                if result['status']=='generated':
                    verify(dest)
                    if sha(dest/'family-manifest.json')!=result['manifest_sha256']:raise ValueError('Completed artifact changed')
                records.append(result)
                if result['status']!='generated':break
                continue
            if dest.exists():raise ValueError('Interrupted package preserved; review before continuing')
            start=time.monotonic()
            try:
                materialize(parent,dest)
                result={'task_id':tid,'status':'generated','manifest_sha256':sha(dest/'family-manifest.json')}
            except Exception as error:
                result={'task_id':tid,'status':'generation_failed','error_type':type(error).__name__}
            result.update(parent_manifest_sha256=row['manifest_sha256'],wall_seconds=time.monotonic()-start,industrial_admission='not_run')
            save(record,result);records.append(result);save(out/'progress.json',records)
            print(tid,result['status'],flush=True)
            if result['status']!='generated':break
        summary={'schema':'router-execution-production-v1','plan_sha256':sha(freeze),'planned':len(plan['parents']),
                 'generated':sum(r['status']=='generated' for r in records),'admitted':0,'rows':records}
        save(out/'result.json',summary);return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');a=p.parse_args()
    r=run(a.plan,a.out);print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
