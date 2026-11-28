"""Function first; only complete consistent mappings can receive a resource grade."""
import argparse,json,re,time
from pathlib import Path
from verifier.bitfold_synth.campaign import grade as functional_grade,ROOT,sha
TASK='bitfold_cell_budget_v1'
VERSION='bitfold-cell-budget-verifier-v1'
LIMIT=22
LIBRARY_SHA256='3bfd6dc6041095c7a15815a6f95762fd24a19d6836cfbe7994515532b41caa89'

def measurement(base,log):
    if base.get('reward')!=1 or not base.get('verification_complete'):return None
    if base.get('library_sha256')!=LIBRARY_SHA256:raise ValueError('Frozen library mismatch')
    if any(base.get(k,{}).get('reward')!=1 for k in ('integer_oracle','synthesis','independent_reference','own_netlist')):raise ValueError('Incomplete prerequisite checks')
    values=re.findall(r'^PB_CELLS=(\d+)\s*$',log,re.M)
    if len(values)!=1:raise ValueError('Missing or ambiguous structural count')
    return {'metric_version':'dc-mapped-instance-count-v1','mapped_cell_count':int(values[0]),'limit':LIMIT,'functional_checks_passed':True}

def grade(task,source,out,phase='public'):
    if task!=TASK:raise ValueError('Unknown optimization task')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source);start=time.monotonic()
    r=dict(task_id=task,phase=phase,source_sha256=sha(source),verifier_version=VERSION,grader_sha256=sha(__file__),reward=None,category='infrastructure_error',verification_complete=False)
    try:
        base=functional_grade('bitfold_population_repair_v1',source,out/'functional',phase)
        r.update(base);r.update(task_id=TASK,verifier_version=VERSION,grader_sha256=sha(__file__),functional_grader_sha256=base['grader_sha256'])
        r['base_task_id']='bitfold_population_repair_v1'
        if base.get('reward')!=1:return r
        m=measurement(base,(out/'functional/synthesis.log').read_text());r['resource_measurement']=m
        if m['mapped_cell_count']>LIMIT:r.update(reward=0.,category='synthesis_error',reason='mapped_cell_budget_exceeded',verification_complete=True)
        return r
    except ValueError as e:r.update(reward=None,category='infrastructure_error',verification_complete=False,reason=str(e));return r
    finally:
        r['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(TASK,a.source,a.out,a.phase),indent=2))
