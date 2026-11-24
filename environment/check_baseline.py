"""Audit the standard baseline against saved evidence; this does not simulate RTL."""
import hashlib,json
from pathlib import Path
from .reset import ROOT
from .validate_v3 import NAMES
from verifier.scenarios import suite


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(root=ROOT):
    root=Path(root)
    manifest=json.loads((root/'tasks/axil_to_apb4_001/baseline.json').read_text())
    errors=[]
    def require(condition,message):
        if not condition:errors.append(message)
    require(manifest['status']=='standard_baseline','Baseline is not designated standard')
    for group in ('runtime_files','evidence_files'):
        for name,expected in manifest[group].items():
            p=root/name
            require(p.is_file() and digest(p)==expected,'File changed/missing: '+name)
    for name in manifest['retired_paths']:
        require(not (root/name).exists(),'Retired implementation is present: '+name)
    evidence=root/manifest['evidence_root']
    frozen=json.loads((evidence/'agent/freeze.json').read_text())
    for name in manifest['proven_runtime_files']:
        require(name in frozen['files'] and manifest['runtime_files'][name]==frozen['files'][name],
                'Runtime differs from measured episode: '+name)
    controls=json.loads((evidence/'controls-summary.json').read_text())
    require(controls['accepted'] and set(controls['results'])==set(NAMES),'Incomplete control bank')
    for name in NAMES:
        result=controls['results'][name]
        require(result['reward']==(1.0 if name=='reference' else 0.0),'Wrong control verdict: '+name)
        require(result['fixture_sha256']==digest(root/'fixtures'/(name+'.sv')),'Fixture changed: '+name)
    reference=controls['results']['reference']
    plan=suite(False)
    expected_names=[c['name'] for c in plan]
    expected_suite_hash=hashlib.sha256(json.dumps(plan,indent=2).encode()).hexdigest()
    require(reference['suite_sha256']==expected_suite_hash,'Default stimulus differs from verified inputs')
    require(reference['required_cases']==expected_names,'Required case list changed')
    require(len(plan)==22 and sum(len(c['rows']) for c in plan)==2868,'Full suite size changed')
    public=suite(True,17)
    require(len(public)==17 and sum(len(c['rows']) for c in public)==132,'Public suite size changed')
    agent=json.loads((evidence/'agent/result.json').read_text())
    reserved=json.loads((evidence/'agent/reserved-evaluation/result.json').read_text())
    for name,result in [('reference',reference),('agent',agent),('reserved',reserved)]:
        require(result['reward']==1 and result['verification_complete'],name+' did not complete successfully')
        require(result['required_cases']==expected_names and len(result['cases'])==22,name+' missing cases')
        require(all(c['reward']==1 for c in result['cases']),name+' contains a failed case')
        require((result['planned'],result['checked'],result['aborted'])==(2868,2842,26),name+' accounting mismatch')
        require(result['functional_cross']=={'required':576,'observed':576,'missing':[]},name+' cross coverage incomplete')
    require(agent['freeze_unchanged'],'Episode freeze failed')
    require(agent['suite_sha256']==frozen['private_reward_suite_sha256'],'Reward input hash mismatch')
    require(reserved['suite_sha256']==frozen['reserved_evaluation_suite_sha256'],'Reserved input hash mismatch')
    require(agent['suite_sha256']!=reserved['suite_sha256'],'Reward/evaluation inputs are identical')
    require(agent['source_sha256']==reserved['source_sha256']==digest(evidence/'agent/final.sv'),'Submission identity mismatch')
    require(bool(json.loads((evidence/'agent/harness-provenance.json').read_text())),'Missing actual Harness events')
    return {'baseline':manifest['id'],'status':'pass' if not errors else 'fail',
            'check':'saved-evidence-and-source-consistency','simulation_executed':False,'errors':errors}


if __name__=='__main__':
    try:result=check()
    except Exception as e:result={'status':'fail','simulation_executed':False,'errors':[type(e).__name__+': '+str(e)]}
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['status']=='pass' else 1)
