"""Actual standalone-grader/session qualification for a verified route/queue composition capsule.

This deterministic engineering acceptance uses VCS/VIP but no model API. It
complements installed-SDK mechanism evidence and per-instance control banks.
It is not an Agent rollout and never declares a task admitted by itself.
"""
import argparse,json,time,hashlib
from pathlib import Path
from environment.composed_backend_v1 import Backend
from environment.package_session import Session
from environment.artifact_task.session_v4 import save,sha
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['environment/'+n for n in ('composed_acceptance_v1.py','composed_backend_v1.py','composed_inputs_v1.py','composed_grade_entry_v1.py','package_session.py')]+['task_families/package.py','task_families/router_v3/toolchain.py']

def run(package,config,inputs,seeds,out):
    package=Path(package).resolve();out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    backend=Backend(package,sha(package/'family-manifest.json'),config,inputs,seeds)
    meta=backend.task;work=out/'work';work.mkdir()
    for name,src in [('spec.md',backend.taskdir/'spec.md'),('bridge.sv',backend.taskdir/'workspace/bridge.sv')]:
        (work/name).write_bytes(src.read_bytes())
    reference=package/meta['quality']['references'][0]
    freeze={'schema':'composed-standalone-acceptance-v1','package_manifest_sha256':backend.manifest_sha256,
            'config_sha256':backend.config_sha256,'input_sha256':backend.input_sha256,'input_seeds':seeds,
            'reference_sha256':sha(reference),'max_actions':20,'max_tests':2,'model_requests':0,
            'sources':{n:sha(ROOT/n) for n in SOURCES}}
    save(out/'freeze.json',freeze);checks=[];calls=[];start=time.monotonic()
    def check(name,condition,**detail):
        checks.append(dict(name=name,passed=bool(condition),**detail));save(out/'checks.json',checks)
        print(json.dumps(checks[-1]),flush=True)
        if not condition:raise RuntimeError('Acceptance failed: '+name)
    def grader(source,dest,phase):
        t=time.monotonic();r=backend.grade(source,dest,phase)
        calls.append({'source_sha256':sha(source),'phase':phase,'out':str(dest.relative_to(out)),
                      'reward':r['reward'],'category':r['category'],'wall_seconds':time.monotonic()-t})
        save(out/'grade-calls.json',calls);return r
    s=Session(meta,work,out/'session',grader,20,2)
    error=None
    try:
        for name in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':name})
        initial=s.handle({'tool':'test'})
        check('initial_functional_rejection',initial['status']=='FAIL' and calls[-1]['reward']==0,category=initial['category'])
        s.handle({'tool':'edit','content':reference.read_text()})
        public=s.handle({'tool':'test'})
        check('standalone_reference_public',public['status']=='PASS' and public['source_sha256']==sha(reference))
        check('old_feedback_identity',initial['source_sha256']!=public['source_sha256'] and s.trace[2]['observation']['source_sha256']==initial['source_sha256'])
        denied=s.handle({'tool':'test'})
        check('third_test_no_grading',denied.get('reason')=='test_budget_exhausted' and len(calls)==2)
        s.handle({'tool':'submit'});submitted=s.out/'submission/bridge.sv'
        solve_trace=json.loads(json.dumps(s.trace))
        check('submit_same_source',sha(submitted)==sha(reference))
        check('closed_after_submit',s.handle({'tool':'edit','content':'late'}).get('reason')=='episode_closed' and sha(submitted)==sha(reference))
        try:s.finalize(False)
        except ValueError:denied=True
        else:denied=False
        check('terminal_requires_stop',denied and len(calls)==2)
        terminal=s.finalize(True);save(out/'terminal.json',terminal)
        check('standalone_reference_terminal',terminal['reward']==1 and terminal['evaluation_role']=='terminal' and terminal['verification_complete'] is True)
        held=grader(submitted,out/'heldout','heldout');save(out/'heldout.json',held)
        check('standalone_reference_heldout',held['reward']==1 and held['evaluation_role']=='heldout' and held['verification_complete'] is True)
        check('private_results_not_in_feedback',s.trace==solve_trace and all(r['observation'].get('evaluation_role') is None for r in s.trace))
        invalid=out/'invalid.sv';invalid.write_text('module bridge; initial $finish; endmodule\n')
        r=grader(invalid,out/'invalid-result','public')
        check('source_policy_invalid',r['reward'] is None and r['category']=='invalid_submission' and not (out/'invalid-result/runtime.json').exists())
        broken=out/'compile-error.sv';broken.write_text(reference.read_text().replace('endmodule','this_is_not_valid_syntax !\nendmodule'))
        r=grader(broken,out/'compile-error-result','public')
        check('compile_error_is_not_infrastructure',r['reward']==0 and r['category']=='compile_error')
        # An unreachable environment entry fails before VCS; never alter licensing.
        badcfg=json.loads(Path(config).read_text());badcfg['eda_env_script']='/nonexistent/pb-acceptance-env.sh'
        cfg=out/'unavailable-environment.json';save(cfg,badcfg)
        bad=Backend(package,backend.manifest_sha256,cfg,inputs,seeds)
        r=bad.grade(reference,out/'infrastructure-result','public')
        check('infrastructure_is_not_rtl_failure',r['reward'] is None and r['category']=='infrastructure_error' and not (out/'infrastructure-result/compile.log').exists())
        check('grading_roles', [c['phase'] for c in calls[:4]]==['public','public','terminal','heldout'])
    except Exception as e:
        error=type(e).__name__+': '+str(e)[:180]
    result={'schema':'composed-standalone-acceptance-v1','passed':error is None,'error':error,'admitted':False,
            'checks':checks,'freeze_sha256':sha(out/'freeze.json'),'grade_calls':calls,'seconds':time.monotonic()-start,
            'scope':'One representative composed capsule: standalone source-policy, public/terminal/heldout dispatch, real candidate/session binding. No model and no new protocol qualification.'}
    save(out/'result.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('config');p.add_argument('input_plan');p.add_argument('out');a=p.parse_args()
    plan=json.loads(Path(a.input_plan).read_text());r=run(a.package,a.config,plan['inputs'],plan['seeds'],a.out)
    print(json.dumps({'passed':r['passed'],'error':r['error']}));raise SystemExit(0 if r['passed'] else 1)
