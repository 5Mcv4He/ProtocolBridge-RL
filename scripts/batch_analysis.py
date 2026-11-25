"""All-started denominators, descriptive Wilson intervals and preregistered quality gate."""
import argparse,hashlib,json,math,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_policy import analyze
from scripts.audit_policy import audit
from scripts.batch_tables import aggregate,render

def interval(k,n):
    if not n:return None
    z=1.96;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;w=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,c-w),min(1,c+w)]
def report(root,limit):
    root=Path(root);a=analyze(root);manifest=json.loads((root/'experiment.json').read_text());inspection=audit(root,limit);rows=[]
    for entry in manifest['schedule'][:limit]:
        name=entry['id'];d=root/name
        if not (root/(name+'-job.json')).exists() and not d.exists():continue
        if not (d/'metrics.json').exists():
            rows.append({'trial':name,'repeat':entry['repeat'],'policy':entry['policy'],'reward':None,'infrastructure':True,'protocol_errors':0,'actions':0,'effective_edit':False,'submitted':False,'feedback':False,'edited_after_feedback':False,'labels':['infrastructure_error']});continue
        m=json.loads((d/'metrics.json').read_text());t=json.loads((d/'trace.json').read_text());x=next(x for x in a['runs'] if x['trial']==name)
        feedback=[e for e in t if e['action'].get('tool')=='test' and e['executed'] and e.get('observation_delivered') and e['observation'].get('status') in ('PASS','FAIL')]
        edits=[e['action_index'] for e in t if e['action'].get('tool')=='edit' and e['executed']]
        parse_errors=sum(e['observation'].get('reason')=='invalid_action_format' for e in t)
        schema_errors=sum(e['observation'].get('reason')=='invalid_action' for e in t)
        errors=parse_errors+schema_errors
        after=bool(feedback and any(i>feedback[0]['action_index'] for i in edits));labels=[]
        failed_feedback=[e for e in feedback if e['observation']['status']=='FAIL']
        active=manifest.get('starting_rtl_sha256',manifest['source_files']['tasks/axil_to_apb4_001/workspace/bridge.sv']);changed_after=False;changed_after_fail=False
        for event in t:
            if event['executed'] and event['action'].get('tool')=='edit':
                digest=hashlib.sha256(event['action']['content'].encode()).hexdigest()
                if feedback and event['action_index']>feedback[0]['action_index'] and digest!=active:changed_after=True
                if failed_feedback and event['action_index']>failed_feedback[0]['action_index'] and digest!=active:changed_after_fail=True
                active=digest
        bad_turns={e['action_index']-1 for e in t if e['observation'].get('reason') in ('invalid_action_format','invalid_action')}
        rejected_edit_replies=0;request_seconds=0;measured_requests=0
        for f in d.glob('harness-*.json'):
            response=json.loads(f.read_text())['response']
            if int(f.stem.split('-')[1]) in bad_turns and re.search(r'"tool"\s*:\s*"edit"',response.get('final_response') or ''):rejected_edit_replies+=1
            events=response.get('events',[]);starts=[e['time'] for e in events if e['type']=='turn/start'];ends=[e['time'] for e in events if e['type']=='turn/end']
            if starts and ends:request_seconds+=(max(ends)-min(starts))/1000;measured_requests+=1
        if errors:labels.append('action_protocol_error')
        if not m['first_candidate_source']:labels.append('no_effective_edit_candidate')
        elif not m['submitted']:labels.append('edited_without_submission')
        category=m['terminal']['category']
        environment_errors=[key for key in ('terminal','held_out','first_candidate_public') if (m.get(key) or {}).get('category')=='infrastructure_error']
        environment_errors+=['public-%02d'%e['action_index'] for e in t if e['action'].get('tool')=='test' and e['executed'] and e['observation'].get('status')=='ENV_ERROR']
        primary=category
        if category not in ('pass','infrastructure_error','invalid_submission'):
            if not m['edits'] and rejected_edit_replies:primary='action_protocol_blocked_edit'
            elif m['first_candidate_source'] and not m['submitted']:primary='edited_without_submission'
            elif not m['first_candidate_source']:primary='no_effective_edit_candidate'
        if category!='pass':labels.append(category)
        if after and m['terminal']['reward']==0 and any(e['observation']['status']=='FAIL' for e in feedback):labels.append('repair_after_feedback_failed')
        times=[e for p in d.rglob('timing.json') for e in json.loads(p.read_text())]
        def case_count(path):
            return len(json.loads(path.read_text()).get('cases',[])) if path.exists() else None
        case_counts={'terminal':case_count(d/'submission/grade/result.json'),'held_out':case_count(d/'reserved-evaluation/result.json'),'offline_first_candidate':case_count(d/'first-candidate-audit/result.json'),'public':sum(case_count(p) or 0 for p in d.glob('public-*/result.json'))}
        rows.append({'trial':name,'repeat':entry['repeat'],'policy':entry['policy'],'reward':m['terminal']['reward'],'held_out':m['held_out']['reward'] if m['held_out'] else None,'infrastructure':bool(environment_errors),'environment_error_locations':environment_errors,'protocol_errors':errors,'parse_errors':parse_errors,'schema_or_argument_errors':schema_errors,'actions':m['actions'],'edits':m['edits'],'effective_edit':bool(m['first_candidate_source']),'submitted':m['submitted'],'valid_submission':m['submitted'] and category!='invalid_submission','feedback':bool(feedback),'failed_feedback':any(e['observation']['status']=='FAIL' for e in feedback),'edited_after_feedback':after,'changed_after_feedback':changed_after,'changed_after_failed_feedback':changed_after_fail,'public_verdicts':[e['observation']['status'] for e in feedback],'terminal_category':category,'primary_outcome':primary,'rejected_edit_replies':rejected_edit_replies,'model_request_wall_seconds':request_seconds if measured_requests else None,'labels':labels,'tokens':x['usage']['totals'],'wall_seconds':m['wall_seconds'],'model_session_span_seconds':x['model_session_span_seconds'],'compile_wall_seconds':sum(e['wall_seconds'] for e in times if e['kind']=='compile'),'simulation_wall_seconds':sum(e['wall_seconds'] for e in times if e['kind']=='simulate'),'public_test_calls':m['public_test_calls'],'final_candidate_public':m['final_candidate_public'],'first_candidate_public':m['first_candidate_public'],'case_counts':case_counts,'compilation_processes':sum(e['kind']=='compile' for e in times),'simulation_processes':sum(e['kind']=='simulate' for e in times),'api_cost':None})
    groups={}
    for policy in manifest['policies']:
        rs=[r for r in rows if r['policy']==policy];n=len(rs);k=sum(r['reward']==1 for r in rs)
        groups[policy]={'started':n,'effective_edit':sum(r['effective_edit'] for r in rs),'submitted':sum(r['submitted'] for r in rs),'successes':k,'success_rate_all_started':k/n if n else None,'wilson95':interval(k,n),'feedback_exposed':sum(r['feedback'] for r in rs),'edited_after_feedback':sum(r['edited_after_feedback'] for r in rs),'reward_distribution':{('null' if v is None else str(v)):sum(r['reward']==v for r in rs) for v in (0,1,None)},'protocol_error_actions':sum(r['protocol_errors'] for r in rs),'total_actions':sum(r['actions'] for r in rs)}
    for policy,g in groups.items():
        rs=[r for r in rows if r['policy']==policy]
        g['conditional']={}
        for field in ('effective_edit','valid_submission','feedback'):
            subset=[r for r in rs if r.get(field)];n=len(subset);k=sum(r['reward']==1 for r in subset)
            g['conditional'][field]={'n':n,'successes':k,'rate':k/n if n else None,'wilson95':interval(k,n)}
        valid=[r for r in rs if r['reward'] in (0,1)];p=sum(r['reward']==1 for r in valid)/len(valid) if valid else None
        g['determinate_binary_reward_entropy_bits']=None if p is None else sum(-q*math.log(q,2) for q in (p,1-p) if q)
        g['entropy_excludes_null']=True
        g['measurements']=aggregate(rs)
    reasons=[]
    if not inspection['accepted']:reasons.append('audit_failed')
    if len(rows)!=limit:reasons.append('incomplete_stage')
    if any(r['infrastructure'] for r in rows):reasons.append('infrastructure_failure')
    if rows and sum(not r['effective_edit'] and r['protocol_errors']>0 for r in rows)/len(rows)>=1/3:reasons.append('widespread_protocol_blocked_edits')
    actions=sum(r['actions'] for r in rows)
    if actions and sum(r['protocol_errors'] for r in rows)/actions>.30:reasons.append('protocol_error_action_rate_above_30_percent')
    states=[json.loads((root/(e['id']+'-job.json')).read_text()) for e in manifest['schedule'][:limit] if (root/(e['id']+'-job.json')).exists()]
    batch_span=max(x['ended'] for x in states)-min(x['started'] for x in states) if states and all(x.get('status')=='finished' for x in states) else None
    result={'groups':groups,'rows':rows,'quality_gate':{'passed':not reasons,'reasons':reasons},'protocol':manifest.get('protocol'),'labels_are_nonexclusive':True,'interval_note':'Descriptive Wilson 95%; small samples and paired/time effects prevent causal ranking.','parameter_training':False,'batch_span_seconds':batch_span,'analysis_code_sha256':{str(p.relative_to(Path(__file__).resolve().parents[1])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),Path(__file__).with_name('batch_tables.py'),Path(__file__).with_name('analyze_policy.py'),Path(__file__).with_name('audit_policy.py')]}}
    (root/'batch-analysis.json').write_text(json.dumps(result,indent=2));render(root,result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--limit',type=int,required=True);a=p.parse_args();r=report(a.root,a.limit);print(json.dumps({'groups':r['groups'],'quality_gate':r['quality_gate']},indent=2))
