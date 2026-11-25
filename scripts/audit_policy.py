"""Audit local complete evidence, including the exact prompts actually sent to DSH."""
import argparse,hashlib,json,re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from environment.policy import policy_hash,prompt,validate,parse_action
from environment.feedback import project
from environment.batch_contract import experiment_prompt


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(root,limit=None):
    root=Path(root);experiment=json.loads((root/'experiment.json').read_text());errors=[];sessions=set();results=[]
    task_id=experiment.get('task_id','axil_to_apb4_001')
    if task_id not in ('axil_to_apb4_001','axil_to_apb4_router_002'):raise ValueError('Unknown task audit contract')
    task_dir='tasks/'+task_id
    projector=project
    if task_id=='axil_to_apb4_router_002':
        from environment.task002 import project as projector
    def require(ok,msg):
        if not ok:errors.append(msg)
    for entry in experiment['schedule'][:limit]:
        name=entry['id'];d=root/name
        if not (d/'metrics.json').exists():errors.append(name+': missing trial');continue
        metrics=json.loads((d/'metrics.json').read_text());freeze=json.loads((d/'freeze.json').read_text())
        require(freeze.get('task_id','axil_to_apb4_001')==task_id and metrics.get('task_id','axil_to_apb4_001')==task_id,name+': task identity mismatch')
        policy=validate(json.loads((d/'policy.json').read_text()))
        trace=json.loads((d/'trace.json').read_text()) if (d/'trace.json').exists() else []
        observations=json.loads((d/'observations.json').read_text()) if (d/'observations.json').exists() else []
        require(policy_hash(policy)==freeze['policy_sha256']==metrics['policy_sha256']==experiment['policies'][entry['policy']]['sha256'],name+': policy mismatch')
        require(policy['policy_id']==metrics['policy_id']==entry['policy'],name+': policy identity mismatch')
        expected_runtime={k:v for k,v in experiment['source_files'].items()
                          if k.split('/')[0] in ('environment','verifier','fixtures','tasks')}
        require(freeze['files']==expected_runtime,name+': deployed runtime differs from experiment freeze')
        require(digest(d/'initial-prompt.txt')==freeze['prompt_sha256']==experiment['policies'][entry['policy']]['prompt_sha256'],name+': prompt hash mismatch')
        protocol=experiment.get('protocol','text-json-atomic-v1')
        require(freeze.get('action_protocol','text-json-atomic-v1')==protocol,name+': action protocol mismatch')
        if observations:require(observations[0]['prompt']==experiment_prompt(policy,'starting_rtl_sha256' in experiment,protocol),name+': unexpected initial observation')
        else:require(metrics['actions']==0 and metrics['terminal']['reward'] is None,name+': missing initial observation')
        require(metrics['freeze_unchanged'],name+': freeze failure')
        if not metrics['solver_stopped_before_evaluation']:
            require(metrics['terminal']['reward'] is None and metrics['held_out'] is None,name+': evaluated before solver stop')
        require(len(trace)==metrics['actions']<=20,name+': action accounting')
        count=0;edit_count=0;read_files=set();active_text=None
        active_source=experiment.get('starting_rtl_sha256',experiment['source_files'][task_dir+'/workspace/bridge.sv'])
        spec_source=experiment['source_files'][task_dir+'/spec.md']
        for i,event in enumerate(trace):
            action=event['action'];obs=event['observation'];tool=action.get('tool')
            if event['executed']:
                require(tool in policy['allowed_tools'],name+': executed forbidden tool')
            if tool=='test' and event['executed']:
                count+=1;p=d/('public-%02d'%event['action_index'])/'result.json'
                require(p.exists(),name+': public result missing')
                if p.exists():
                    result=json.loads(p.read_text())
                    require(obs==projector(result,policy,policy['max_public_test_calls']-count),name+': public projection differs')
                    require(result['source_sha256']==active_source,name+': public test used a different candidate')
            elif tool=='test':require(not (d/('public-%02d'%event['action_index'])).exists(),name+': rejected test executed')
            if tool=='read' and event['executed']:
                require(action['file'] in policy['readable_files'],name+': forbidden read');read_files.add(action['file'])
                require(obs['file']==action['file'],name+': wrong file observation')
                if action['file']=='spec.md':require(hashlib.sha256(obs['content'].encode()).hexdigest()==spec_source,name+': Spec observation differs')
                elif active_text is None:require(hashlib.sha256(obs['content'].encode()).hexdigest()==active_source,name+': initial RTL observation differs')
                else:require(obs['content']==active_text.replace('\r\n','\n').replace('\r','\n'),name+': current RTL observation differs')
            if tool=='edit' and event['executed']:
                require(read_files==set(policy['readable_files']),name+': edit before required reads')
                edit_count+=1;candidate=d/('candidate-%02d.sv'%event['action_index'])
                require(candidate.read_bytes()==action['content'].encode(),name+': edit differs from saved RTL')
                active_source=digest(candidate);active_text=action['content']
            if tool=='submit' and event['executed']:require(read_files==set(policy['readable_files']),name+': submit before required reads')
            delivered=event.get('observation_delivered',False)
            if delivered:
                require(i+1<len(observations),name+': missing delivered observation')
                if i+1<len(observations):require(json.loads(observations[i+1]['prompt'])=={'tool_result':obs},name+': actual model input differs from projected observation')
            else:require(i==len(trace)-1,name+': unexplained nondelivery')
        require(count==metrics['public_test_calls']<=policy['max_public_test_calls'],name+': test budget')
        require(edit_count==metrics['edits'],name+': edit accounting')
        sid=set()
        for f in d.glob('harness-*.json'):
            r=json.loads(f.read_text());sid.add(r['response']['session_id'])
            require(r['worker_uid']==1101 and r['worker_pid']==1,name+': unexpected worker identity')
            turn=int(f.stem.split('-')[1]);events=r['response'].get('events',[])
            try:decoded=parse_action(r['response']['final_response'])
            except (ValueError,KeyError,TypeError):decoded={}
            if turn<len(trace):require(decoded==trace[turn]['action'],name+': executed action differs from whole-response decoding')
            else:require(metrics['terminal']['reward'] is None,name+': unaccounted model action')
            user_inputs=[]
            for event in events:
                data=event.get('data',{})
                if event['type']=='user/message':
                    content=data.get('content',[])
                    require(all(c.get('type')=='text' for c in content),name+': unexpected non-text SDK input')
                    text=''.join(c.get('text','') for c in content)
                    kind=data.get('source',{}).get('kind')
                    if kind=='user':user_inputs.append(text)
                    elif kind=='runtime-context':
                        sections=data['source'].get('sections',[])
                        require(len(sections)==1 and sections[0].get('name')=='working-directory:current',name+': unexpected SDK environment observation')
                        if len(sections)==1:
                            directory=sections[0].get('text','')
                            require(bool(re.fullmatch(r'Current working directory: "/work/policy-[a-f0-9]{32}"\.',directory)),name+': unexpected SDK directory')
                            expected=chr(10).join(['<system-reminder>',
                                'The following information describes your current session:',
                                '',directory,'</system-reminder>'])
                            require(text==expected,name+': unexpected SDK context payload')
                    else:require(False,name+': unexpected SDK input source')
                elif event['type']=='system/message':
                    text=''.join(c.get('text','') for c in data.get('message',{}).get('content',[]))
                    require(text=='You are a helpful software engineer assistant.',name+': SDK system prompt changed')
                elif event['type']=='request/header':
                    config=data.get('header',{}).get('config',{})
                    require(all(config.get(k)==v for k,v in {'model':experiment['model'],'provider':'deepseek-official','maxTokens':7000,'reasoningEffort':'off'}.items()),name+': model request parameters changed')
            require(turn<len(observations) and user_inputs and all(x==observations[turn]['prompt'] for x in user_inputs),name+': actual Harness input differs from controller observation')
        require(len(sid)<=1 and not (sid & sessions),name+': session reused')
        if not sid:require(metrics['actions']==0 and metrics['terminal']['reward'] is None,name+': missing real model evidence')
        sessions.update(sid)
        paired=experiment['paired_suite_hashes'][str(entry['repeat'])]
        require(paired['reward']!=paired['evaluation'],name+': reward/held-out inputs identical')
        for key,split in [('private_reward_suite_sha256','reward'),('reserved_evaluation_suite_sha256','evaluation')]:
            require(metrics[key]==freeze[key]==paired[split],name+': paired inputs changed')
        if metrics['submitted']:
            source=digest(d/'submission/bridge.sv')
            require(source==active_source,name+': submission differs from last model-written RTL')
            if metrics['terminal']['source_sha256'] is not None:require(metrics['terminal']['source_sha256']==source,name+': terminal candidate mismatch')
            else:require(metrics['terminal']['reward'] is None,name+': determinate reward without candidate identity')
            if metrics['terminal']['suite_sha256'] is not None:require(metrics['terminal']['suite_sha256']==paired['reward'],name+': terminal suite mismatch')
            else:require(metrics['terminal']['reward'] is None,name+': determinate reward without suite')
            if metrics['held_out']:
                require(metrics['held_out']['source_sha256']==source,name+': held-out candidate mismatch')
                if metrics['held_out']['suite_sha256'] is not None:require(metrics['held_out']['suite_sha256']==paired['evaluation'],name+': held-out suite mismatch')
                else:require(metrics['held_out']['reward'] is None,name+': determinate held-out reward without suite')
        results.append({'trial':name,'actions':len(trace),'public_calls':count,'policy':entry['policy']})
    report={'accepted':not errors,'trials':results,'errors':errors,'audit_scope':'Full local trace, exact Harness user/system/context inputs, request parameters, worker identities, budgets, submissions, runtime hashes and paired suites; no new simulation.',
            'common_sdk_observation':'Fixed helpful-software-engineer system prompt and the fresh solver working directory only.'}
    (root/'audit.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--limit',type=int);a=p.parse_args();r=audit(a.source,a.limit);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
