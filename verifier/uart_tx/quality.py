"""Targeted serial framing/latency controls for both finite UART contracts."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha

def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);rows=[]
 for fmt in ('8n1','8e1'):
  task='uart_tx_'+fmt+'_v1';ref=ROOT/'fixtures/uart_tx'/('reference_'+fmt+'.sv');s=ref.read_text()
  controls=[('reference',s,1),('initial',(ROOT/'tasks'/task/'workspace/uart_tx.sv').read_text(),0),('short_bit',s.replace('tick==15','tick==14'),0),('wrong_start',s.replace("data,1'b0","data,1'b1"),0),('early_ready',s.replace('remaining==0','remaining<=1'),0),('data_invert',s.replace('data,1\'b0','~data,1\'b0'),0)]
  if fmt=='8e1':controls.append(('parity_invert',s.replace('^data','~^data'),0))
  for name,src,expected in controls:
   p=out/(fmt+'-'+name+'.sv');p.write_text(src);r=grade(task,p,out/(fmt+'-'+name));rows.append({'task_id':task,'control':name,'expected_reward':expected,'result':r,'accepted':r['reward']==expected})
   (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(fmt,name,r['category'],flush=True)
   if r['reward'] is None:break
  if rows[-1]['result']['reward'] is None:break
 files=[p for d in ('verifier/uart_tx','fixtures/uart_tx','tasks/uart_tx_8n1_v1','tasks/uart_tx_8e1_v1') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 r={'schema':'finite-uart-quality-v1','accepted':len(rows)==13 and all(x['accepted'] for x in rows),'checks':rows,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}}
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted'])
