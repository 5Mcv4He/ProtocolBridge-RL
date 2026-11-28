"""Replay actual native transport without API or EDA; do not regrade candidates.

The live audit establishes SDK delivery. This offline audit additionally checks
that every host state transition and receipt flag follows the frozen controller,
including refused calls. Saved public grades are replay inputs, not new results.
"""
import argparse, copy, hashlib, json, tempfile
from pathlib import Path
from environment.package_session import Session
from environment.artifact_task.session_v4 import sha
from environment.register_admission_v1 import validate as validate_admission
from environment.native_tools.run_register_v1 import unchanged
from environment.native_tools.controller_v2 import Controller as V2
from environment.native_tools.controller_v3 import Controller as V3
from environment.native_tools.audit import audit
ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads(Path(p).read_text())
def check(trial, *, interrupted=False):
    trial=Path(trial); plan=load(trial/'freeze.json'); result=load(trial/'result.json')
    completion=load(trial/'completion.json')
    actual={str(p.relative_to(trial)):sha(p) for p in sorted(trial.rglob('*'))
            if p.is_file() and p.name!='completion.json'}
    if (completion['result_sha256']!=sha(trial/'result.json')
            or completion['plan_sha256']!=sha(trial/'freeze.json')
            or completion['evidence_files']!=actual):
        raise ValueError('Sealed completion evidence changed')
    if result['plan_sha256'] != sha(trial/'freeze.json'): raise ValueError('Plan hash mismatch')
    if not unchanged(plan):
        raise ValueError('Frozen replay dependencies differ')
    if not result['solver_stop_confirmed']: raise ValueError('Unconfirmed runtime shutdown')
    if interrupted:
        if result['error']!='public_environment_error' or result['submitted']:
            raise ValueError('Only a confirmed public-environment stop is supported by interruption replay')
    elif result['error']:
        raise ValueError('Incomplete runtime is not accepted by this audit')
    row=next(r for r in plan['trials'] if r['trial_id']==result['trial_id'])
    if row['task_id']!=result['task_id']: raise ValueError('Task mismatch')
    if sha(row['admission'])!=row['admission_sha256']:raise ValueError('Admission changed')
    admission=validate_admission(row['admission'],plan['config'])
    taskdir=Path(admission['package']);task=dict(load(taskdir/'task.json'),deliverable='bridge.sv');filename='bridge.sv'
    if admission['package_manifest_sha256']!=result['package_manifest_sha256']:raise ValueError('Package source differs')
    events=load(trial/'events.json'); calls=load(trial/'session/native-calls.json'); requests=load(trial/'session/native-requests.json')
    if not events or events[-1].get('kind')!='stopped' or not events[-1].get('runtime_closed'): raise ValueError('Shutdown evidence missing')
    if result['schema']!='native-register-material-rollout-v1':raise ValueError('Unsupported rollout profile')
    version=V3
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
                reply=ctrl.dispatch(copy.deepcopy(e))
                if interrupted and reply['observation'].get('status')=='ENV_ERROR':
                    session.done=True
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
        original=load(trial/'session/terminal/result.json')
        if terminal!=original:raise ValueError('Terminal grader differs')
        if terminal['frozen_input_sha256']!=row['input_sha256']['terminal']:raise ValueError('Terminal input identity differs')
        if terminal['source_sha256']!=sha(trial/'session/submission'/filename):raise ValueError('Terminal candidate differs')
    elif interrupted:
        if terminal!={'reward':None,'category':'infrastructure_error','exception_type':'public_environment_error'}:
            raise ValueError('Interrupted episode must preserve its original indeterminate result')
        if not calls or calls[-1]['observation'].get('status')!='ENV_ERROR':
            raise ValueError('Interruption does not follow public environment feedback')
        if result.get('reserved_evaluation') is not None:
            raise ValueError('Unsubmitted interruption cannot have held-out grading')
    elif terminal!={'reward':None,'category':'agent_incomplete'}:raise ValueError('Unsubmitted episode has a grade')
    from scripts.register_grade_audit import audit_grade
    for d in sorted((trial/'session').glob('public-*')):
        if (d/'result.json').exists(): audit_grade(d, admission['package'], row, 'public')
    if result['submitted']:
        audit_grade(trial/'session/terminal', admission['package'], row, 'terminal')
        held=load(trial/'reserved-evaluation.json')
        if held != result['reserved_evaluation'] or held != load(trial/'reserved-evaluation/result.json'):
            raise ValueError('Heldout record differs')
        audit_grade(trial/'reserved-evaluation', admission['package'], row, 'heldout')
    checked=audit(events,calls,requests,result['submitted'])
    if not interrupted and checked!=load(trial/'audit.json'):raise ValueError('SDK audit differs')
    return {'trial_id':result['trial_id'],'accepted':True,'scope':'interrupted_research_record' if interrupted else 'completed_runtime',
            'training_eligible':False if interrupted else None,'sdk_audit':checked,
            'actions':result['actions'],'public_results_replayed':len(tests),'new_model_or_eda_calls':0,'terminal_reward':terminal['reward']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trials',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--interrupted-research-only',action='store_true');a=p.parse_args()
    rows=[check(t,interrupted=a.interrupted_research_only) for t in a.trials]
    with a.out.open('x') as f:json.dump({'schema':'native-register-offline-replay-v1','auditor_sha256':sha(__file__),'results':rows},f,indent=2);f.write('\n')
