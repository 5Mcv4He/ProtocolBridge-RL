"""Materialize one of six reviewed finite contracts with exact source dependencies.

This is a bounded template producer, not a protocol synthesizer. Runtime and
trusted checkers are shared through a verified source dependency manifest.
"""
import argparse,json,shutil
from pathlib import Path
from environment.artifact_task.dispatch import ROOT
from environment.artifact_task.session import sha,save
FAMILIES={
 'reference-repair':{'wrap':'accumulator_wrap_repair_v1','saturating':'accumulator_saturating_repair_v1'},
 'uart-transmit':{'8n1':'uart_tx_8n1_v1','8e1':'uart_tx_8e1_v1'},
 'stimulus-design':{'mapping':'x2p_stimulus_mapping_v1','timing':'x2p_stimulus_timing_v1'}}
GATES={'reference-repair':'independent-reference-quality.json','uart-transmit':'uart-quality-v2.json','stimulus-design':'stimulus-quality.json'}

def materialize(family,variant,out):
 if family not in FAMILIES or variant not in FAMILIES[family]:raise ValueError('Unsupported engineering contract')
 task=FAMILIES[family][variant];gatefile=ROOT/'experiments/verification-resources-v1'/GATES[family];gate=json.loads(gatefile.read_text())
 if not gate['accepted'] or any(sha(ROOT/p)!=h for p,h in gate['source_files'].items()):raise ValueError('Quality evidence no longer matches')
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 shutil.copytree(ROOT/'tasks'/task,out/'task')
 common=[ROOT/'environment/artifact_task'/n for n in ('session_v2.py','runner_v3.py','dispatch_v2.py','dispatch.py','__main__.py')]
 common += [ROOT/p for p in ('environment/policy.py','environment/remote_backend.py','environment/utm_worker.py','environment/utm_sandbox.sh','verifier/independent_formal/campaign.py')]
 deps=dict(gate['source_files']);deps.update({str(p.relative_to(ROOT)):sha(p) for p in common});deps[str(gatefile.relative_to(ROOT))]=sha(gatefile)
 manifest={'schema':'finite-engineering-materialization-v2','family':family,'variant':variant,'task_id':task,'producer_sha256':sha(__file__),'verifier_revision':2 if family=='uart-transmit' else 1,
  'source_dependencies':deps,'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
  'runtime':'Use a checkout satisfying source_dependencies; no compiled artifacts or commercial source is included.',
  'status':'Task checker qualified; this materialization is not a new independent engineering capability or a new model trial.'}
 save(out/'manifest.json',manifest);return manifest

def check(package):
 package=Path(package);m=json.loads((package/'manifest.json').read_text())
 if m['family'] not in FAMILIES or FAMILIES[m['family']].get(m['variant'])!=m['task_id']:raise ValueError('Identity mismatch')
 if m['family']=='uart-transmit' and m.get('verifier_revision',1)!=2:raise ValueError('UART verifier 1 admission superseded after confirmed busy-offer blindspot')
 if m['schema']!='finite-engineering-materialization-v2':raise ValueError('Use the producer version bound to this historical package')
 taskroot=ROOT/'tasks'/m['task_id']
 expected={'task/'+str(p.relative_to(taskroot)):sha(p) for p in taskroot.rglob('*') if p.is_file()}
 if m['files']!=expected:raise ValueError('Package differs from the qualified task contract')
 gatefile=ROOT/'experiments/verification-resources-v1'/GATES[m['family']];gate=json.loads(gatefile.read_text())
 if not gate['accepted'] or any(m['source_dependencies'].get(p)!=h for p,h in gate['source_files'].items()):raise ValueError('Missing qualified dependencies')
 if m['source_dependencies'].get(str(gatefile.relative_to(ROOT)))!=sha(gatefile):raise ValueError('Wrong active admission evidence')
 for name,h in m['files'].items():
  p=(package/name).resolve()
  if not p.is_relative_to(package.resolve()) or sha(p)!=h:raise ValueError('Materialized file differs')
 for name,h in m['source_dependencies'].items():
  p=(ROOT/name).resolve()
  if not p.is_relative_to(ROOT) or sha(p)!=h:raise ValueError('Runtime dependency differs')
 return m

def reset(package,work):
 m=check(package);package=Path(package);task=json.loads((package/'task/task.json').read_text());work=Path(work);work.mkdir(parents=True,exist_ok=False)
 for p in (package/'task/spec.md',package/'task/workspace'/task['deliverable']):shutil.copyfile(p,work/p.name)
 save(work/'task-identity.json',{'task_id':m['task_id'],'task_sha256':sha(package/'task/task.json'),'initial_sha256':sha(work/task['deliverable']),'materialization_sha256':sha(package/'manifest.json')})
 return {'task_id':m['task_id'],'initialized':True}

if __name__=='__main__':
 p=argparse.ArgumentParser();subs=p.add_subparsers(dest='command',required=True)
 a=subs.add_parser('produce');a.add_argument('family',choices=FAMILIES);a.add_argument('variant');a.add_argument('out')
 a=subs.add_parser('check');a.add_argument('package')
 a=subs.add_parser('reset');a.add_argument('package');a.add_argument('work');args=p.parse_args()
 r=materialize(args.family,args.variant,args.out) if args.command=='produce' else check(args.package) if args.command=='check' else reset(args.package,args.work)
 print(json.dumps(r,indent=2))
