"""Replay-audited engineering artifact trajectories (v7); no private logs.

The replay never launches an EDA tool or repairs a model response. It checks
actions against the original raw response and reuses hash-bound recorded results.
"""
import argparse,hashlib,json,tempfile
from pathlib import Path
from environment.policy import parse_action
from environment.artifact_task.session import Session,sha,save
from environment.artifact_task.runner import ROOT

def audit(root):
    root=Path(root);plan=json.loads((root/'freeze.json').read_text());result=json.loads((root/'result.json').read_text())
    trace=json.loads((root/'session/trace.json').read_text());requests=json.loads((root/'requests.json').read_text())
    taskdir=ROOT/'tasks'/result['task_id'];task=json.loads((taskdir/'task.json').read_text())
    expected=plan.get('prompts',{}).get(task['deliverable'],plan.get('prompt'))
    if requests[0]['input']['prompt']!=expected or sha(root/'freeze.json')!=result['plan_sha256']:raise ValueError('Prompt or plan identity differs')
    if {'trial_id':result['trial_id'],'task_id':result['task_id']} not in plan['trials']:raise ValueError('Unplanned trial')
    for p in (taskdir/'spec.md',taskdir/'workspace'/task['deliverable']):
        if sha(p)!=plan['source_files'][str(p.relative_to(ROOT))]:raise ValueError('Initial material differs')
    tokens=0;protocol_errors=0;schema_errors=0;tool_seconds=0
    with tempfile.TemporaryDirectory() as t:
        work=Path(t)/'work';work.mkdir()
        for p in (taskdir/'spec.md',taskdir/'workspace'/task['deliverable']):(work/p.name).write_bytes(p.read_bytes())
        def recorded(source,out,phase):
            nonlocal tool_seconds
            p=root/'session'/out.name/'result.json'
            r=json.loads(p.read_text());tool_seconds+=r.get('wall_seconds',0)
            if sha(source)!=r['source_sha256']:raise ValueError('Tool checked wrong candidate')
            return r
        cls=Session
        if result['schema'] in ('artifact-rollout-v2','artifact-rollout-v3','artifact-rollout-v4','artifact-rollout-v5','artifact-rollout-v6','artifact-rollout-v7'):
            from environment.artifact_task.session_v2 import Session as CurrentSession
            cls=CurrentSession
        elif plan.get('rejection_feedback')=='explicit-v2':
            from environment.artifact_task.feedback_v2 import ExplicitRejectionSession
            cls=ExplicitRejectionSession
        replay=cls(task,work,Path(t)/'session',recorded,plan['max_actions'],plan['max_tests'])
        for i,event in enumerate(trace):
            raw=json.loads((root/('harness-%02d.json'%i)).read_text())['response']
            try:a=parse_action(raw['final_response'])
            except (ValueError,TypeError):a={'tool':'invalid'};protocol_errors+=1
            if a!=event['action']:raise ValueError('Raw action mismatch')
            observation=replay.handle(a)
            if a.get('tool')!='invalid' and observation.get('reason')=='invalid_action_format':schema_errors+=1
            if observation!=event['observation'] or replay.trace[-1]['executed']!=event['executed']:raise ValueError('Feedback or execution mismatch')
            delivered=i+1<len(requests) and requests[i+1]['response_received']
            if delivered and json.loads(requests[i+1]['input']['prompt'])!={'tool_result':observation}:raise ValueError('Delivered feedback mismatch')
            if delivered!=event['observation_delivered']:raise ValueError('Exposure flag mismatch')
            for e in raw.get('events',[]):
                if e.get('type')=='assistant/message':tokens+=(e['data'].get('usage') or {}).get('totalTokens',0)
        if [replay.actions,replay.edits,replay.tests,replay.submitted]!=[result[k] for k in ('actions','edits','public_test_calls','submitted')]:raise ValueError('Count mismatch')
        if replay.submitted:
            frozen=root/'session/submission'/task['deliverable']
            if sha(frozen)!=sha(work/task['deliverable']) or result['terminal'].get('source_sha256')!=sha(frozen):raise ValueError('Final candidate mismatch')
        if not result['frozen_sources_unchanged']:raise ValueError('Frozen sources changed')
        if not result['solver_stop_confirmed']:
            # Preserve interrupted records without claiming a confirmed terminal
            # boundary. No independent scoring may have run in this state.
            if result['terminal'].get('reward') is not None or result['terminal'].get('category')!='infrastructure_error' or result['reserved_evaluation'] is not None or (root/'session/terminal').exists():
                raise ValueError('Scoring occurred without confirmed solver stop')
    return {'accepted':True,'solver_stop_confirmed':result['solver_stop_confirmed'],'terminal_evaluation_performed':(root/'session/terminal').exists(),'trial_id':result['trial_id'],'actions':len(trace),'tokens':tokens,'protocol_errors':protocol_errors+schema_errors,'reply_parse_errors':protocol_errors,'action_schema_errors':schema_errors,
            'public_check_wall_seconds':round(tool_seconds,4),'checks':['raw_action_replay','feedback_whitelist_and_projection','candidate_hash_binding','budgets','actual_feedback_delivery','submission_identity','solver_stop_and_freeze'],
            'limits':'Exit and freeze claims are controller evidence, not independent OS attestation; no model hidden reasoning inference.'}

