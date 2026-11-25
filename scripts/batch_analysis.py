"""All-started denominators, descriptive Wilson intervals and preregistered quality gate."""
import argparse,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_policy import analyze
from scripts.audit_policy import audit

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
            rows.append({'trial':name,'policy':entry['policy'],'reward':None,'infrastructure':True,'protocol_errors':0,'actions':0,'effective_edit':False,'submitted':False,'feedback':False,'edited_after_feedback':False,'labels':['infrastructure_error']});continue
        m=json.loads((d/'metrics.json').read_text());t=json.loads((d/'trace.json').read_text());x=next(x for x in a['runs'] if x['trial']==name)
        feedback=[e for e in t if e['action'].get('tool')=='test' and e['executed'] and e.get('observation_delivered') and e['observation'].get('status') in ('PASS','FAIL')]
        edits=[e['action_index'] for e in t if e['action'].get('tool')=='edit' and e['executed']]
        errors=sum(e['observation'].get('reason')=='invalid_action_format' for e in t)
        after=bool(feedback and any(i>feedback[0]['action_index'] for i in edits));labels=[]
        if errors:labels.append('action_protocol_error')
        if not m['first_candidate_source']:labels.append('no_effective_edit_candidate')
        elif not m['submitted']:labels.append('edited_without_submission')
        category=m['terminal']['category']
        if category!='pass':labels.append(category)
        if after and m['terminal']['reward']==0:labels.append('repair_after_feedback_failed')
        times=[e for p in d.rglob('timing.json') for e in json.loads(p.read_text())]
        rows.append({'trial':name,'policy':entry['policy'],'reward':m['terminal']['reward'],'held_out':m['held_out']['reward'] if m['held_out'] else None,'infrastructure':category=='infrastructure_error','protocol_errors':errors,'actions':m['actions'],'effective_edit':bool(m['first_candidate_source']),'submitted':m['submitted'],'feedback':bool(feedback),'failed_feedback':any(e['observation']['status']=='FAIL' for e in feedback),'edited_after_feedback':after,'labels':labels,'tokens':x['usage']['totals'],'wall_seconds':m['wall_seconds'],'model_session_span_seconds':x['model_session_span_seconds'],'compile_wall_seconds':sum(e['wall_seconds'] for e in times if e['kind']=='compile'),'simulation_wall_seconds':sum(e['wall_seconds'] for e in times if e['kind']=='simulate'),'public_test_calls':m['public_test_calls'],'first_candidate_public':m['first_candidate_public'],'api_cost':None})
    groups={}
    for policy in manifest['policies']:
        rs=[r for r in rows if r['policy']==policy];n=len(rs);k=sum(r['reward']==1 for r in rs)
        groups[policy]={'started':n,'effective_edit':sum(r['effective_edit'] for r in rs),'submitted':sum(r['submitted'] for r in rs),'successes':k,'success_rate_all_started':k/n if n else None,'wilson95':interval(k,n),'feedback_exposed':sum(r['feedback'] for r in rs),'edited_after_feedback':sum(r['edited_after_feedback'] for r in rs),'reward_distribution':{str(v):sum(r['reward']==v for r in rs) for v in (0,1,None)},'protocol_error_actions':sum(r['protocol_errors'] for r in rs),'total_actions':sum(r['actions'] for r in rs)}
    reasons=[]
    if not inspection['accepted']:reasons.append('audit_failed')
    if len(rows)!=limit:reasons.append('incomplete_stage')
    if any(r['infrastructure'] for r in rows):reasons.append('infrastructure_failure')
    if rows and sum(not r['effective_edit'] and r['protocol_errors']>0 for r in rows)/len(rows)>=1/3:reasons.append('widespread_protocol_blocked_edits')
    actions=sum(r['actions'] for r in rows)
    if actions and sum(r['protocol_errors'] for r in rows)/actions>.30:reasons.append('protocol_error_action_rate_above_30_percent')
    result={'groups':groups,'rows':rows,'quality_gate':{'passed':not reasons,'reasons':reasons},'protocol':manifest.get('protocol'),'labels_are_nonexclusive':True,'interval_note':'Descriptive Wilson 95%; small samples and paired/time effects prevent causal ranking.','parameter_training':False}
    (root/'batch-analysis.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--limit',type=int,required=True);a=p.parse_args();r=report(a.root,a.limit);print(json.dumps({'groups':r['groups'],'quality_gate':r['quality_gate']},indent=2))
