"""Check non-public orderings and the final shared session adapter with real tools."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha
from environment.artifact_task.session_v2 import Session

def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
 for fmt in ('8n1','8e1'):
  for phase in ('terminal','evaluation'):
   r=grade('uart_tx_'+fmt+'_v1',ROOT/'fixtures/uart_tx'/('reference_'+fmt+'.sv'),out/(fmt+'-'+phase),phase)
   checks.append({'task_id':'uart_tx_'+fmt+'_v1','phase':phase,'result':r,'accepted':r['reward']==1});print(fmt,phase,r['category'],flush=True)
   if r['reward'] is None:break
  if checks[-1]['result']['reward'] is None:break
 # The checker is real; a forbidden extra call must not start another tool job.
 from verifier.stimulus.campaign import grade as stim_grade
 task='x2p_stimulus_mapping_v1';work=out/'work';work.mkdir()
 for name,source in [('spec.md',ROOT/'tasks'/task/'spec.md'),('stimulus.json',ROOT/'fixtures/stimulus/good_mapping.json')]:
  (work/name).write_bytes(source.read_bytes())
 calls=[]
 def evaluator(p,o,phase):calls.append((phase,sha(p)));return stim_grade(task,p,o,phase)
 s=Session(json.loads((ROOT/'tasks'/task/'task.json').read_text()),work,out/'session',evaluator,max_actions=8,max_tests=1)
 for f in ('spec.md','stimulus.json'):s.handle({'tool':'read','file':f})
 first=s.handle({'tool':'test'});denied=s.handle({'tool':'test'});before=len(calls);s.handle({'tool':'submit'})
 terminal=s.finalize(True)
 checks.append({'control':'real_session_v2','accepted':first['status']=='PASS' and denied['reason']=='test_budget_exhausted' and before==1 and len(calls)==2 and terminal['reward']==1,'public_calls':before,'all_calls':len(calls),'terminal':terminal})
 result={'schema':'artifact-phase-acceptance-v1','accepted':len(checks)==5 and all(c['accepted'] for c in checks),'checks':checks,'session_sha256':sha(ROOT/'environment/artifact_task/session_v2.py'),'runner_sha256':sha(ROOT/'environment/artifact_task/runner_v2.py'),'script_sha256':sha(__file__)}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted'])
