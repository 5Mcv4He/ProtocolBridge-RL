"""Negative replay checks on private copies of a real, completed episode."""
import argparse,json,shutil,tempfile
from pathlib import Path
from scripts.artifact_exchange_v5 import audit
from environment.artifact_task.session import save,sha

def run(source):
 source=Path(source);assert audit(source)['accepted'];rows=[]
 for name in ('extra_feedback_field','wrong_delivered_feedback','changed_submission','unconfirmed_stop_with_evaluation','changed_terminal_reward'):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'episode';shutil.copytree(source,p)
   if name=='extra_feedback_field':
    f=p/'session/trace.json';d=json.loads(f.read_text());d[0]['observation']['sensitive_canary']='not-allowed';save(f,d)
   elif name=='wrong_delivered_feedback':
    f=p/'requests.json';d=json.loads(f.read_text());d[1]['input']['prompt']='{"tool_result":{"status":"PASS"}}';save(f,d)
   elif name=='changed_terminal_reward':
    f=p/'result.json';d=json.loads(f.read_text());d['terminal']['reward']=1 if d['terminal']['reward']!=1 else 0;save(f,d)
   elif name=='unconfirmed_stop_with_evaluation':
    f=p/'result.json';d=json.loads(f.read_text());d['solver_stop_confirmed']=False;save(f,d)
   else:
    files=list((p/'session/submission').glob('*'))
    if len(files)!=1:raise ValueError('A submitted episode is required')
    files[0].chmod(0o644);files[0].write_text('changed source')
   try:audit(p);accepted=False;reason='not_rejected'
   except ValueError as e:accepted=True;reason=str(e)
   rows.append({'injection':name,'rejected':accepted,'reason':reason})
 return {'schema':'artifact-audit-negative-v6','accepted':all(r['rejected'] for r in rows),'source_trace_sha256':sha(source/'session/trace.json'),'checks':rows,'scope':'Mutated private copies only; original raw episode unchanged; no model or simulator invocation.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');a=p.parse_args();r=run(a.source);save(Path(a.out),r);print(r['accepted'])
