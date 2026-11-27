"""Real positive/negative controls and independent reference-semantic anchors."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha
from .anchor import run as anchor

def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);rows=[]
 controls=[('wrap','legal_wrap',1.),('saturating','legal_saturating',1.),('wrap','reference_wrap',1.),('saturating','reference_saturating',1.)]
 controls += [('wrap',name,0.) for name in ('bad_reset','bad_enable','bad_clock_edge','bad_async_reset','bad_hold')]
 controls += [('wrap','initial',0.),('saturating','initial',0.)]
 for kind,name,expected in controls:
  task='accumulator_'+kind+'_repair_v1'
  source=ROOT/'tasks'/task/'workspace/accumulator.sv' if name=='initial' else ROOT/'fixtures/independent_formal'/(name+'.sv')
  result=grade(task,source,out/(kind+'-'+name));rows.append({'task':task,'control':name,'expected_reward':expected,'result':result,'accepted':result['reward']==expected})
  (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(kind,name,result['category'],flush=True)
 for kind in ('wrap','saturating'):
  r=anchor('accumulator_'+kind+'_repair_v1',ROOT/'fixtures/independent_formal'/('reference_'+kind+'.sv'),out/('anchor-'+kind));rows.append({'task':kind,'control':'independent_integer_anchor','result':r,'accepted':r['accepted']})
 # A missing/empty deliverable is not an equivalent circuit or a functional loss.
 empty=out/'empty.sv';empty.write_text('')
 r=grade('accumulator_wrap_repair_v1',empty,out/'empty-grade');rows.append({'control':'empty_submission','result':r,'accepted':r['reward'] is None and r['category']=='invalid_submission'})
 syntax=out/'syntax.sv';syntax.write_text('module accumulator(input logic clk,output logic q); always_ff @(posedge clk) q<=; endmodule\n')
 r=grade('accumulator_wrap_repair_v1',syntax,out/'syntax-grade');rows.append({'control':'syntax_error','result':r,'accepted':r['reward']==0 and r['category']=='compile_error'})
 files=[p for d in ('verifier/independent_formal','fixtures/independent_formal','tasks/accumulator_wrap_repair_v1','tasks/accumulator_saturating_repair_v1') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 result={'schema':'independent-reference-quality-v1','accepted':all(x['accepted'] for x in rows),'checks':rows,'source_files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},'scope':'Bounded 8-bit synchronous task contract; independent RTL equivalence plus exhaustive finite transition anchors. No PPA claim.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
