"""Real combined workflow: development tools, stale result queries, terminal grade."""
import argparse
import json
from pathlib import Path
from environment.engineering_lab import Session
from environment.policy import load
from verifier.task003.scenarios import suite

ROOT=Path(__file__).resolve().parents[1]

def acceptance(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);checks={}
    def check(name,value):
        checks[name]=bool(value)
        (out/'progress.json').write_text(json.dumps(checks,indent=2))
        if not value:raise RuntimeError(name)
    try:
        work=out/'work';work.mkdir()
        source=(ROOT/'fixtures/task003/reference.sv').read_text()
        (work/'bridge.sv').write_text(source)
        (work/'spec.md').write_text('Acceptance uses the source-matched task contract; no model invoked.')
        s=Session(load('test_diagnostic'),work,out/'session',suite(False,20261127))
        check('pre_read_rejected',s.handle({'tool':'synth_check'})['status']=='REJECTED')
        for file in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':file})
        for tool in ('compile','synth_check','test'):
            obs=s.handle({'tool':tool});check(tool+'_pass',obs['status']=='PASS')
            check(tool+'_current',obs['candidate_binding']['is_current'])
        obs=s.handle({'tool':'experiment','scenario':'write_fifo'})
        check('experiment_pass',obs['status']=='PASS')
        obs=s.handle({'tool':'observe','start':'B:0','count':8})
        check('retirement_visible',any('B' in row['events'] for row in obs['rows']))
        check('edit',s.handle({'tool':'edit','content':source+'\n// new candidate revision\n'})['status']=='EDITED')
        check('inspect_stale',s.handle({'tool':'inspect'})['candidate_binding']['is_current'] is False)
        check('observe_stale',s.handle({'tool':'observe','start':'AW:0','count':8})['candidate_binding']['is_current'] is False)
        check('private_read_denied',s.handle({'tool':'read','file':'private/reward.json'})['status']=='REJECTED')
        check('submit',s.handle({'tool':'submit'})['status']=='SUBMITTED')
        check('closed',s.handle({'tool':'test'})['reason']=='episode_closed')
        terminal=s.finalize()
        check('independent_terminal',terminal['reward']==1 and terminal['verification_complete'])
        check('all_nine_actions_exercised',{'read','edit','submit','compile','synth_check','test','inspect','experiment','observe'}<=set(x['action']['tool'] for x in s.trace if x['executed']))
        result={'version':'engineering-lab-v1','accepted':True,'checks':checks,'model_used':False,
                'terminal':{k:terminal.get(k) for k in ('reward','category','source_sha256','suite_sha256')}}
    except Exception as error:
        result={'version':'engineering-lab-v1','accepted':False,'checks':checks,
                'error_type':type(error).__name__,'reason':str(error),'model_used':False}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=acceptance(a.out)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
