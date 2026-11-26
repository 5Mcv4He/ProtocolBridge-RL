"""Trusted task catalog and CLI adapters; preserves task-specific verification contracts."""
import argparse,hashlib,importlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
FIELDS={'task_id','version','title','metadata','spec','initial_rtl','verifier','environment','quality_kind','capabilities','protocols','policies','reward_contract'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_catalog(path=None):
    data=json.loads(Path(path or ROOT/'tasks/registry.json').read_text())
    if set(data)!={'schema_version','tasks'} or data['schema_version']!=1:raise ValueError('Invalid catalog schema')
    result={}
    for t in data['tasks']:
        if set(t)!=FIELDS:raise ValueError('Unknown or missing task fields')
        name=t['task_id']
        if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]+',name) or name in result:raise ValueError('Invalid/duplicate task ID')
        if type(t['version']) is not int or t['version']<1:raise ValueError('Invalid task version')
        for k in ('metadata','spec','initial_rtl'):
            p=Path(t[k])
            if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe catalog path')
            try:(ROOT/p).resolve().relative_to((ROOT/'tasks'/name).resolve())
            except ValueError:raise ValueError('Path outside task package')
            if not (ROOT/p).is_file():raise ValueError('Missing task artifact')
        if t['spec']!='tasks/'+name+'/spec.md' or t['initial_rtl']!='tasks/'+name+'/workspace/bridge.sv':raise ValueError('Unsupported task artifact layout')
        if not re.fullmatch(r'verifier\.[a-zA-Z0-9_.]+',t['verifier']):raise ValueError('Invalid verifier module')
        if set(t['environment'])!={'reset','test','submit'}:raise ValueError('Missing environment interface')
        for a,m in t['environment'].items():
            if not re.fullmatch(r'environment\.[a-zA-Z0-9_]+:'+a,m):raise ValueError('Invalid environment binding')
        for k in ('capabilities','protocols','policies'):
            if not isinstance(t[k],list) or not t[k] or any(not isinstance(v,str) or not v for v in t[k]) or len(set(t[k]))!=len(t[k]):raise ValueError('Invalid task descriptors')
        if set(t['policies'])!={'spec_only','test_verdict','test_diagnostic'} or t['reward_contract']!='terminal_binary_with_infrastructure_null':raise ValueError('Unsupported policy/reward contract')
        if t['quality_kind']=='source_bound_gate':
            m=json.loads((ROOT/t['metadata']).read_text())
            if (m['task_id'],m['version'],m['verifier'])!=(name,t['version'],t['verifier']):raise ValueError('Task metadata mismatch')
            if m['capabilities']!=t['capabilities']:raise ValueError('Capability metadata mismatch')
        elif t['quality_kind']=='legacy_revision3':
            if name!='axil_to_apb4_001' or t['version']!=3:raise ValueError('Unknown legacy task')
        else:raise ValueError('Unknown quality contract')
        result[name]=t
    if not result:raise ValueError('Empty catalog')
    return result

def execute(action,task,work,out=None):
    work=Path(work)
    if action!='reset' and sha(work/'spec.md')!=sha(ROOT/task['spec']):raise ValueError('Workspace Spec does not match selected task')
    module,function=task['environment'][action].split(':')
    fn=getattr(importlib.import_module(module),function)
    return fn(work) if action=='reset' else fn(work,out)

def quality_command(task,out,resume=False):
    if task['quality_kind']=='legacy_revision3':
        if resume:raise ValueError('Legacy verifier does not support gate resume')
        return [sys.executable,'-m','environment.validate_v3',out]
    return [sys.executable,'-m','environment.task_quality','tasks/'+task['task_id'],out]+(['--resume'] if resume else [])
def rollout_command(task,extra):
    if extra[:1]==['--']:extra=extra[1:]
    if any(x=='--task' or x.startswith('--task=') for x in extra):raise ValueError('Task override is not permitted')
    return [sys.executable,'-m','environment.policy_experiment','--task',task['task_id']]+extra

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',help='Verified generated task capsule; separate source-bound admission');s=p.add_subparsers(dest='action');s.add_parser('list')
    q=s.add_parser('show');q.add_argument('task')
    for action in ('reset','test','submit'):
        q=s.add_parser(action);q.add_argument('task');q.add_argument('work')
        if action!='reset':q.add_argument('out')
    q=s.add_parser('quality');q.add_argument('task');q.add_argument('out');q.add_argument('--resume',action='store_true')
    q=s.add_parser('rollout');q.add_argument('task');q.add_argument('extra',nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.package:
        from task_families.package import verify
        package=Path(a.package).resolve();verify(package)
        extra=list(sys.argv[1:]);i=extra.index('--package') if '--package' in extra else next(i for i,v in enumerate(extra) if v.startswith('--package='))
        del extra[i:i+(2 if extra[i]=='--package' else 1)]
        raise SystemExit(subprocess.call([sys.executable,str(package/'scripts/tasks.py')]+extra,cwd=str(package)))
    catalog=load_catalog()
    if a.action=='list':print(json.dumps(list(catalog.values()),indent=2));return
    if not a.action:p.error('Choose an action')
    if a.task not in catalog:p.error('Unknown task ID')
    t=catalog[a.task]
    if a.action=='show':print(json.dumps(dict(t,spec_sha256=sha(ROOT/t['spec']),initial_rtl_sha256=sha(ROOT/t['initial_rtl'])),indent=2))
    elif a.action in ('quality','rollout'):
        cmd=quality_command(t,a.out,a.resume) if a.action=='quality' else rollout_command(t,a.extra)
        raise SystemExit(subprocess.call(cmd,cwd=str(ROOT)))
    else:print(json.dumps(execute(a.action,t,a.work,getattr(a,'out',None)),indent=2))
if __name__=='__main__':main()
