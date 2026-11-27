import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha,paths

def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
 for kind in ('mapping','timing'):
  task='x2p_stimulus_'+kind+'_v1'
  for name,phase,expect in [('good_'+kind,'public',1),('good_'+kind,'terminal',1),('good_'+kind,'evaluation',1),('weak','terminal',0),('empty','public',None)]:
   r=grade(task,ROOT/'fixtures/stimulus'/(name+'.json'),out/(kind+'-'+name+'-'+phase),phase)
   accepted=r['reward']==expect and (expect is not None or r['category']=='invalid_submission')
   checks.append({'task_id':task,'control':name,'phase':phase,'expected_reward':expect,'result':r,'accepted':accepted})
   (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(kind,name,phase,r['category'],flush=True)
   if not accepted:break
  if not checks[-1]['accepted']:break
 files=paths()+[p for d in ('verifier/stimulus','verifier/v3','fixtures/stimulus','tasks/x2p_stimulus_mapping_v1','tasks/x2p_stimulus_timing_v1') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]+[ROOT/'verifier/campaign.py',ROOT/'environment/control_bank.py']
 r={'schema':'structured-stimulus-quality-v1','accepted':len(checks)==10 and all(c['accepted'] for c in checks),'checks':checks,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))}}
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted'])
