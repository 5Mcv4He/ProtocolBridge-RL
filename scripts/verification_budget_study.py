"""Execute a frozen, bounded repair schedule using source-matched existing runners.

One commercial-tool trial at a time. Complete trials are audited/exported once;
incomplete trials are preserved and stop expansion rather than silently rerun.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from task_families.package import verify
from scripts.analyze_policy import usage
from scripts.export_task_rollouts import export
from scripts.candidate_decisions import analyze
from environment.remote_backend import remote_command

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    p=Path(p);t=p.with_suffix('.tmp');t.write_text(json.dumps(data,indent=2)+'\n');os.replace(str(t),str(p))
def run(package,admission,starts,inputs,plan,out):
    package=Path(package).resolve();admission=Path(admission).resolve();starts=Path(starts).resolve();inputs=Path(inputs).resolve();plan=Path(plan).resolve();out=Path(out).resolve()
    verify(package);p=json.loads(plan.read_text());plan_sha=sha(plan)
    if sha(package/'family-manifest.json')!=p['source_manifest_sha256'] or sha(admission/'freeze.json')!=p['admission_freeze_sha256']:raise ValueError('Study source/admission mismatch')
    for x in p['starts']:
        if sha(starts/(x['id']+'.sv'))!=x['source_sha256']:raise ValueError('Starting candidate drift')
    for split,h in p['input_sha256'].items():
        if sha(inputs/('r01-'+split+'.json'))!=h:raise ValueError('Input drift')
    out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    frozen=out/'plan.json'
    if frozen.exists() and sha(frozen)!=plan_sha:raise ValueError('Frozen plan changed')
    if not frozen.exists():frozen.write_bytes(plan.read_bytes())
    if (out/'STOP.json').exists():raise ValueError('Stopped study requires review; no automatic replacement trials')
    cfg_path=Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).resolve();cfg=json.loads(cfg_path.read_text())
    used=0;elapsed=0;rows=[];prior=None
    for t in p['schedule']:
        name=t['id'];trial=out/name;complete=out/(name+'-completed.json')
        if complete.exists():
            row=json.loads(complete.read_text())
            for name_hash,digest in row['raw_evidence_hashes'].items():
                if sha(trial/'r01-test_diagnostic'/name_hash)!=digest:raise ValueError('Completed evidence changed; never regrade automatically')
            if sha(out/(name+'-exchange')/'manifest.json')!=row['exchange_manifest_sha256']:raise ValueError('Completed export changed')
            rows.append(row);used+=row['tokens'];elapsed+=row['wall_seconds'];prior=prior or trial;continue
        if sha(plan)!=plan_sha:raise ValueError('Plan changed during study')
        if trial.exists():raise ValueError('Incomplete trial preserved; inspect before any further model call: '+name)
        if used>=p['limits']['between_trial_tokens'] or elapsed>=p['limits']['between_trial_seconds']:
            save(out/'STOP.json',{'reason':'between_trial_resource_limit','completed':len(rows),'tokens':used});break
        probe="import os,shutil,json;from pathlib import Path; names=[]\nfor f in Path('/proc').glob('[0-9]*/comm'):\n try:\n  n=f.read_text().strip()\n  if n in ('simv','vcs','vcs1','dc_shell','fm_shell','pt_shell'):names.append(n)\n except IOError:pass\nprint(json.dumps({'free_bytes':shutil.disk_usage('.').free,'active_eda':names,'load':os.getloadavg()}))"
        r=subprocess.run(['ssh','-F',cfg['ssh_config'],cfg['host'],remote_command(cfg,'python3 -c '+__import__('shlex').quote(probe))],capture_output=True,universal_newlines=True,check=True,timeout=45)
        resource=json.loads(r.stdout);save(out/(name+'-resources.json'),resource)
        if resource['free_bytes']<4*1024**3 or resource['active_eda']:raise RuntimeError('Resource preflight rejected; no model started')
        cmd=[sys.executable,'-m','environment.policy_experiment','--out',str(trial),'--task','x2p_queue_three_v1','--admission',str(admission),'--policies','test_diagnostic','--model',p['model'],'--protocol',p['protocol'],'--repeats','1','--limit','1','--capabilities','engineering-lab-v1','--public-test-budget',str(t['budget']),'--starting-rtl',str(starts/(t['start']+'.sv')),'--paired-inputs',str(inputs),'--max-tokens',str(p['limits']['between_trial_tokens']-used),'--max-seconds',str(p['limits']['between_trial_seconds']-int(elapsed))]
        if prior is not None:cmd+=['--preflight-from',str(prior)]
        print('START',name,'completed',len(rows),'tokens',used,flush=True)
        with (out/(name+'-controller.log')).open('w') as log:r=subprocess.run(cmd,cwd=package,env=dict(os.environ,PB_CONFIG=str(cfg_path)),stdout=log,stderr=subprocess.STDOUT)
        episode=trial/'r01-test_diagnostic'
        if r.returncode or not (episode/'metrics.json').exists():
            save(out/'STOP.json',{'reason':'controller_or_preflight_failure','trial':name,'exit_code':r.returncode,'preserve_all_raw':True});break
        m=json.loads((episode/'metrics.json').read_text());u=usage(list(episode.glob('harness-*.json')));tokens=(u.get('totals') or {}).get('totalTokens')
        if tokens is None:raise RuntimeError('Unknown usage; stop expansion')
        used+=tokens;elapsed+=m['wall_seconds']
        subprocess.run([sys.executable,'scripts/audit_policy.py',str(trial)],cwd=package,stdout=(out/(name+'-audit.log')).open('w'),check=True)
        exchange=out/(name+'-exchange');export(package,trial,exchange)
        row={'trial':name,'start':t['start'],'repeat':t['repeat'],'budget':t['budget'],'tokens':tokens,'wall_seconds':m['wall_seconds'],'decisions':analyze(episode),'exchange_manifest_sha256':sha(exchange/'manifest.json'),'raw_evidence_hashes':{str(f.relative_to(episode)):sha(f) for f in sorted(episode.rglob('*')) if f.is_file()}}
        save(complete,row);rows.append(row);save(out/'progress.json',{'completed':len(rows),'tokens':used,'rows':rows})
        print('FINISH',name,'reward',m['terminal']['reward'],'tokens',used,flush=True)
        prior=prior or trial
        if row['decisions']['conflicting_public_verdict_sources'] or any(e['observation'].get('status')=='ENV_ERROR' for e in json.loads((episode/'trace.json').read_text())) or m['terminal']['category']=='infrastructure_error' or (episode/'controller-error.json').exists() or (m.get('held_out') or {}).get('category')=='infrastructure_error':
            save(out/'STOP.json',{'reason':'infrastructure_failure','trial':name,'completed':len(rows)});break
    save(out/'summary.json',{'plan_sha256':plan_sha,'planned':len(p['schedule']),'completed':len(rows),'tokens':used,'wall_seconds':elapsed,'rows':rows,'stopped':(out/'STOP.json').exists()})
    print('STUDY_SAVED',len(rows),used,flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser()
    for x in ('package','admission','starts','inputs','plan','out'):a.add_argument('--'+x,required=True)
    n=a.parse_args();run(**vars(n))
