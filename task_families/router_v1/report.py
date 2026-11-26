"""Summarize a generated package's actual source-bound admission evidence.
No private vectors, deployment configuration or raw logs enter this projection.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from task_families.router_v1.generate import verify,sha

def numeric_cost(root):
 compile_logs=list(Path(root).rglob('compile.log'));simulation_logs=list(Path(root).rglob('simulation.log'))
 compiler=[];simulator=[]
 for path in compile_logs:
  matches=re.findall(r'CPU time:\s*([\d.]+) seconds to compile \+\s*([\d.]+) seconds to elab \+\s*([\d.]+) seconds to link',path.read_text(errors='replace'))
  if matches:compiler.append(sum(map(float,matches[-1])))
 for path in simulation_logs:
  matches=re.findall(r'CPU Time:\s*([\d.]+) seconds;\s*Data structure size:\s*([\d.]+)Mb',path.read_text(errors='replace'))
  if matches:simulator.append(tuple(map(float,matches[-1])))
 return {'compile_logs':len(compile_logs),'compile_cpu_footers':len(compiler),'compiler_cpu_seconds_measured':round(sum(compiler),3) if compiler else None,
         'simulation_logs':len(simulation_logs),'simulation_cpu_footers':len(simulator),'simulator_cpu_seconds_measured':round(sum(x[0] for x in simulator),3) if simulator else None,
         'maximum_reported_data_structure_Mb':max(x[1] for x in simulator) if simulator else None,
         'scope':'Only numeric vendor footers; CPU seconds are not wall time, missing footers are not zero cost, data structure size is not host peak RSS.'}

def report(package,gate,job=None):
 package=Path(package);gate=Path(gate);m=verify(package)
 frozen=json.loads((gate/'freeze.json').read_text())
 result=json.loads((gate/'result.json').read_text())
 if result.get('accepted') is not True:raise ValueError('Unaccepted gate cannot enter the admitted catalog')
 if result['task_id']!=m['task_id'] or frozen['task_id']!=m['task_id'] or result['freeze_sha256']!=sha(gate/'freeze.json'):raise ValueError('Gate identity mismatch')
 for name,h in frozen['files'].items():
  if m['files'].get(name)!=h:raise ValueError('Gate/package source mismatch')
 # Check the exact snapshot domain rather than accepting an arbitrary subset.
 task='tasks/'+m['task_id']+'/'
 expected={k:v for k,v in m['files'].items() if k.startswith(task) or k.split('/')[0] in ('environment','verifier','fixtures','tests')}
 if expected!=frozen['files']:raise ValueError('Incomplete gate source binding')
 controls={}
 for name,r in result['results'].items():
  controls[name]={k:r.get(k) for k in ('reward','category','verification_complete','failed_case','planned','checked','aborted','source_sha256','suite_sha256','functional_cross')}
 seconds=None
 if job:
  j=json.loads(Path(job).read_text())
  if j['status']!='finished' or j['exit_code']!=0:raise ValueError('Gate job did not complete successfully')
  seconds=j['ended']-j['started']
 return {'schema':'router-family-admission-v1','task_id':m['task_id'],'accepted':True,'package_manifest_sha256':sha(package/'family-manifest.json'),
         'reporter_sha256':sha(__file__),'numeric_eda_cost':numeric_cost(gate),'generator_sha256':m['generator_sha256'],'base_commit':m['source_commit'],'parameters':m['parameters'],
         'gate_result_sha256':sha(gate/'result.json'),'gate_freeze_sha256':sha(gate/'freeze.json'),
         'toolchain':frozen['toolchain'],'positive_count':result['positive_count'],'negative_count':result['negative_count'],
         'mechanism_checks':result['mechanism_checks'],'isolation_probe_accepted':result['isolation_probe_accepted'],
         'gate_wall_seconds':seconds,'compile_wall_seconds':None,'simulation_wall_seconds':None,
         'cost_scope':'Whole gate wall time when available; per-process EDA timing not instrumented by this gate',
         'controls':controls,'limitations':result['limitations']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('gate');p.add_argument('--job');p.add_argument('--out',required=True);a=p.parse_args()
 value=report(a.package,a.gate,a.job)
 with Path(a.out).open('x') as f:f.write(json.dumps(value,indent=2)+'\n')
