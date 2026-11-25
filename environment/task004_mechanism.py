"""Deterministic end-to-end policy acceptance using the real VCS grader (no model)."""
import argparse,json
from pathlib import Path
from .policy import load,parse_action
from .task004 import Session
from .batch_contract import PROTOCOLS
from .reset import ROOT
from verifier.task004.campaign import grade,sha


def run(out,reward_path,protocol=PROTOCOLS[0]):
    if protocol not in PROTOCOLS:raise ValueError('Unknown action protocol')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    reward=json.loads(Path(reward_path).read_text());builds={};runs={};checks=[]
    for mode in ('spec_only','test_verdict','test_diagnostic'):
        work=out/(mode+'-work');work.mkdir()
        (work/'spec.md').write_bytes((ROOT/'tasks/axil_to_apb4_decoupled_004/spec.md').read_bytes())
        (work/'bridge.sv').write_bytes((ROOT/'fixtures/task004/bad_strobe.sv').read_bytes())
        calls=[]
        def counted(source,dest,**kw):
            calls.append({'public':kw.get('public',False),'cases_sha256':sha(reward_path) if 'cases' in kw else None})
            return grade(source,dest,**kw)
        s=Session(load(mode),work,out/mode,reward,counted,reuse=builds)
        s.protocol_version=2 if protocol==PROTOCOLS[1] else 1
        # A malformed/multiple-action reply must not skip an edit and execute
        # a later test/submit. This uses the same parser as the real controller.
        try:action=parse_action('{"tool":"edit","content":"module bridge;\nendmodule"}\n{"tool":"test"}\n{"tool":"submit"}')
        except ValueError:action={}
        rejected=s.handle(action)
        checks.append(rejected.get('reason')=='invalid_action_format' and not calls and not s.submitted)
        if s.protocol_version==2:
            before=sha(work/'bridge.sv')
            invalid=s.handle({'tool':'edit','content':'module bridge; endmodule','content_note':'overwrite'})
            checks.append(invalid['reason']=='invalid_action' and sha(work/'bridge.sv')==before and not calls and s.edits==0)
            checks.append(invalid['action_fields']['edit']==['content','tool'] and set(invalid['action_fields'])==set(s.policy['allowed_tools']))
        for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
        for f in ('policy.json','fixtures/reference.sv','private/reward.json','verifier/v3/vip.sv'):
            checks.append(s.handle({'tool':'read','file':f})['status']=='REJECTED')
        edited=s.handle({'tool':'edit','content':(work/'bridge.sv').read_text()+'\n// accepted mechanism edit\n'})
        checks.append(edited['status']=='EDITED' and s.edits==1 and s.first_candidate is not None and not calls)
        obs=[]
        if mode=='spec_only':
            obs.append(s.handle({'tool':'test'}));checks.append(len(calls)==0)
        else:
            for _ in range(2):obs.append(s.handle({'tool':'test'}))
            denied=s.handle({'tool':'test'});checks.append(denied['status']=='REJECTED' and len(calls)==2)
            for item in obs:
                if mode=='test_verdict':checks.append(set(item)=={'status','remaining_test_calls'})
                else:checks.append(item['status']=='FAIL' and item['first_failed_case'] in ('write_pipeline',) and bool(item['diagnostic']))
        checks.append(s.handle({'tool':'submit'})['status']=='SUBMITTED')
        result=s.finalize();checks.append(result['reward']==0 and result['category']=='transaction_functional_error')
        checks.append(calls[-1]['cases_sha256']==sha(reward_path) and not calls[-1]['public'])
        builds.update(s.builds)
        runs[mode]={'public_test_calls':s.tests,'grader_invocations':calls,'observations':obs,'terminal_reward':result['reward'],
                    'terminal_category':result['category'],'source_sha256':sha(work/'bridge.sv')}
        (out/'progress.json').write_text(json.dumps(runs,indent=2))
    report={'action_protocol':protocol,'accepted':all(checks),'check_count':len(checks),'real_vcs':True,'agent_model_used':False,
            'private_reward_suite_sha256':sha(reward_path),'candidate':'fixtures/task004/bad_strobe.sv','runs':runs}
    (out/'result.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('reward');p.add_argument('--protocol',choices=PROTOCOLS,default=PROTOCOLS[0]);a=p.parse_args()
    raise SystemExit(0 if run(a.out,a.reward,a.protocol)['accepted'] else 1)
