"""Replay actual native transport without API or EDA; do not regrade candidates.

The live audit establishes SDK delivery. This offline audit additionally checks
that every host state transition and receipt flag follows the frozen controller,
including refused calls. Saved public grades are replay inputs, not new results.
"""
import argparse, copy, hashlib, json, tempfile
from pathlib import Path
from environment.artifact_task.session_v4 import Session, sha
from environment.native_tools.controller_v2 import Controller as V2
from environment.native_tools.controller_v3 import Controller as V3
from environment.native_tools.audit import audit
ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads(Path(p).read_text())
def check(trial):
    trial=Path(trial); plan=load(trial/'freeze.json'); result=load(trial/'result.json')
    if result['plan_sha256'] != sha(trial/'freeze.json'): raise ValueError('Plan hash mismatch')
    if any(not (ROOT/f).is_file() or sha(ROOT/f)!=h for f,h in plan['source_files'].items()):
        raise ValueError('Frozen replay dependencies differ')
    if not result['solver_stop_confirmed'] or result['error']: raise ValueError('Incomplete runtime is not accepted by this audit')
    row=next(r for r in plan['trials'] if r['trial_id']==result['trial_id'])
    if row['task_id']!=result['task_id']: raise ValueError('Task mismatch')
    taskdir=ROOT/'tasks'/row['task_id']; task=load(taskdir/'task.json'); filename=task['deliverable']
    events=load(trial/'events.json'); calls=load(trial/'session/native-calls.json'); requests=load(trial/'session/native-requests.json')
    if not events or events[-1].get('kind')!='stopped' or not events[-1].get('runtime_closed'): raise ValueError('Shutdown evidence missing')
    version={'native-artifact-rollout-v2':V2,'native-artifact-rollout-v3':V3,'native-artifact-rollout-v4':V3,'native-artifact-rollout-v5':V3}[result['schema']]
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp)/'work';work.mkdir()
        for name,src in [('spec.md',taskdir/'spec.md'),(filename,taskdir/'workspace'/filename)]:
            (work/name).write_bytes(src.read_bytes())
        tests=[]
        def grade(candidate,dest,phase):
            if phase!='public': raise ValueError('Offline replay must not grade terminal or heldout')
            value=load(trial/'session'/dest.name/'result.json')
            if value['source_sha256']!=sha(candidate): raise ValueError('Public result source mismatch')
            tests.append(dest.name);return value
        session=Session(task,work,Path(tmp)/'session',grade,plan['max_actions'],plan['max_tests'])
        ctrl=version(session,plan['max_requests'])
        for e in events:
            if e.get('kind') in ('model_request','tool_request'):
                ctrl.dispatch(copy.deepcopy(e))
                if e['kind']=='tool_request':ctrl.returned(e['call_id'])
            elif e.get('kind')=='notification':ctrl.response_received(e['notification'].get('payload',{}).get('event',{}))
        if ctrl.calls!=calls or ctrl.requests!=requests:raise ValueError('Native dispatch or receipt replay differs')
        if session.trace!=load(trial/'session/trace.json'):raise ValueError('Session replay differs')
        if load(session.out/'session.json')!=load(trial/'session/session.json'):raise ValueError('Session provenance differs')
        for key,actual in [('actions',session.actions),('edits',session.edits),('public_test_calls',session.tests),('submitted',session.submitted)]:
            if result[key]!=actual:raise ValueError('Result counters differ')
        for p in session.out.glob('candidate-*'):
            if sha(p)!=sha(trial/'session'/p.name):raise ValueError('Candidate artifact differs')
        if session.submitted and sha(session.out/'submission'/filename)!=sha(trial/'session/submission'/filename):raise ValueError('Submitted artifact differs')
    terminal=load(trial/'terminal.json')
    if terminal!=result['terminal']:raise ValueError('Terminal summary differs')
    if result['submitted']:
        if terminal!=load(trial/'session/terminal/result.json'):raise ValueError('Terminal grader result differs')
        if terminal['source_sha256']!=sha(trial/'session/submission'/filename):raise ValueError('Terminal candidate differs')
    elif terminal!={'reward':None,'category':'agent_incomplete'}:raise ValueError('Unsubmitted episode has a grade')
    checked=audit(events,calls,requests,result['submitted'])
    if checked!=load(trial/'audit.json'):raise ValueError('SDK audit differs')
    return {'trial_id':result['trial_id'],'accepted':True,'actions':result['actions'],'public_results_replayed':len(tests),'new_model_or_eda_calls':0,'terminal_reward':terminal['reward']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trials',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    rows=[check(t) for t in a.trials]
    with a.out.open('x') as f:json.dump({'schema':'native-offline-replay-v3','auditor_sha256':sha(__file__),'results':rows},f,indent=2);f.write('\n')
