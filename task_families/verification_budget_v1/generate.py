"""Budget-only study overlay on the frozen depth-three engineering laboratory."""
import argparse,json,shutil
from pathlib import Path
from task_families.engineering_lab_v1.generate import generate as parent_generate,TASK
from task_families.capsule import ROOT,finish,write

def replace(path,old,new):
    text=path.read_text()
    if text.count(old)!=1:raise ValueError('Source anchor changed: '+str(path)+' '+old[:50])
    path.write_text(text.replace(old,new))

def generate(out):
    out=Path(out).resolve();parent=parent_generate(out);write(out/'budget-parent.json',parent)
    for name in ('verification_budget.py','verification_budget_acceptance.py','verification_preflight.py'):
        shutil.copyfile(ROOT/'environment'/name,out/'environment'/name)
    p=out/'environment/policy.py'
    replace(p,'def validate(p):','def _validate_v1(p):')
    replace(p,'def load(name):','def validate(p):\n    from .verification_budget import validate as budget_validate\n    return budget_validate(p,_validate_v1)\n\ndef load(name,public_test_budget=None):')
    replace(p,'    return policy\n','    from .verification_budget import derive\n    return derive(policy,public_test_budget,_validate_v1)\n')
    replace(out/'environment/batch_contract.py','one of the same two public calls.','one of the declared public test calls.')
    replace(out/'environment/runtime_session.py','2 full public tests remain unchanged.','the public test allowance is stated above.')
    replace(out/'environment/synthesis_session.py','the two public functional tests are unchanged.','the public functional test allowance is stated above.')
    p=out/'environment/engineering_lab.py'
    replace(p,"        (self.out / 'capabilities.json').write_text(json.dumps(PROFILE, indent=2) + '\\n')","        profile=dict(PROFILE,max_public_test_calls=self.policy['max_public_test_calls'])\n        if self.policy['version']==2:profile['budget_condition']='verification-budget-v1-test%d'%self.policy['max_public_test_calls']\n        (self.out / 'capabilities.json').write_text(json.dumps(profile, indent=2) + '\\n')")
    p=out/'environment/policy_utm_agent.py'
    replace(p,"policy=load(bootstrap['policy'])","policy=load(bootstrap['policy'],bootstrap.get('public_test_budget'))")
    p=out/'environment/policy_experiment.py'
    replace(p,'paired_inputs=None):','paired_inputs=None,public_test_budget=None,preflight_from=None):')
    replace(p,'    selected={p:load(p) for p in policies}',"    if public_test_budget is not None and (capabilities!='engineering-lab-v1' or policies!=['test_diagnostic']):raise ValueError('Budget condition requires combined diagnostic environment')\n    selected={p:load(p,public_test_budget) for p in policies}")
    replace(p,"manifest={'task_id':task_id,","manifest={'public_test_budget':public_test_budget,'budget_study_version':'verification-budget-v1' if public_test_budget is not None else None,'task_id':task_id,")
    replace(p,"        if capabilities!=manifest.get('capabilities'):","        if public_test_budget!=manifest.get('public_test_budget'):raise ValueError('Resume budget mismatch')\n        if capabilities!=manifest.get('capabilities'):")
    replace(p,"    if capabilities in ('runtime-verdict-v1','runtime-events-v2','engineering-lab-v1'):\n        rc=", "    if preflight_from is not None and not resume:\n        from .verification_preflight import reuse\n        reuse(out,preflight_from,manifest)\n    if capabilities in ('runtime-verdict-v1','runtime-events-v2','engineering-lab-v1'):\n        rc=")
    replace(p,'    for trial in schedule[:limit]:',"    if public_test_budget is not None:\n        rc=0 if (out/'budget-acceptance/result.json').exists() else remote('environment.verification_budget_acceptance',['budget-acceptance','private/r01-reward.json'],'budget-acceptance-controller.log')\n        fetch('budget-acceptance')\n        if rc or not json.loads((out/'budget-acceptance/result.json').read_text()).get('accepted'):raise RuntimeError('Budget mechanism acceptance failed')\n        if not resume:clean_builds('budget-acceptance')\n        from .verification_preflight import seal\n        seal(out,manifest)\n    for trial in schedule[:limit]:")
    replace(p,"bootstrap={'task_id':task_id,","bootstrap={'public_test_budget':public_test_budget,'task_id':task_id,")
    replace(p,'    a=p.parse_args()',"    p.add_argument('--public-test-budget',type=int,choices=(2,6));p.add_argument('--preflight-from')\n    a=p.parse_args()")
    replace(p,'a.capabilities,a.paired_inputs)','a.capabilities,a.paired_inputs,a.public_test_budget,a.preflight_from)')
    # Budget and all current-candidate bindings remain independently audited.
    p=out/'scripts/audit_policy.py'
    replace(p,"        policy=validate(json.loads((d/'policy.json').read_text()))","        policy=validate(json.loads((d/'policy.json').read_text()))\n        if experiment.get('public_test_budget') is not None:\n            require(policy['version']==2 and policy['max_public_test_calls']==experiment['public_test_budget'],name+': budget condition mismatch')")
    files=[Path(__file__)]+[ROOT/'environment'/n for n in ('verification_budget.py','verification_budget_acceptance.py','verification_preflight.py')]
    return finish(out,TASK,parent['family'],dict(parent['parameters'],verification_budget_version=1),files)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();print(generate(a.out)['task_id'])
