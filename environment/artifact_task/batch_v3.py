"""Bounded sequential artifact sampling with immutable completed episodes.

A batch is an execution envelope, not a training algorithm. A started incomplete
trial is retained for investigation; resume never silently replaces it.
"""
import argparse,fcntl,json,os,shlex,subprocess
from pathlib import Path
from .runner_v11 import run,unchanged
from .session_v4 import save
from environment.remote_backend import remote_command

def usage(base):
    base=Path(base);started=0;tokens=0
    for directory in base.iterdir() if base.exists() else []:
        if not directory.is_dir() or not (directory/'freeze.json').is_file():continue
        started+=1
        for p in directory.glob('harness-*.json'):
            response=json.loads(p.read_text()).get('response',{})
            for e in response.get('events',[]):
                if e.get('type')=='assistant/message':tokens+=(e['data'].get('usage') or {}).get('totalTokens',0)
    return dict(started=started,tokens=tokens)

def resource_probe(config):
    # Read-only readiness; no license configuration or daemon operations.
    c=json.loads(Path(config).read_text())
    program='''import json,os
from pathlib import Path
v=os.statvfs(os.environ['PB_RESOURCE_PATH'])
m={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()}
names=[]
for p in Path('/proc').glob('[0-9]*/comm'):
 try:names.append(p.read_text().strip())
 except OSError:pass
active=sum(n in ('vcs','vcs1','vlogan','simv','dc_shell','fm_shell','pt_shell') for n in names)
print(json.dumps({'active_eda_processes':active,'free_disk_bytes':v.f_bavail*v.f_frsize,'available_memory_bytes':m.get('MemAvailable',0)*1024,'load_1m':os.getloadavg()[0]}))'''
    command='PB_RESOURCE_PATH='+shlex.quote(c['remote_root'])+' python3 -c '+shlex.quote(program)
    r=subprocess.run(['ssh','-F',c['ssh_config'],c['host'],remote_command(c,command)],capture_output=True,text=True,timeout=30,check=True)
    return json.loads(r.stdout)

def _batch(planfile,base,config):
    os.environ['PB_CONFIG']=str(Path(config).resolve())
    planfile=Path(planfile);p=json.loads(planfile.read_text());base=Path(base);base.mkdir(parents=True,exist_ok=True)
    ids=[r['trial_id'] for r in p['trials']]
    if len(ids)!=len(set(ids)) or any(not i or '/' in i or '..' in i for i in ids):raise ValueError('Invalid or duplicate trial identity')
    cap=p['resource_envelope']
    if not 0<len(ids)<=cap['max_started_trials']<=24 or not 0<cap['reported_token_stop']<=750000:raise ValueError('Unbounded study')
    if not unchanged(p):raise ValueError('Frozen source differs')
    progress=[]
    for row in p['trials']:
        out=base/row['trial_id']
        if (out/'result.json').exists():
            result=json.loads((out/'result.json').read_text())
            from .session_v4 import sha
            if result['trial_id']!=row['trial_id'] or result['plan_sha256']!=sha(planfile):raise ValueError('Existing episode belongs to another plan')
        else:
            if out.exists():raise RuntimeError('Preserve started incomplete episode; manual investigation required')
            used=usage(base)
            if used['started']>=cap['max_started_trials'] or used['tokens']>=cap['reported_token_stop']:
                save(base/'stop.json',{'category':'resource_ceiling','usage':used});break
            probe=resource_probe(config);save(base/'resource-latest.json',probe)
            if probe['active_eda_processes'] or probe['free_disk_bytes']<cap['minimum_free_disk_bytes'] or probe['available_memory_bytes']<cap['minimum_available_memory_bytes'] or probe['load_1m']>cap['maximum_load_1m']:
                save(base/'stop.json',{'category':'resource_readiness'});break
            result=run(planfile,row['trial_id'],out)
        progress.append(result);save(base/'progress.json',progress)
        print(json.dumps({'completed_or_retained':len(progress),'planned':len(ids),'trial':row['trial_id'],'reward':result['terminal']['reward'],'category':result['terminal']['category'],'usage':usage(base)}),flush=True)
        if not result['solver_stop_confirmed'] or (result['terminal']['reward'] is None and result['terminal']['category'] not in ('agent_incomplete','invalid_submission')):
            save(base/'stop.json',{'category':'indeterminate_episode','trial':row['trial_id']});break
    return progress
def batch(planfile,base,config):
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    with (base/'.batch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        prior=os.environ.get('PB_CONFIG')
        try:return _batch(planfile,base,config)
        finally:
            if prior is None:os.environ.pop('PB_CONFIG',None)
            else:os.environ['PB_CONFIG']=prior
            fcntl.flock(lock,fcntl.LOCK_UN)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');p.add_argument('--config',default=os.environ.get('PB_CONFIG','.local/config.json'));a=p.parse_args();batch(a.plan,a.out,a.config)
