"""Resume a prespecified package study without repeating completed model trials.

An incomplete started directory needs operator review; timeout of the observer
never authorizes restarting a model trial. No automatic replacement sampling.
"""
import argparse,getpass,json
from pathlib import Path
from environment.artifact_task.session_v4 import save,sha
from task_families.production_lock import exclusive
from .run_package import run,unchanged

def infrastructure_stop(result):
    if result.get('error'):return True
    categories={'infrastructure_error','infrastructure_timeout','proof_timeout','incomplete_comparison'}
    return any((result.get(k) or {}).get('category') in categories for k in ('terminal','reserved_evaluation'))

def evidence_files(directory):
    directory=Path(directory)
    return {str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.name!='completion.json'}

def batch(planfile,out,password=None):
    planfile=Path(planfile).resolve();plan=json.loads(planfile.read_text());out=Path(out).resolve()
    if not unchanged(plan):raise ValueError('Frozen sources differ')
    with exclusive(out):
        frozen=out/'study-plan.json'
        if frozen.exists():
            if frozen.read_bytes()!=planfile.read_bytes():raise ValueError('Different study cannot resume this directory')
        else:frozen.write_bytes(planfile.read_bytes())
        rows=[]
        for trial in plan['trials']:
            dest=out/trial['trial_id'];complete=dest/'result.json';receipt=dest/'completion.json'
            if dest.exists():
                if not complete.exists() or not receipt.exists():raise RuntimeError('Unfinished trial preserved; inspect live processes before any recovery')
                info=json.loads(receipt.read_text());r=json.loads(complete.read_text())
                if info['result_sha256']!=sha(complete) or info['evidence_files']!=evidence_files(dest) or r['plan_sha256']!=sha(planfile) or r['trial_id']!=trial['trial_id']:raise ValueError('Completed trial identity changed')
                rows.append(r)
                if infrastructure_stop(r):break
                continue
            try:r=run(planfile,trial['trial_id'],dest,password)
            except Exception as e:
                save(out/'stopped.json',{'trial_id':trial['trial_id'],'category':'infrastructure_error','exception_type':type(e).__name__,'no_replacement_started':True})
                raise
            save(receipt,{'result_sha256':sha(complete),'plan_sha256':sha(planfile),'evidence_files':evidence_files(dest)})
            rows.append(r);save(out/'results.json',{'planned':len(plan['trials']),'completed':len(rows),'trials':rows})
            print(json.dumps({'trial':r['trial_id'],'reward':r['terminal'].get('reward'),'category':r['terminal'].get('category'),'actions':r['actions'],'tokens':r['reported_tokens']}),flush=True)
            if infrastructure_stop(r):break
        result={'planned':len(plan['trials']),'completed':len(rows),'trials':rows};save(out/'results.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');p.add_argument('--ask-sudo-password',action='store_true');a=p.parse_args()
    secret=getpass.getpass('Authorized worker credential: ') if a.ask_sudo_password else None
    print(json.dumps(batch(a.plan,a.out,secret),indent=2))
