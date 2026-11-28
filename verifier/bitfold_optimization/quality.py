"""Function and mapping budget are independently necessary acceptance conditions."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,TASK,sha,LIMIT,LIBRARY_SHA256
from verification_resources.dependencies import local_import_closure

def dependencies():
 files=set(local_import_closure(ROOT,['verifier/bitfold_optimization/quality.py']))
 files.update('verifier/bitfold_synth/'+n for n in ('dc.tcl','proof.tcl','netlist.tcl'))
 files.add('tasks/bitfold_population_repair_v1/reference.sv')
 files.update(str(p.relative_to(ROOT)) for p in (ROOT/'tasks'/TASK).rglob('*') if p.is_file())
 return {f:sha(ROOT/f) for f in sorted(files)}
def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[];sources=dependencies();task=ROOT/'tasks'/TASK
 (out/'freeze.json').write_text(json.dumps(sources,indent=2)+'\n')
 def record(name,src,reward,category,phase='public',cells=None):
  r=grade(TASK,src,out/(name+'-'+phase),phase);ok=r['reward']==reward and r['category']==category
  if cells is not None:ok=ok and r.get('resource_measurement',{}).get('mapped_cell_count')==cells and r.get('library_sha256')==LIBRARY_SHA256
  checks.append({'control':name,'phase':phase,'expected_reward':reward,'expected_cells':cells,'accepted':ok,'result':r})
  (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(name,phase,r['category'],r.get('resource_measurement'),ok,flush=True)
  if r['category'].startswith('infrastructure'):raise RuntimeError('Stop on indeterminate environment')
 for name,cells in [('reference',22),('alternate',19)]:
  for phase in ('public','terminal','evaluation'):record(name,task/(name+'.sv'),1.,'pass',phase,cells)
 record('baseline',task/'workspace/bitfold.sv',0.,'synthesis_error',cells=33)
 record('serial_over_budget',task/'controls/serial_over_budget.sv',0.,'synthesis_error',cells=23)
 for name in ('constant','drop_bit','overflow'):record(name,task/'controls'/(name+'.sv'),0.,'transaction_mismatch')
 ref=(task/'reference.sv').read_text()
 for name,src,reward,cat in [('empty','',None,'invalid_submission'),('interface',ref.replace('[7:0] data','[6:0] data'),None,'invalid_submission'),('spoof',ref.replace('endmodule','initial $display("PB_CELLS=0");endmodule'),None,'invalid_submission'),('syntax',ref.replace('assign a=','assign a=;'),0.,'compile_error')]:
  f=out/(name+'.sv');f.write_text(src);record(name,f,reward,cat)
 if dependencies()!=sources:raise RuntimeError('Source changed during gate')
 result={'schema':'bitfold-cell-budget-quality-v1','accepted':len(checks)==15 and all(r['accepted'] for r in checks),'limit':LIMIT,'library_sha256':LIBRARY_SHA256,'checks':checks,'source_files':sources,'scope':'Fixed teaching-library mapping structure, not industrial PPA; all incorrect functions rejected before metric reward.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
