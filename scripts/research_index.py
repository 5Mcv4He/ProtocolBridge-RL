"""Join task contracts with reviewed cohort evidence, without changing task freezes."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.tasks import load_catalog
from scripts.export_rollout_exchange import validate_source,sha

def build(sources):
    catalog=load_catalog();tasks={};seen=set()
    for source in sources:
        source=Path(source).resolve();relative=str(source.relative_to(ROOT));m,rows,_,_=validate_source(source);h=sha(source/'experiment.json')
        if h in seen:raise ValueError('Duplicate cohort')
        seen.add(h);name=m.get('task_id','axil_to_apb4_001');t=catalog[name]
        if name not in tasks:tasks[name]={k:t[k] for k in ('task_id','version','title','metadata','spec','initial_rtl','verifier','capabilities','protocols','quality_kind','reward_contract')};tasks[name]['cohorts']=[];tasks[name]['calibration']='Empirical, cohort-specific; no absolute Easy/Hard label';tasks[name]['contamination_risks']=['Spec, reference RTL and verifier source are public and may enter future pretraining','Solver runtime hides reference/private inputs, but this does not establish absence of prior model knowledge','Held-out uses separate inputs of the same task, not an unseen task family']
        groups={}
        for policy in m['policies']:
            rs=[r for r in rows if r['policy']==policy]
            groups[policy]={'started':len(rs),'valid_submissions':sum(bool(r.get('valid_submission')) for r in rs),'reward_counts':{k:sum(r['reward']==v for r in rs) for k,v in [('one',1),('zero',0),('null',None)]},'feedback_exposed':sum(bool(r.get('feedback')) for r in rs),'tokens':sum(r['tokens']['totalTokens'] for r in rs) if all((r.get('tokens') or {}).get('totalTokens') is not None for r in rs) else None,'episode_seconds':sum(r['wall_seconds'] for r in rs) if all(r.get('wall_seconds') is not None for r in rs) else None,'terminal_categories':{c:sum(r.get('terminal_category','unknown')==c for r in rs) for c in sorted(set(r.get('terminal_category','unknown') for r in rs))}}
        tasks[name]['cohorts'].append({'evidence':relative,'experiment_sha256':h,'publication_sha256':sha(source/'publication.json'),'study':m.get('study'),'environment_capabilities':m.get('capabilities'),'protocol':m.get('protocol'),'model':m['model'],'source_commit':m['source_commit'],'task_metadata_sha256':m['source_files'].get(t['metadata']),'matching_current_task_version':t['version'] if sha(ROOT/t['metadata'])==m['source_files'].get(t['metadata']) else None,'verifier_manifest_sha256':hashlib.sha256(json.dumps({k:v for k,v in m['source_files'].items() if k.startswith('verifier/')},sort_keys=True).encode()).hexdigest(),'toolchain':m.get('toolchain',{}),'groups':groups,'api_currency_cost':None})
    return {'schema':'task-research-index-v1','scope':'Research evidence index, not execution admission. Cohorts remain separate; no pooled task success-rate ranking. Task contracts stay frozen while measurements accumulate.','generator_sha256':sha(__file__),'tasks':tasks}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('sources',nargs='+');a=p.parse_args();r=build(a.sources)
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({'tasks':len(r['tasks']),'cohorts':sum(len(t['cohorts']) for t in r['tasks'].values())}))
