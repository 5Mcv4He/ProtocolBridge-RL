"""Real public/terminal/evaluation checks through the versioned resource session.

No model is sampled. Each task runs three actual trusted checks; one cheap task also exercises all four public calls. Forbidden
reads and exhausted budgets are verified before any additional backend call.
"""
import argparse,json,shutil,tempfile
from pathlib import Path
from .session_v4 import Session,sha,save
from .dispatch_v9 import ROOT,NEW_TASKS,graders

def run(tasks,out):
    if len(tasks)!=len(set(tasks)) or any(t not in NEW_TASKS for t in tasks):raise ValueError('Unique current tasks required')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);checks=[];runs=[]
    def record(name,ok):
        checks.append({'check':name,'accepted':bool(ok)});save(out/'progress.json',checks)
        if not ok:raise RuntimeError('Mechanism check failed: '+name)
    for task in tasks:
        td=ROOT/'tasks'/task;meta=json.loads((td/'task.json').read_text());filename=meta['deliverable']
        work=out/(task+'-work');work.mkdir()
        for p in (td/'spec.md',td/'workspace'/filename):shutil.copyfile(p,work/p.name)
        grade,evaluate=graders(task);calls=[]
        def tracked(p,o,phase):
            calls.append((phase,sha(p)));r=grade(p,o,phase);runs.append(r);return r
        budget=4 if task=='fifo_checker_d1_v1' else 1
        s=Session(meta,work,out/(task+'-session'),tracked,20,budget)
        record(task+'-private-read-denied',s.handle({'tool':'read','file':'reference.sv'}).get('reason')=='file_not_allowed' and not calls)
        s.handle({'tool':'read','file':'spec.md'});s.handle({'tool':'read','file':filename})
        obs=s.handle({'tool':'test'});old=obs.get('source_sha256')
        record(task+'-initial-confirmed-fail',obs.get('status')=='FAIL')
        record(task+'-feedback-allowlist',set(obs)=={'status','category','source_sha256','remaining_test_calls'})
        for _ in range(budget-1):
            repeat=s.handle({'tool':'test'})
            if repeat.get('status')!='FAIL':raise RuntimeError('Repeated initial check changed classification')
        if budget==4:record(task+'-four-real-public-checks',len(calls)==4)
        s.handle({'tool':'edit','content':(td/'reference.sv').read_text()})
        record(task+'-stale-feedback-keeps-source',old!=sha(work/filename) and s.trace[3]['observation']['source_sha256']==old)
        n=len(calls);record(task+'-budget-reject-no-execution',s.handle({'tool':'test'}).get('reason')=='test_budget_exhausted' and len(calls)==n)
        obs=s.handle({'tool':'submit'});f=s.out/'submission'/filename
        record(task+'-frozen-submission',obs.get('source_sha256')==sha(f))
        n=len(calls);record(task+'-closed-episode',s.handle({'tool':'test'}).get('reason')=='episode_closed' and len(calls)==n)
        try:s.finalize(False);denied=False
        except ValueError:denied=True
        record(task+'-stop-required',denied)
        terminal=s.finalize(True);record(task+'-terminal-pass',terminal['reward']==1)
        reserved=evaluate(f,out/(task+'-reserved'));runs.append(reserved);record(task+'-reserved-pass',reserved['reward']==1)
        record(task+'-expected-backend-invocations',len(calls)==budget+1)
        record(task+'-phase-input-separation',terminal['input_sha256']!=reserved['input_sha256'])
        record(task+'-terminal-not-observed',all('reward' not in e['observation'] and 'first_failure' not in e['observation'] for e in s.trace))
        if task=='fifo_checker_d1_v1':
            total=Session(meta,work,out/(task+'-total-budget-session'),tracked,20,4)
            n=len(calls)
            for _ in range(20):total.handle({'tool':'read','file':'spec.md'})
            record(task+'-twenty-action-limit',total.done and total.actions==20)
            record(task+'-twenty-first-no-backend',total.handle({'tool':'test'}).get('reason')=='episode_closed' and len(calls)==n)
        print(task,'mechanisms passed',flush=True)
    result=dict(schema='engineering-resource-runtime-acceptance-v2',accepted=all(c['accepted'] for c in checks),checks=checks,real_backend_invocations=len(runs),task_ids=tasks,
        backend_results=runs,session_sha256=sha(ROOT/'environment/artifact_task/session_v4.py'),controller_sha256=sha(__file__),scope='Real controller checks, not model trials. Remote process isolation separately probed before each model episode.')
    save(out/'result.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--tasks',nargs='+',default=NEW_TASKS);a=p.parse_args();r=run(a.tasks,a.out);print(len(r['checks']),'accepted')
