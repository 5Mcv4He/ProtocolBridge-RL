"""Add register-checker production with required dependency closure, not copies of the repository."""
import argparse,json,shutil
from pathlib import Path
from .production_v5 import ROOT,qualified as previous_qualified
from .dependencies import local_import_closure
from environment.artifact_task.session_v4 import sha,save
FAMILY='register-checker'
SCHEMA='finite-engineering-materialization-v9'
def qualified(family,variant):
    if family!=FAMILY:return previous_qualified(family,variant)
    if variant not in ('rw','w1c'):raise ValueError('Unsupported contract')
    from task_families.register_checker_v1.qualification import check,GATE
    task='register_checker_'+variant+'_v1';check(ROOT/'tasks'/task)
    gate=json.loads((ROOT/GATE).read_text())
    entries=['environment/native_tools/run_v4.py','environment/native_tools/worker_v3.py','environment/native_tools/tools_v3.mjs','environment/native_tools/launch_v3.sh','environment/artifact_task/cli_v2.py','verification_resources/production_v6.py']
    required=set(gate['source_files'])|set(local_import_closure(ROOT,entries))|{GATE}
    deps={f:sha(ROOT/f) for f in sorted(required)}
    files={'task/'+str(p.relative_to(ROOT/'tasks'/task)):sha(p) for p in sorted((ROOT/'tasks'/task).rglob('*')) if p.is_file()}
    return task,deps,files

def check(package):
    package=Path(package)
    if any(p.is_symlink() for p in package.rglob('*')):raise ValueError('Symlink package')
    m=json.loads((package/'manifest.json').read_text())
    if m['schema']!=SCHEMA or m['family']!=FAMILY:raise ValueError('Unsupported materialization')
    task,deps,files=qualified(m['family'],m['variant'])
    if m['task_id']!=task or m['source_dependencies']!=deps or m['files']!=files or m['producer_sha256']!=sha(__file__):raise ValueError('Missing or changed required materialization dependency')
    actual={str(p.relative_to(package)):sha(p) for p in package.rglob('*') if p.is_file() and p!=package/'manifest.json'}
    if actual!=files:raise ValueError('Materialized task differs')
    return {'task_id':task,'accepted':True,'source_dependency_count':len(deps),'task_file_count':len(files)}

def materialize(variant,out):
    task,deps,files=qualified(FAMILY,variant);out=Path(out);out.mkdir(parents=True,exist_ok=False);shutil.copytree(ROOT/'tasks'/task,out/'task')
    save(out/'manifest.json',dict(schema=SCHEMA,family=FAMILY,variant=variant,task_id=task,producer_sha256=sha(__file__),runtime='environment.native_tools.run_v4',source_dependencies=deps,files=files))
    return check(out)
if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);a=sub.add_parser('materialize');a.add_argument('variant',choices=['rw','w1c']);a.add_argument('out');a=sub.add_parser('check');a.add_argument('package');a=p.parse_args();print(json.dumps(materialize(a.variant,a.out) if a.command=='materialize' else check(a.package),indent=2))
