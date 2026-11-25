"""Continue a frozen staged study only after its predeclared quality/cost gate."""
import argparse,fcntl,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.batch_analysis import report

def wait_for(root,count):
    end=time.time()+14400
    while time.time()<end:
        p=root/'summary.json'
        if p.exists() and (json.loads(p.read_text())['completed_runs']>=count or (root/'quality-stop.json').exists()):
            with root.with_name(root.name+'.lock').open('a') as f:fcntl.flock(f,fcntl.LOCK_EX)
            return
        print(json.dumps({'waiting_for_trials':count}),flush=True);time.sleep(30)
    raise RuntimeError('Stage deadline reached; preserve evidence')
def run(command,log):
    with log.open('a') as f:
        p=subprocess.Popen(command,stdout=f,stderr=f)
        while p.poll() is None:
            print(json.dumps({'running':log.name}),flush=True);time.sleep(30)
        if p.returncode:raise RuntimeError('Runner stopped; use explicit resume after inspecting evidence')
def main():
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--repair-out',required=True);p.add_argument('--starting-rtl',required=True);a=p.parse_args();root=Path(a.root)
    wait_for(root,9)
    if (root/'quality-stop.json').exists():return
    pilot=report(root,9);manifest=json.loads((root/'experiment.json').read_text())
    tokens=sum((x.get('tokens') or {}).get('totalTokens',0) or 0 for x in pilot['rows']);seconds=sum(x.get('wall_seconds',0) for x in pilot['rows'])
    estimate={'tokens_for_30':tokens*30/9,'seconds_for_30':seconds*30/9,'api_currency_cost':None}
    allowed=pilot['quality_gate']['passed'] and estimate['tokens_for_30']<=manifest['limits']['max_tokens'] and estimate['seconds_for_30']<=manifest['limits']['max_seconds']
    (root/'expansion-decision.json').write_text(json.dumps({'pilot_gate':pilot['quality_gate'],'estimate':estimate,'expand':allowed},indent=2))
    print(json.dumps({'pilot_gate':pilot['quality_gate'],'estimate':estimate,'expand':allowed}),flush=True)
    if not allowed:return
    command=[sys.executable,'-m','environment.policy_experiment','--out',str(root),'--repeats','10','--limit','30','--resume','--model',manifest['model'],'--protocol',manifest.get('protocol','text-json-atomic-v1')]
    run(command,root.parent/'expansion.log');completed=json.loads((root/'summary.json').read_text())['completed_runs'];full=report(root,completed)
    if completed!=30:return
    if not full['quality_gate']['passed']:return
    run([sys.executable,'-m','verifier.campaign',a.starting_rtl,str(root.parent/'repair-input-check'),'--public'],root.parent/'repair-input-check.log')
    initial=json.loads((root.parent/'repair-input-check/result.json').read_text())
    if initial['reward']!=0:raise RuntimeError('Repair input is not a confirmed functional failure')
    command=[sys.executable,'-m','environment.policy_experiment','--out',a.repair_out,'--policies','test_verdict,test_diagnostic','--repeats','3','--limit','6','--starting-rtl',a.starting_rtl,'--model',manifest['model'],'--protocol',manifest.get('protocol','text-json-atomic-v1')]
    run(command,root.parent/'repair-launch.log');repair=report(a.repair_out,6)
    valid=repair['quality_gate']['passed'] and all(x.get('failed_feedback') and x.get('edited_after_feedback') for x in repair['rows'])
    (Path(a.repair_out)/'repair-validity.json').write_text(json.dumps({'all_trials_entered_feedback_repair':valid,'expanded_beyond_six':False},indent=2))
if __name__=='__main__':main()
