"""Actual observational non-interference and bounded laboratory controls."""
import argparse,json
from pathlib import Path
from environment.runtime_tools import run,observation,ROOT,sha
from environment.runtime_session import Session,PROFILES
from environment.policy import load
from verifier.task003.campaign import grade
from verifier.task003.scenarios import suite

def acceptance(out,full=False):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);checks={};records={};reuse=None
 def check(name,value):
  checks[name]=bool(value);(out/'progress.json').write_text(json.dumps(checks,indent=2))
  if not value:raise RuntimeError('Acceptance failed: '+name)
 def invoke(name,source,request,previous=None):
  r=run(source,out/name,request,previous);records[name]=r
  check(name+'_decidable',r['status'] in ('PASS','FAIL'))
  print(json.dumps({'control':name,'status':r['status']}),flush=True)
  return r
 try:
  for case in (['write_fifo','read_fifo','partial_aw','round_robin','reset_7'] if full else ['write_fifo']):
   name='reference-'+case;r=invoke(name,ROOT/'fixtures/task003/reference.sv',{'scenario':case},reuse)
   reuse=str(out/name/'grade');check(name+'_pass',r['status']=='PASS')
   check(name+'_observed',len(r['timeline']['samples'])>0 and r['timeline']['first_error'] is None)
   check(name+'_credits',all(0<=x<=2 for row in r['timeline']['samples'] for x in row['unretired']))
  r=invoke('capacity',ROOT/'fixtures/task003/bad_early_credit.sv',{'scenario':'write_fifo'})
  check('capacity_failure',r['status']=='FAIL' and r['invariant']['code']=='Q_CAPACITY')
  check('observed_overflow',any(max(row['unretired'])>2 for row in r['timeline']['samples']))
  check('error_window',r['timeline']['first_error'] is not None)
  check('verdict_no_trace',observation(r,False)=={'status':'FAIL'})
  check('detailed_trace',bool(observation(r,True)['rows']))
  custom={'transactions':[[1,256,123,15,0,0,8,16,0,0],[0,256,0,0,0,0,2,8,0,0]]}
  r=invoke('custom',ROOT/'fixtures/task003/reference.sv',custom,reuse);check('custom_pass',r['status']=='PASS')
  if full:
   r=invoke('wrong-head',ROOT/'fixtures/task003/bad_wrong_aw_head.sv',{'scenario':'partial_aw'})
   check('wrong_head_failure',r['status']=='FAIL')
   ordinary=grade(ROOT/'fixtures/task003/reference.sv',out/'unobserved',public=True,cases=[c for c in suite(True,17) if c['name']=='write_fifo'])
   instrumented=json.loads((out/'reference-write_fifo/grade/result.json').read_text())
   check('unchanged_verdict_and_accounting',ordinary['cases']==instrumented['cases'])
  # Actual dispatcher: one successful custom invocation, remaining calls reuse build.
  work=out/'work';work.mkdir();(work/'bridge.sv').write_bytes((ROOT/'fixtures/task003/reference.sv').read_bytes());(work/'spec.md').write_text('Task003 Spec')
  s=Session(load('test_diagnostic'),work,out/'session',[],capability=PROFILES[1])
  calls_before=len(list((out/'session').glob('experiment-*')))
  check('pre_read_denied',s.handle({'tool':'experiment','scenario':'write_fifo'})['status']=='REJECTED')
  for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
  check('private_scenario_denied',s.handle({'tool':'experiment','scenario':'private'})['status']=='REJECTED')
  check('no_denied_execution',len(list((out/'session').glob('experiment-*')))==calls_before)
  s.lab_builds[sha(work/'bridge.sv')]=str(out/'custom/grade')
  for i in range(3):check('actual_session_%d'%i,s.handle(dict(custom,tool='experiment'))['status']=='PASS')
  check('fourth_denied',s.handle(dict(custom,tool='experiment'))['reason']=='experiment_budget_exhausted')
  check('actual_query',bool(s.handle({'tool':'observe','start':8,'count':4}).get('rows')))
  check('submit',s.handle({'tool':'submit'})['status']=='SUBMITTED')
  check('closed',s.handle(dict(custom,tool='experiment'))['reason']=='episode_closed')
  result={'accepted':all(checks.values()),'checks':checks,'full':full,'model_used':False,
          'controls':{n:{k:r.get(k) for k in ('status','source_sha256','observer_sha256','wall_seconds','verifier_result_sha256')} for n,r in records.items()}}
 except Exception as e:result={'accepted':False,'checks':checks,'error_type':type(e).__name__,'reason':str(e),'model_used':False}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--full',action='store_true');a=p.parse_args();r=acceptance(a.out,a.full);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
