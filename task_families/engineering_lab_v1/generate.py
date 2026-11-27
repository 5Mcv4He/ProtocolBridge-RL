"""An environment overlay on the unchanged reviewed depth-three queue contract."""
import argparse
import json
import shutil
from pathlib import Path
from task_families.queue_v1.generate import generate as queue_generate, HERE as QUEUE
from task_families.capsule import ROOT, finish, write

TASK='x2p_queue_three_v1'

def generate(out):
    out=Path(out).resolve()
    contract=next(x for x in json.loads((QUEUE/'contracts.json').read_text())['instances'] if x['task_id']==TASK)
    parent=queue_generate(contract,out)
    write(out/'environment-parent.json',parent)
    for name in ('engineering_lab.py','engineering_lab_acceptance.py'):
        shutil.copyfile(ROOT/'environment'/name,out/'environment'/name)
    p=out/'environment/engineering_lab.py';p.write_text(p.read_text().replace('axil_to_apb4_queue_003',TASK))
    p=out/'environment/policy_experiment.py';s=p.read_text()
    s=s.replace("(None,'engineering-tools-v1'", "(None,'engineering-lab-v1','engineering-tools-v1'")
    s=s.replace("choices=['engineering-tools-v1'", "choices=['engineering-lab-v1','engineering-tools-v1'")
    s=s.replace("if capabilities=='engineering-tools-v1' and", "if capabilities in ('engineering-lab-v1','engineering-tools-v1') and")
    s=s.replace("if capabilities=='synthesis-tools-v1':from .synthesis_session import extend_prompt", "if capabilities=='engineering-lab-v1':from .engineering_lab import extend_prompt\n            elif capabilities=='synthesis-tools-v1':from .synthesis_session import extend_prompt")
    s=s.replace("if capabilities=='synthesis-tools-v1':", "if capabilities in ('synthesis-tools-v1','engineering-lab-v1'):")
    s=s.replace("if capabilities in ('runtime-verdict-v1','runtime-events-v2'):\n        rc=", "if capabilities in ('runtime-verdict-v1','runtime-events-v2','engineering-lab-v1'):\n        rc=")
    needle="    print('Running real deterministic mechanism acceptance"
    s=s.replace(needle,"    if capabilities=='engineering-lab-v1':\n        rc=0 if (out/'lab-acceptance/result.json').exists() else remote('environment.engineering_lab_acceptance',['lab-acceptance'],'lab-acceptance-controller.log')\n        fetch('lab-acceptance')\n        if rc or json.loads((out/'lab-acceptance/result.json').read_text()).get('accepted') is not True:raise RuntimeError('Combined capability acceptance failed')\n"+needle)
    p.write_text(s)
    p=out/'environment/policy_utm_agent.py';s=p.read_text()
    s=s.replace("        if capabilities in ('runtime-verdict-v1'", "        if capabilities=='engineering-lab-v1':\n            from .engineering_lab import Session as session_type\n        elif capabilities in ('runtime-verdict-v1'",1)
    s=s.replace("        elif capabilities=='synthesis-tools-v1':from .synthesis_session import extend_prompt", "        elif capabilities=='engineering-lab-v1':from .engineering_lab import extend_prompt\n        elif capabilities=='synthesis-tools-v1':from .synthesis_session import extend_prompt")
    p.write_text(s)
    p=out/'scripts/audit_policy.py';s=p.read_text()
    s=s.replace("            if capabilities in ('runtime-verdict-v1'", "            if capabilities=='engineering-lab-v1':\n                from environment.engineering_lab import PROFILE,extend_prompt\n                require(task_id=='"+TASK+"' and policy['policy_id']=='test_diagnostic',name+': invalid combined profile')\n            elif capabilities in ('runtime-verdict-v1'",1)
    s=s.replace("capabilities=='runtime-events-v2'", "capabilities in ('runtime-events-v2','engineering-lab-v1')")
    needle="            if event['executed']:\n"
    code="""            actual_obs=obs
            if capabilities=='engineering-lab-v1' and event['executed'] and tool in ('edit','submit','test','compile','inspect','synth_check','experiment','observe'):
                obs=dict(obs);binding=obs.pop('candidate_binding',None)
                current=hashlib.sha256(action['content'].encode()).hexdigest() if tool=='edit' else active_source
                result=current
                if tool=='inspect':result=last_public[1]['source_sha256'] if last_public else None
                elif tool=='observe':result=last_lab[1]['source_sha256'] if last_lab else None
                require(binding=={'current_sha256':current,'result_sha256':result,'is_current':current==result},name+': candidate/result binding mismatch')
"""
    assert s.count(needle)==1;s=s.replace(needle,code+needle)
    s=s.replace("=={'tool_result':obs}","=={'tool_result':actual_obs}")
    p.write_text(s)
    # Use the depth-specialized capacity mutant for the capacity-specific
    # synthesis/functional independence assertion. Early-credit also breaks
    # registered scheduling first and is not a capacity-only negative control.
    p=out/'environment/synthesis_acceptance.py'
    p.write_text(p.read_text().replace('bad_early_credit.sv','bad_over_capacity.sv'))
    # Preserve the task semantics but use the backend's configured environment.
    p=out/'verifier/task003/campaign.py';s=p.read_text().replace('from .scenarios import suite,REQUIRED_BINS','from .scenarios import suite,REQUIRED_BINS\nfrom environment.remote_backend import remote_command')
    s=s.replace("return run((['/bin/bash','-lc',command] if local else ssh+[command]),timeout)","return run((['/bin/bash','-lc',remote_command(cfg,command)] if local else ssh+[remote_command(cfg,command)]),timeout)").replace('source ~/.bashrc; ','');p.write_text(s)
    p=out/'environment/engineering_tools.py';s=p.read_text().replace("['bash','-lc',command]","['bash','-lc',remote_command(cfg,command)]").replace('source ~/.bashrc; ','');p.write_text(s)
    files=[Path(__file__),ROOT/'task_families/capsule.py',ROOT/'environment/engineering_lab.py',ROOT/'environment/engineering_lab_acceptance.py']
    return finish(out,TASK,parent['family'],dict(contract,environment='engineering-lab-v1'),files)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();print(generate(a.out)['task_id'])
