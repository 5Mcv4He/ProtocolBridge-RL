"""Current-only pool: historical v2 receipts are explicitly refused.

Query source-matched generated task admissions; fail closed on stale records.

This is a local index of executable environments, not a count of generated
candidates or a collection of previously successful Agent trajectories.
"""
import argparse,json
from pathlib import Path
from environment.package_admission_v3 import validate,sha

def query(directory,config):
    rows=[];seen=set()
    for p in sorted(Path(directory).glob('*.json')):
        a=validate(p,config)
        if a['task_id'] in seen:raise ValueError('Duplicate admitted task identity')
        seen.add(a['task_id']);root=Path(a['package'])
        m=json.loads((root/'family-manifest.json').read_text());task=json.loads((root/'tasks'/a['task_id']/'task.json').read_text())
        rows.append({'task_id':a['task_id'],'admission':str(p.resolve()),'admission_sha256':sha(p),
                     'package_manifest_sha256':a['package_manifest_sha256'],'family':m['family'],
                     'capabilities':task['capabilities'],'deliverable':'bridge.sv','task_form':'rtl_implementation',
                     'initial_sha256':sha(root/'tasks'/a['task_id']/'workspace/bridge.sv'),
                     'status':'source_matched_admitted','difficulty':'not_inferred_from_admission'})
    return {'schema':'generated-task-pool-v2','count':len(rows),'tasks':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('config');a=p.parse_args()
    print(json.dumps(query(a.directory,a.config),indent=2))
