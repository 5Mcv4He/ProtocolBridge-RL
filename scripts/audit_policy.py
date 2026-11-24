"""Audit local complete evidence, including the exact prompts actually sent to DSH."""
import argparse,hashlib,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from environment.policy import policy_hash,prompt,validate
from environment.feedback import project


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(root):
    root=Path(root);experiment=json.loads((root/'experiment.json').read_text());errors=[];sessions=set();results=[]
    def require(ok,msg):
        if not ok:errors.append(msg)
    for entry in experiment['schedule']:
        name=entry['id'];d=root/name
        if not (d/'metrics.json').exists():errors.append(name+': missing trial');continue
        metrics=json.loads((d/'metrics.json').read_text());freeze=json.loads((d/'freeze.json').read_text())
        policy=validate(json.loads((d/'policy.json').read_text()))
        trace=json.loads((d/'trace.json').read_text()) if (d/'trace.json').exists() else []
        observations=json.loads((d/'observations.json').read_text()) if (d/'observations.json').exists() else []
        require(policy_hash(policy)==freeze['policy_sha256']==metrics['policy_sha256']==experiment['policies'][entry['policy']]['sha256'],name+': policy mismatch')
        require(digest(d/'initial-prompt.txt')==freeze['prompt_sha256']==experiment['policies'][entry['policy']]['prompt_sha256'],name+': prompt hash mismatch')
        if observations:require(observations[0]['prompt']==prompt(policy),name+': unexpected initial observation')
        else:require(metrics['actions']==0 and metrics['terminal']['reward'] is None,name+': missing initial observation')
        require(metrics['freeze_unchanged'],name+': freeze failure')
        if not metrics['solver_stopped_before_evaluation']:
            require(metrics['terminal']['reward'] is None and metrics['held_out'] is None,name+': evaluated before solver stop')
        require(len(trace)==metrics['actions']<=20,name+': action accounting')
        count=0;edit_count=0
        for i,event in enumerate(trace):
            action=event['action'];obs=event['observation'];tool=action.get('tool')
            if event['executed']:
                require(tool in policy['allowed_tools'],name+': executed forbidden tool')
            if tool=='test' and event['executed']:
                count+=1;p=d/('public-%02d'%event['action_index'])/'result.json'
                require(p.exists(),name+': public result missing')
                if p.exists():require(obs==project(json.loads(p.read_text()),policy,policy['max_public_test_calls']-count),name+': public projection differs')
            elif tool=='test':require(not (d/('public-%02d'%event['action_index'])).exists(),name+': rejected test executed')
            if tool=='read' and event['executed']:require(action['file'] in policy['readable_files'],name+': forbidden read')
            if tool=='edit' and event['executed']:
                edit_count+=1;require((d/('candidate-%02d.sv'%event['action_index'])).read_text()==action['content'],name+': edit differs from saved RTL')
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
        require(len(sid)<=1 and not (sid & sessions),name+': session reused')
        if not sid:require(metrics['actions']==0 and metrics['terminal']['reward'] is None,name+': missing real model evidence')
        sessions.update(sid)
        paired=experiment['paired_suite_hashes'][str(entry['repeat'])]
        for key,split in [('private_reward_suite_sha256','reward'),('reserved_evaluation_suite_sha256','evaluation')]:
            require(metrics[key]==freeze[key]==paired[split],name+': paired inputs changed')
        if metrics['submitted']:
            source=digest(d/'submission/bridge.sv')
            if metrics['terminal']['source_sha256'] is not None:require(metrics['terminal']['source_sha256']==source,name+': terminal candidate mismatch')
            else:require(metrics['terminal']['reward'] is None,name+': determinate reward without candidate identity')
            if metrics['terminal']['suite_sha256'] is not None:require(metrics['terminal']['suite_sha256']==paired['reward'],name+': terminal suite mismatch')
            else:require(metrics['terminal']['reward'] is None,name+': determinate reward without suite')
            if metrics['held_out']:
                require(metrics['held_out']['source_sha256']==source,name+': held-out candidate mismatch')
                if metrics['held_out']['suite_sha256'] is not None:require(metrics['held_out']['suite_sha256']==paired['evaluation'],name+': held-out suite mismatch')
                else:require(metrics['held_out']['reward'] is None,name+': determinate held-out reward without suite')
        results.append({'trial':name,'actions':len(trace),'public_calls':count,'policy':entry['policy']})
    report={'accepted':not errors,'trials':results,'errors':errors,'audit_scope':'Full local trace, exact solver observations, Harness identities, budgets, submissions and paired suites; no new simulation.'}
    (root/'audit.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');a=p.parse_args();r=audit(a.source);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
