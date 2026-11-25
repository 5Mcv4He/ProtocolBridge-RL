"""Policy rollout controller on trusted UTM host; original v3 controller is unchanged."""
import argparse,hashlib,json,select,subprocess,sys,time,uuid
from pathlib import Path
from .reset import ROOT
from .policy import load,canonical,policy_hash,prompt,parse_action
from .policy_session import Session
from .batch_contract import experiment_prompt
from verifier.campaign import sha


def source_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for d in ('tasks','verifier','environment','fixtures')
            for p in sorted((ROOT/d).rglob('*')) if p.is_file() and '__pycache__' not in str(p)}

def run(out,bootstrap):
    out=Path(out).resolve();policy=load(bootstrap['policy'])
    reward_file=Path(bootstrap['private_suite']);evaluation_file=Path(bootstrap['evaluation_suite'])
    reward=json.loads(reward_file.read_text());evaluation=json.loads(evaluation_file.read_text())
    name='policy-'+uuid.uuid4().hex;work=Path('/opt/protocolbridge-runtime/work')/name
    subprocess.run(['sudo','-n','install','-d','-o','1101','-g','1000','-m','0770',str(work)],check=True)
    task_id=bootstrap.get('task_id','axil_to_apb4_001')
    if task_id not in ('axil_to_apb4_001','axil_to_apb4_router_002','axil_to_apb4_queue_003'):raise ValueError('Unsupported task')
    task=ROOT/'tasks'/task_id
    session_type=Session
    if task_id=='axil_to_apb4_router_002':
        from .task002 import Session as session_type
    elif task_id=='axil_to_apb4_queue_003':
        from .task003 import Session as session_type
    initial=Path(bootstrap.get('starting_rtl',task/'workspace/bridge.sv'))
    if 'starting_rtl' in bootstrap and sha(initial)!=bootstrap['starting_rtl_sha256']:raise ValueError('Repair input hash mismatch')
    for dest,src in [('spec.md',task/'spec.md'),('bridge.sv',initial)]:
        (work/dest).write_bytes(src.read_bytes());(work/dest).chmod(0o664)
    session=session_type(policy,work,out,reward)
    session.repair=bool(bootstrap.get('starting_rtl'))
    protocol=bootstrap.get('protocol','text-json-atomic-v1')
    initial_prompt=experiment_prompt(policy,session.repair,protocol);frozen=source_hashes()
    session.protocol_version=2 if protocol=='text-json-atomic-v2' else 1
    manifest={'task_id':task_id,'action_protocol':protocol,'initial_rtl_sha256':sha(initial),'files':frozen,'policy':policy,'policy_sha256':policy_hash(policy),
              'policy_file_sha256':sha(ROOT/'environment/policies'/(policy['policy_id']+'.json')),
              'prompt_sha256':hashlib.sha256(initial_prompt.encode()).hexdigest(),
              'private_reward_suite_sha256':sha(reward_file),'reserved_evaluation_suite_sha256':sha(evaluation_file),
              'model':bootstrap['model'],'worker_settings':{'profile':'sdk-minimal','reasoning_effort':'off','max_tokens':7000,
              'temperature':'SDK/provider default; not explicitly fixed','seed':'not set'},'source_commit':bootstrap.get('source_commit')}
    (out/'freeze.json').write_text(json.dumps(manifest,indent=2));(out/'initial-prompt.txt').write_text(initial_prompt)
    start=time.time();process=None;transport_error=None;stopped=False
    stderr=(out/'worker-stderr.log').open('w');observations=[];request_prompt=initial_prompt
    try:
        process=subprocess.Popen(['sudo','-n','/usr/local/sbin/pb-sandbox','/work/'+name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,universal_newlines=True,bufsize=1)
        def send(x):process.stdin.write(json.dumps(x)+'\n');process.stdin.flush()
        send({'api_key':bootstrap['api_key'],'model':bootstrap['model']})
        for turn in range(policy['max_agent_actions']):
            observations.append({'turn':turn,'prompt':request_prompt})
            (out/'observations.json').write_text(json.dumps(observations,indent=2))
            send({'prompt':request_prompt})
            if session.trace:
                session.trace[-1]['observation_delivered']=True
                (out/'trace.json').write_text(json.dumps(session.trace,indent=2))
            ready,_,_=select.select([process.stdout],[],[],240)
            if not ready:raise RuntimeError('Model worker timed out')
            line=process.stdout.readline()
            if not line:raise RuntimeError('Model worker ended')
            message=json.loads(line)
            if 'worker_error' in message:raise RuntimeError('Model worker failed')
            (out/('harness-%02d.json'%turn)).write_text(json.dumps(message,indent=2))
            try:action=parse_action(message['response']['final_response'])
            except (ValueError,KeyError,TypeError):action={}
            obs=session.handle(action)
            session.trace[-1]['observation_delivered']=False
            (out/'trace.json').write_text(json.dumps(session.trace,indent=2))
            print(json.dumps({'turn':turn,'tool':action.get('tool'),'public_calls':session.tests}),flush=True)
            if session.done:break
            request_prompt=json.dumps({'tool_result':obs},ensure_ascii=True)
        send({'stop':True})
    except Exception as e:
        transport_error=type(e).__name__
        (out/'controller-error.json').write_text(json.dumps({'type':transport_error}))
    finally:
        if process is not None:
            try:process.stdin.close();process.wait(timeout=30);stopped=True
            except Exception:
                process.terminate()
                try:process.wait(timeout=15)
                except Exception:pass
        stderr.close()
    # No private tests or post-hoc feedback run until the solver is confirmed stopped.
    unchanged=(frozen==source_hashes() and sha(reward_file)==manifest['private_reward_suite_sha256'] and sha(evaluation_file)==manifest['reserved_evaluation_suite_sha256'])
    result={'reward':None,'category':'agent_incomplete'};held=None;first=None
    if not stopped or not unchanged or transport_error:
        result={'reward':None,'category':'infrastructure_error'}
    else:
        result=session.finalize()
        if session.submitted:
            held=session.verify(out/'submission/bridge.sv',out/'reserved-evaluation',cases=evaluation)
        if session.first_candidate:
            # Same public suite for all policies; offline measurement, never sent to solver.
            candidate=out/session.first_candidate;h=sha(candidate)
            matching=[x for x in session.public if x['source_sha256']==h]
            first=matching[0]['result'] if matching else session.verify(candidate,out/'first-candidate-audit',public=True)
            (out/'first-candidate-result.json').write_text(json.dumps(first,indent=2))
    def brief(r):
        if r is None:return None
        return {k:r.get(k) for k in ('reward','category','verification_complete','source_sha256','suite_sha256','planned','checked','aborted','failed_case')}
    final_hash=sha(out/'submission/bridge.sv') if session.submitted else None
    final_public=[x for x in session.public if x['source_sha256']==final_hash]
    metrics={'task_id':task_id,'policy_id':policy['policy_id'],'policy_sha256':manifest['policy_sha256'],'model':bootstrap['model'],
        'actions':session.actions,'edits':session.edits,'public_test_calls':session.tests,'submitted':session.submitted,
        'terminal':brief(result),'held_out':brief(held),'first_candidate_public':brief(first),
        'first_candidate_source':session.first_candidate,'first_candidate_measurement':'post-hoc or matching actual public call; never additional solver feedback',
        'final_candidate_public':brief(final_public[-1]['result']) if final_public else None,
        'freeze_unchanged':unchanged and frozen==source_hashes(),'solver_stopped_before_evaluation':stopped,
        'wall_seconds':round(time.time()-start,3),'api_usage':None,'api_cost':None,
        'api_usage_note':'Raw Harness response events retained; availability extracted separately.',
        'private_reward_suite_sha256':manifest['private_reward_suite_sha256'],
        'reserved_evaluation_suite_sha256':manifest['reserved_evaluation_suite_sha256']}
    (out/'result.json').write_text(json.dumps(result,indent=2));(out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps({'policy':policy['policy_id'],'terminal':brief(result)}),flush=True)
    return metrics

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');args=p.parse_args();run(args.out,json.loads(sys.stdin.readline()))
