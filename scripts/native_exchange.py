"""V9 exchange: native proposals, executed actions and received feedback stay distinct.

Only whitelisted terminal/evaluation summaries are copied. Runtime streams,
private inputs, operational configuration and EDA logs remain in local storage.
"""
import argparse,copy,hashlib,json
from pathlib import Path
from environment.native_tools.audit import audit

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def export(planfile,runs,out):
    planfile=Path(planfile);plan=json.loads(planfile.read_text());runs=Path(runs);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    def artifact(data,suffix='.txt'):
        raw=data if isinstance(data,bytes) else data.encode();h=hashlib.sha256(raw).hexdigest();name='artifacts/'+h+suffix
        p=out/name;p.parent.mkdir(exist_ok=True);p.write_bytes(raw);return {'file':name,'sha256':h}
    training=[];evaluation=[]
    def grade_summary(value):
        if value is None:return None
        keys=('reward','category','verification_complete','source_sha256','input_sha256','grader_sha256','compile_exit','simulation_exit','compile_seconds','simulation_seconds','wall_seconds')
        return {k:value[k] for k in keys if k in value}
    for row in plan['trials']:
        path=runs/row['trial_id']
        if not (path/'started.json').exists():continue
        if not (path/'result.json').exists():raise ValueError('Started trial lacks terminal record; retain and resolve before export')
        result=json.loads((path/'result.json').read_text());session=path/'session'
        if result['plan_sha256']!=sha(planfile):raise ValueError('Plan mismatch')
        calls=json.loads((session/'native-calls.json').read_text());requests=json.loads((session/'native-requests.json').read_text());events=json.loads((path/'events.json').read_text())
        checked=audit(events,calls,requests,result['submitted'])
        if checked!=json.loads((path/'audit.json').read_text()):raise ValueError('Audit mismatch')
        metadata=json.loads((session/'session.json').read_text());filename=metadata['deliverable']
        task=Path('tasks')/row['task_id'];initial=task/'workspace'/filename
        if sha(initial)!=metadata['initial_sha256'] or sha(task/'spec.md')!=plan['source_files'][str(task/'spec.md')]:raise ValueError('Initial materials differ')
        traces=copy.deepcopy(json.loads((session/'trace.json').read_text()))
        for event in traces:
            action=event['action'];obs=event['observation']
            if 'content' in action:action['content_artifact']=artifact(action.pop('content'))
            if 'content' in obs:obs['content_artifact']=artifact(obs.pop('content'))
        native=[]
        for c in calls:
            native.append({'call_id':c['request']['call_id'],'tool':c['request']['name'],'arguments_artifact':artifact(c['raw_arguments'],'.json'),
                'action_index':c['action_index'],'executed':c['executed'],'transport_returned':c['transport_returned'],
                'feedback_text_sha256':c['observation_text_sha256'],'model_receipt_confirmed':c['model_receipt_confirmed'],
                'argument_projection':c.get('argument_projection')})
        messages=[];schemas=[];model_ms=0;step_start={}
        for r in events:
            e=r.get('notification',{}).get('payload',{}).get('event',{});d=e.get('data',{})
            if e.get('type')=='step/start':step_start[(d['turn'],d['step'])]=e['time']
            elif e.get('type')=='request/header':schemas.append(d['header'].get('tools',[]))
            elif e.get('type')=='assistant/message':
                model_ms+=e['time']-step_start.get((d['turn'],d['step']),e['time'])
                blocks=[]
                for b in d['message']['content']:
                    if b['type']=='tool-call':blocks.append({'type':'tool-call','id':b['id'],'name':b['name'],'arguments_artifact':artifact(b['arguments'],'.json')})
                    elif b['type']=='text':blocks.append({'type':'text','text':b['text']})
                messages.append({'event_seq':e['seq'],'turn':d['turn'],'step':d['step'],'content':blocks,'usage':d.get('usage')})
        submitted=artifact((session/'submission'/filename).read_bytes(),Path(filename).suffix) if result['submitted'] else None
        terminal=result['terminal']
        if submitted and terminal.get('source_sha256') not in (None,submitted['sha256']):raise ValueError('Final result differs from exported artifact')
        public=[json.loads(p.read_text()) for p in sorted(session.glob('public-*/result.json'))]
        active_grades=[g for g in public+[terminal] if 'compile_seconds' in g]
        episode=sha(planfile)+':'+row['trial_id']
        training.append({'schema':'pb-tool-trajectory-v9','episode_id':episode,'task_id':row['task_id'],
          'cohort':{'study':plan['study_id'],'model':plan['model'],'protocol':result['schema'],'reasoning':plan.get('reasoning_effort'),'max_actions':plan['max_actions'],'max_tests':plan['max_tests'],'max_requests':plan['max_requests']},
          'versions':{'source_commit':plan['source_commit'],'source_manifest':plan['source_files'],'plan_sha256':sha(planfile),'harness':plan['harness']},
          'initial_prompt':plan['prompts'][filename],'native_tool_schemas':schemas,
          'task_inputs':{'spec':artifact((task/'spec.md').read_bytes()),'initial_artifact':artifact(initial.read_bytes(),initial.suffix)},
          'model_messages':messages,'native_calls':native,'model_requests':requests,'tool_events':traces,'final_submission':submitted,
          'outcome':{'reward':terminal.get('reward'),'category':terminal.get('category'),'submitted':result['submitted'],'valid_submission':result['submitted'] and terminal.get('category')!='invalid_submission','infrastructure':bool(result['error'] or terminal.get('category') in ('infrastructure_error','infrastructure_timeout'))},
          'resources':{'reported_tokens':result['reported_tokens'],'tokens':result['reported_tokens'],'actions':result['actions'],'edits':result['edits'],'public_test_calls':result['public_test_calls'],'wall_seconds':result['wall_seconds'],'model_step_wall_seconds':round(model_ms/1000,4),'compile_calls_training':len(active_grades),'compile_seconds_training':sum(x.get('compile_seconds',0) for x in active_grades),'simulation_seconds_training':sum(x.get('simulation_seconds',0) for x in active_grades),'api_cost':None},
          'audit':checked,'optimizer_inputs_available':{'token_ids':False,'behavior_log_probabilities':False,'exact_model_weights':False,'raw_tool_argument_text':True,'assistant_text':True}})
        evaluation.append({'episode_id':episode,'reserved_evaluation':grade_summary(result.get('reserved_evaluation'))})
    for name,rows in [('training/rollouts.jsonl',training),('evaluation/heldout.jsonl',evaluation)]:
        p=out/name;p.parent.mkdir(exist_ok=True);p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
    write(out/'analysis/offline.json',{'intermediate_candidates_regraded':False,'note':'No posthoc candidate grades are included or used to select records.'})
    files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    write(out/'manifest.json',{'schema':'pb-exchange-manifest-v9','records':len(training),'exporter_sha256':sha(__file__),'files':files,'scope':'Actual native proposals and feedback, including failed/incomplete episodes. Exchange is not proof of training utility; evaluation is separate.'})
    return {'records':len(training),'manifest_sha256':sha(out/'manifest.json')}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('runs');p.add_argument('out');a=p.parse_args();print(json.dumps(export(a.plan,a.runs,a.out)))
