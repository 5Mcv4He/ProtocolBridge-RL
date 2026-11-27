"""Real VCS checks of both test allowances, version binding and terminal boundary."""
import argparse,hashlib,json
from pathlib import Path
from environment.engineering_lab import Session,extend_prompt
from environment.policy import load
from environment.batch_contract import experiment_prompt
from verifier.task003.campaign import grade
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out,private):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);checks={};calls=[];builds={}
    def check(name,value):
        checks[name]=bool(value);(out/'progress.json').write_text(json.dumps(checks,indent=2))
        if not value:raise RuntimeError(name)
    def actual(source,dest,**kw):
        calls.append({'source_sha256':sha(source),'public':bool(kw.get('public')),'destination':Path(dest).name})
        return grade(source,dest,**kw)
    try:
        prompts=[extend_prompt(experiment_prompt(load('test_diagnostic',b),True,'text-json-atomic-v2')) for b in (2,6)]
        check('only_budget_prompt_difference',prompts[0].replace('and 2 public test invocations','and 6 public test invocations')==prompts[1])
        for budget in (2,6):
            prefix='test%d_'%budget;work=out/(prefix+'work');work.mkdir()
            source=(ROOT/'fixtures/task003/bad_wrong_address.sv').read_bytes()
            (work/'bridge.sv').write_bytes(source);(work/'spec.md').write_bytes((ROOT/'tasks/x2p_queue_three_v1/spec.md').read_bytes())
            s=Session(load('test_diagnostic',budget),work,out/(prefix+'session'),json.loads(Path(private).read_text()),grader=actual,reuse=builds)
            for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
            start=len(calls)
            for n in range(budget):
                o=s.handle({'tool':'test'})
                check(prefix+'test_%d_actual_fail'%(n+1),o['status']=='FAIL' and o['remaining_test_calls']==budget-n-1 and len(calls)==start+n+1 and calls[-1]['source_sha256']==sha(work/'bridge.sv') and o['candidate_binding']['is_current'])
            before=len(calls);o=s.handle({'tool':'test'})
            check(prefix+'overflow_no_backend',o.get('reason')=='test_budget_exhausted' and len(calls)==before)
            s.handle({'tool':'edit','content':source.decode()+'\n// acceptance revision\n'})
            check(prefix+'old_feedback_identity',s.handle({'tool':'inspect'})['candidate_binding']['is_current'] is False)
            s.handle({'tool':'submit'});submitted=sha(out/(prefix+'session/submission/bridge.sv'))
            check(prefix+'submit_no_private_run',len(calls)==before and s.submitted)
            check(prefix+'closed',s.handle({'tool':'edit','content':'invalid'})['reason']=='episode_closed' and sha(out/(prefix+'session/submission/bridge.sv'))==submitted)
            result=s.finalize();check(prefix+'terminal_actual_failure',result['reward']==0 and len(calls)==before+1 and not calls[-1]['public'])
            builds.update(s.builds)
            # No simulator needed for rejected actions, but use the same real dispatcher.
            t=Session(load('test_diagnostic',budget),work,out/(prefix+'limit'),[],grader=actual)
            for i in range(20):t.handle({'tool':'unknown'})
            before=len(calls)
            check(prefix+'total_20',t.actions==20 and t.handle({'tool':'test'})['reason']=='episode_closed' and len(calls)==before)
        result={'version':'verification-budget-v1','accepted':True,'checks':checks,'actual_verifier_calls':calls,'model_used':False}
    except Exception as e:result={'version':'verification-budget-v1','accepted':False,'checks':checks,'error_type':type(e).__name__,'reason':str(e),'actual_verifier_calls':calls,'model_used':False}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('private');a=p.parse_args();r=run(a.out,a.private);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
