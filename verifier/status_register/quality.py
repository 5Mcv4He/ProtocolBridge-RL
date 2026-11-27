"""Qualify the independent reference itself against a separate truth-table anchor."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha
from task_families.status_register_v1.generate import MODES,rtl,controls

def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
 def record(task,name,src,expected,phase='public',anchor=False,category=None):
  p=out/(task+'-'+name+'.sv');p.write_text(src)
  r=grade(task,p,out/(task+'-'+name+'-'+phase+('-anchor' if anchor else '-combined')),phase,anchor)
  accepted=r['reward']==expected and (category is None or r['category']==category)
  checks.append(dict(task_id=task,control=name,phase=phase,anchor_only=anchor,expected_reward=expected,accepted=accepted,result=r));(out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(task,name,phase,anchor,r['category'],accepted,flush=True)
  if r['category'].startswith('infrastructure'):raise RuntimeError('Stop on infrastructure issue; retain incomplete gate')
 for mode in MODES:
  task='status_'+mode+'_repair_v1'
  for alt in (False,True):
   for phase in ('public','terminal','evaluation'):record(task,'per-bit' if alt else 'bitwise',rtl(mode,alt),1.,phase)
  for name,src in controls(mode).items():
   record(task,name,src,0.)
   record(task,name,src,0.,anchor=True,category='transition_mismatch')
 task='status_set_dominant_repair_v1'
 record(task,'empty','',None,category='invalid_submission')
 record(task,'spoof',rtl('set_dominant').replace('endmodule','initial $display("PASS"); endmodule'),None,category='invalid_submission')
 record(task,'syntax',rtl('set_dominant').replace('status<=0;','status<=;'),0.,category='compile_error')
 paths=[ROOT/p for p in ['verifier/status_register/campaign.py','verifier/status_register/formal.py','verifier/status_register/oracle.py','verifier/status_register/proof.tcl','verifier/status_register/quality.py','task_families/status_register_v1/generate.py','verifier/independent_formal/campaign.py','verifier/uart_tx/campaign_v4.py','environment/remote_backend.py']]
 for mode in MODES:paths.extend(p for p in (ROOT/'tasks'/('status_'+mode+'_repair_v1')).rglob('*') if p.is_file())
 result=dict(schema='status-register-quality-v1',accepted=len(checks)==39 and all(c['accepted'] for c in checks),checks=checks,source_files={str(p.relative_to(ROOT)):sha(p) for p in paths},scope='Independent-reference Formality plus per-bit truth-table VCS; no PPA reward or arbitrary sequential completeness claim')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
