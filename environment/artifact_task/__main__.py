"""Finite engineering artifact tasks; old bridge entrypoints stay unchanged."""
import argparse,json,shutil
from pathlib import Path
from .dispatch_v7 import ROOT,TASKS,graders,catalog
from .session_v2 import sha,save

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 sub.add_parser('list')
 r=sub.add_parser('reset');r.add_argument('task',choices=TASKS);r.add_argument('work')
 for name in ('test','submit'):
  r=sub.add_parser(name);r.add_argument('task',choices=TASKS);r.add_argument('work');r.add_argument('out')
 a=p.parse_args()
 if a.command=='list':print((ROOT/'tasks/artifact-registry.json').read_text());return
 task=json.loads((ROOT/'tasks'/a.task/'task.json').read_text());work=Path(a.work)
 if a.command=='reset':
  work.mkdir(parents=True,exist_ok=False)
  for source in (ROOT/'tasks'/a.task/'spec.md',ROOT/'tasks'/a.task/'workspace'/task['deliverable']):shutil.copyfile(source,work/source.name)
  save(work/'task-identity.json',{'task_id':a.task,'task_sha256':sha(ROOT/'tasks'/a.task/'task.json'),'initial_sha256':sha(work/task['deliverable'])});return
 identity=json.loads((work/'task-identity.json').read_text())
 if identity['task_id']!=a.task or identity['task_sha256']!=sha(ROOT/'tasks'/a.task/'task.json'):raise ValueError('Task identity differs')
 grade,evaluate=graders(a.task);source=work/task['deliverable']
 if a.command=='test':r=grade(source,Path(a.out),'public')
 else:
  out=Path(a.out);out.mkdir(parents=True,exist_ok=False);f=out/task['deliverable'];f.write_bytes(source.read_bytes());f.chmod(0o444)
  r=grade(f,out/'terminal','terminal');save(out/'terminal.json',r)
  save(out/'reserved-evaluation.json',evaluate(f,out/'reserved-evaluation'))
  if sha(f)!=sha(source):raise ValueError('Source changed during manual submission')
 print(json.dumps(r,indent=2))
if __name__=='__main__':main()