def export(roots,out):
    roots=[Path(r).resolve() for r in roots]
    if len(roots)!=len(set(roots)):raise ValueError('Duplicate episode')
    audits=[audit(r) for r in roots];out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for d in ('training','evaluation','analysis','artifacts'):(out/d).mkdir()
    records=[];evaluations=[];analyses=[]
    def artifact(content,suffix):
        digest=hashlib.sha256(content.encode()).hexdigest();name='artifacts/'+digest+suffix
        (out/name).write_text(content);return {'file':name,'sha256':digest}
    for root,checked in zip(roots,audits):
        r=json.loads((root/'result.json').read_text());plan=json.loads((root/'freeze.json').read_text());events=[]
        for e in json.loads((root/'session/trace.json').read_text()):
            a=dict(e['action']);o=dict(e['observation'])
            if 'content' in a:a['content_artifact']=artifact(a.pop('content'),'.txt')
            if 'content' in o:o['content_artifact']=artifact(o.pop('content'),'.txt')
            events.append(dict(e,action=a,observation=o))
        p=list((root/'session/submission').glob('*')) if r['submitted'] else []
        final=artifact(p[0].read_text(),p[0].suffix) if p else None
        records.append({'schema':'pb-tool-trajectory-v7','episode_id':r['plan_sha256']+':'+r['trial_id'],'task_id':r['task_id'],'study':plan['study_id'],
            'model':r['model'],'versions':plan['source_files'],'initial_prompt':json.loads((root/'requests.json').read_text())[0]['input']['prompt'],'tool_events':events,'final_submission':final,
            'outcome':{'reward':r['terminal']['reward'],'category':r['terminal']['category'],'submitted':r['submitted']},
            'resources':dict(checked,model_request_seconds=r['model_request_seconds'],api_currency_cost=None),
            'optimizer_inputs_available':{'token_ids':False,'behavior_log_probabilities':False,'model_weight_revision':False}})
        evaluations.append({'trial_id':r['trial_id'],'evaluation':r['reserved_evaluation'],'use':'evaluation_only_not_training_reward'})
        analyses.append({'trial_id':r['trial_id'],'audit':checked,'whole_trial_seconds':r['wall_seconds'],'terminal_seconds':r['terminal'].get('wall_seconds'),'offline_intermediate_tests':0})
    for name,rows in [('training/rollouts.jsonl',records),('evaluation/heldout.jsonl',evaluations),('analysis/offline.jsonl',analyses)]:
        (out/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    manifest={'schema':'pb-exchange-manifest-v7','records':len(records),'exporter_sha256':sha(__file__),'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        'scope':'Reviewed tool interactions; raw model replies preserved privately and used for replay audit. No token-level on-policy training claim.'}
    save(out/'manifest.json',manifest);return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('sources',nargs='+');a=p.parse_args();print(json.dumps(export(a.sources,a.out),indent=2))
