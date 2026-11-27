"""Score structured test stimulus against fixed designs and the v3 UVM oracle.

The Agent supplies only bounded integer transactions, never checks or executable
code. A functional/protocol rejection counts; timeout/compile failure never does.
"""
import argparse,hashlib,json,os,time
from pathlib import Path
from verifier.campaign import grade as bridge_grade,ROOT,sha
from environment.control_bank import bundle
TASKS={'x2p_stimulus_mapping_v1':{'public':['bad_address'],'terminal':['bad_strobe','bad_read_data'],'evaluation':['heldout_strobe']},
       'x2p_stimulus_timing_v1':{'public':['bad_wait'],'terminal':['bad_error','bad_backpressure'],'evaluation':['bad_early_read']}}
CONTROLS=['reference','bad_address','bad_strobe','bad_read_data','bad_wait','bad_error','bad_backpressure','bad_early_read','heldout_strobe']
FUNCTIONAL={'transaction_functional_error','protocol_timing_error'}

def parse(text):
 def unique(pairs):
  d={}
  for k,v in pairs:
   if k in d:raise ValueError('Duplicate field')
   d[k]=v
  return d
 data=json.loads(text,object_pairs_hook=unique)
 if not isinstance(data,dict) or set(data)!={'transactions'}:raise ValueError('Expected transactions only')
 rows=data['transactions']
 if not isinstance(rows,list) or not 1<=len(rows)<=32:raise ValueError('Requires 1 to 32 transactions')
 for r in rows:
  if not isinstance(r,list) or len(r)!=9 or any(type(x)!=int for x in r):raise ValueError('Nine integer fields required')
  if not (r[0] in (0,1) and 0<=r[1]<2**32 and r[1]%4==0 and 0<=r[2]<2**32 and 0<=r[3]<16 and all(0<=x<=16 for x in r[4:8]) and r[8] in (0,1)):raise ValueError('Field outside contract')
  if r[0]==0 and (r[3]!=0 or r[4]!=0 or r[5]!=0):raise ValueError('Read must use zero strobe and write-channel delays')
 return rows

def paths():
 return [ROOT/'fixtures/stimulus/heldout_strobe.sv' if n=='heldout_strobe' else ROOT/'fixtures'/(n+'.sv') for n in CONTROLS]

def grade(task,source,out,phase='public'):
 if task not in TASKS or phase not in TASKS[task]:raise ValueError('Unknown stimulus task/phase')
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source);start=time.monotonic()
 result={'task_id':task,'source_sha256':sha(source),'reward':None,'category':'infrastructure_error','phase':phase,'verification_complete':False,'controls':[],'grader_sha256':sha(__file__)}
 old=os.environ.get('PB_CONFIG')
 try:
  try:rows=parse(source.read_text())
  except (ValueError,TypeError):result['category']='invalid_submission';return result
  case={'name':'agent_plan','sequence':'mixed_random_sequence','requirements':['AGENT_STIMULUS_VALIDITY'],'ready_mode':'reactive','rows':[r+[0,0] for r in rows]}
  cfg=json.loads(Path(old or ROOT/'.local/config.json').read_text())
  bank=Path(os.environ.get('PB_STIMULUS_CACHE',ROOT/'.local/stimulus-control-bank-v1')).resolve();bank.mkdir(parents=True,exist_ok=True)
  sources=paths();body=bundle(sources)
  fingerprint=hashlib.sha256(json.dumps({'bundle':hashlib.sha256(body.encode()).hexdigest(),'verifier':{p.name:sha(p) for p in (ROOT/'verifier/v3').glob('*.sv')},'campaign':sha(ROOT/'verifier/campaign.py'),'environment':cfg},sort_keys=True).encode()).hexdigest()
  cache=bank/fingerprint;cache.mkdir(exist_ok=True);bank_source=cache/'bridge.sv'
  if bank_source.exists() and bank_source.read_text()!=body:raise RuntimeError('Bank mismatch')
  bank_source.write_text(body);seed=cache/'compiled';reuse=seed if (seed/'backend.json').exists() else None
  result['control_bank_sha256']=sha(bank_source);result['suite_sha256']=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
  for name in ['reference']+TASKS[task][phase]:
   local_cfg=dict(cfg,variant=CONTROLS.index(name));cfgfile=out/'deployment.json';cfgfile.write_text(json.dumps(local_cfg));os.environ['PB_CONFIG']=str(cfgfile)
   dest=out/name
   r=bridge_grade(bank_source,dest,cases=[case],reuse_build=reuse,trusted_controls=True)
   if reuse is None and (dest/'backend.json').exists():
    seed.mkdir(exist_ok=True);(seed/'backend.json').write_bytes((dest/'backend.json').read_bytes());reuse=seed
   summary={k:r.get(k) for k in ('reward','category','verification_complete','planned','checked','compile_exit','compile_reused')}
   summary['control']=name;summary['result_sha256']=sha(dest/'result.json');result['controls'].append(summary)
   if name=='reference':
    if r['reward']!=1:result.update(reason='Legal control failed; do not reward test or blame DUT');return result
    observed=r['cases'][0];result['actual_activity']={'checked':r['checked'],'coverage':observed['coverage'],'cross_bins':observed['cross_bins']}
    covers=observed['coverage'];writes=sum(x[0] for x in rows);reads=len(rows)-writes
    necessary=writes>0 and reads>0 and r['checked']==len(rows)
    if task.endswith('timing_v1'):necessary=necessary and covers['waits']>0 and covers['stalls']>0 and covers['aw_first']>0 and covers['w_first']>0
    if not necessary:result.update(reward=0.,category='missing_activity');return result
   elif r['reward'] is None or r['category']=='compile_error':return result
   elif not (r['reward']==0 and r['category'] in FUNCTIONAL):
    result.update(reward=0.,category='insufficient_detection');return result
  result.update(reward=1.,category='pass',verification_complete=True)
 except Exception as e:result['exception_type']=type(e).__name__
 finally:
  if old is None:os.environ.pop('PB_CONFIG',None)
  else:os.environ['PB_CONFIG']=old
  result['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase),indent=2))
