"""Real compiler and public-verifier acceptance; no model API calls."""
import argparse,json
from pathlib import Path
from environment.engineering_session import Session
from environment.engineering_tools import compile_rtl,inspect_public
from environment.policy import load
from environment.reset import ROOT
from verifier.task003.campaign import grade,sha
from verifier.task003.scenarios import suite

def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);checks={};calls=[]
 work=out/'work';work.mkdir()
 for name,src in [('spec.md',ROOT/'tasks/axil_to_apb4_queue_003/spec.md'),('bridge.sv',ROOT/'fixtures/task003/bad_early_credit.sv')]: (work/name).write_bytes(src.read_bytes())
 def counted(*a,**kw):calls.append(kw);return grade(*a,**kw)
 s=Session(load('test_diagnostic'),work,out/'session',suite(False,20261125),grader=counted)
 for f in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':f})
 for n in range(2):
  checks['public_fail_%d'%n]=s.handle({'tool':'test'})['status']=='FAIL'
  observation=s.handle({'tool':'inspect'})
  checks['capacity_diagnostic_%d'%n]=observation.get('invariant',{}).get('code')=='Q_CAPACITY'
  checks['compile_pass_%d'%n]=s.handle({'tool':'compile'})['status']=='PASS'
 for tool in ('test','inspect','compile'):checks[tool+'_budget_denied']=s.handle({'tool':tool})['status']=='REJECTED'
 checks['only_two_public_executions']=len(calls)==2
 checks['private_read_denied']=s.handle({'tool':'read','file':'private/reward.json'})['status']=='REJECTED'
 checks['arbitrary_arguments_denied']=s.handle({'tool':'compile','args':'private'})['status']=='REJECTED'
 checks['submission']=s.handle({'tool':'submit'})['status']=='SUBMITTED'
 checks['terminal_functional_fail']=s.finalize()['reward']==0
 controls={
  'reference':(ROOT/'fixtures/task003/reference.sv').read_text(),
  'syntax':'module bridge(input logic clk); assign a = ; endmodule',
  'width_truncation':'module bridge(input logic [31:0] a, output logic b); assign b=a; endmodule',
  'forbidden':'module bridge; initial $display("private"); endmodule'}
 expected={'reference':'PASS','syntax':'FAIL','width_truncation':'PASS','forbidden':'INVALID'}
 for name,code in controls.items():
  src=out/(name+'.sv');src.write_text(code)
  checks['compiler_'+name]=compile_rtl(src,out/name)['status']==expected[name]
 checks['null_is_environment']=inspect_public({'reward':None,'secret':'x'})=={'status':'ENV_ERROR','invariant':None}
 checks['source_kept']=sha(work/'bridge.sv')==sha(ROOT/'fixtures/task003/bad_early_credit.sv')
 result={'accepted':all(checks.values()),'checks':checks,'real_vcs':True,'model_used':False,
         'limits':['Compiler does not detect intentional width truncation; no complete lint claim.','Only existing public checker messages are queryable; no raw logs or vectors.']}
 (out/'result.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
