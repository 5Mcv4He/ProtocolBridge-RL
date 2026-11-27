"""Revision-2 admission: full controls, adjacent/busy activity and direct candidates."""
import argparse,json
from pathlib import Path
from .campaign_v2 import grade,ROOT,sha

def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);controls=[];checks=[]
 for fmt in ('8n1','8e1'):
  task='uart_tx_'+fmt+'_v1';s=(ROOT/'fixtures/uart_tx'/('reference_'+fmt+'.sv')).read_text()
  for name,src,expected in [('reference',s,1),('initial',(ROOT/'tasks'/task/'workspace/uart_tx.sv').read_text(),0),('short_bit',s.replace('tick==15','tick==14'),0),('wrong_start',s.replace("data,1'b0","data,1'b1"),0),('early_ready',s.replace('remaining==0','remaining<=1'),0),('data_invert',s.replace('data,1\'b0','~data,1\'b0'),0),('busy_accept',s.replace('else if (ready)','else if (ready || valid)'),0)]+([('parity_invert',s.replace('^data','~^data'),0)] if fmt=='8e1' else []):
   controls.append((fmt,name,src,expected))
 bank='module uart_tx(input logic clk,rst_n,valid,input logic [7:0] data, output wire ready,tx);\ninteger choice; initial if(!$value$plusargs("variant=%d",choice))choice=0;\n'
 for i,(_,_,_,_) in enumerate(controls):bank+='wire r%d,t%d;uart_variant_%d d%d(clk,rst_n,valid,data,r%d,t%d);\n'%(i,i,i,i,i,i)
 bank+='assign ready='+''.join('(choice==%d)?r%d:'%(i,i) for i in range(len(controls)))+"1'bx;\nassign tx="+''.join('(choice==%d)?t%d:'%(i,i) for i in range(len(controls)))+"1'bx;\nendmodule\n"
 bank+='\n'.join(s.replace('module uart_tx(','module uart_variant_%d('%i,1) for i,(_,_,s,_) in enumerate(controls))
 source=out/'control-bank.sv';source.write_text(bank);reuse=None
 def add(task,name,phase,r,expected):
  checks.append({'task_id':task,'control':name,'phase':phase,'expected_reward':expected,'result':r,'accepted':r['reward']==expected and (expected is not None or r['category']=='invalid_submission')})
  (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(task,name,phase,r['category'],flush=True)
 for i,(fmt,name,_,expected) in enumerate(controls):
  task='uart_tx_'+fmt+'_v1';dest=out/(fmt+'-'+name);r=grade(task,source,dest,trusted_controls=True,selection=i,reuse_build=reuse)
  if (dest/'backend.json').exists() and reuse is None:reuse=dest
  add(task,name,'public',r,expected)
  if r['reward'] is None:break
 if len(checks)==len(controls) and all(x['accepted'] for x in checks):
  for fmt in ('8n1','8e1'):
   task='uart_tx_'+fmt+'_v1'
   # Standalone positives also check the ordinary candidate compilation path.
   r=grade(task,ROOT/'fixtures/uart_tx'/('reference_'+fmt+'.sv'),out/(fmt+'-standalone'));add(task,'standalone_reference','public',r,1)
   i=next(i for i,c in enumerate(controls) if c[0]==fmt and c[1]=='reference')
   for phase in ('terminal','evaluation'):
    r=grade(task,source,out/(fmt+'-'+phase),phase,trusted_controls=True,selection=i,reuse_build=reuse);add(task,'reference',phase,r,1)
  r=grade('uart_tx_8n1_v1',source,out/'untrusted-bank');add('uart_tx_8n1_v1','untrusted_bank','public',r,None)
 files=[p for d in ('verifier/uart_tx','fixtures/uart_tx','tasks/uart_tx_8n1_v1','tasks/uart_tx_8e1_v1') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 result={'schema':'finite-uart-quality-v2','accepted':len(checks)==22 and all(x['accepted'] for x in checks),'checks':checks,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},'required_activity':{'frames':256,'busy_offers_8n1':5888,'busy_offers_8e1':6400,'adjacent_frame_acceptances':255},'reuse_scope':'One trusted control bank compiled on the current host for identical source, testbench, grader and configuration hashes. Ordinary Agent candidates cannot request reuse or select controls.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted'])
