"""Offline, stratified behavioral analysis. Never selects a candidate for training."""
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.candidate_decisions import analyze

def wilson(k,n):
    if not n:return None
    z=1.96;p=k/n;scale=1+z*z/n;center=(p+z*z/(2*n))/scale
    delta=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    return [max(0,center-delta),min(1,center+delta)]

def summarize(root):
    def started(d):
        return bool(list(d.glob('harness-*.json'))) or ((d/'observations.json').exists() and bool(json.loads((d/'observations.json').read_text())))
    root=Path(root);plan=json.loads((root/'plan.json').read_text());rows=[];sessions=set()
    for t in plan['schedule']:
        trial=root/t['id'];d=trial/'r01-test_diagnostic'
        if not (d/'metrics.json').exists():
            if trial.exists():rows.append(dict(t,state='preflight_or_incomplete',model_started=started(d),decisions=None))
            continue
        decision=analyze(d)
        if not json.loads((trial/'audit.json').read_text())['accepted']:raise ValueError('Unaccepted source-specific audit')
        details=json.loads((trial/'batch-analysis.json').read_text())['rows'][0]
        ids={json.loads(f.read_text())['response']['session_id'] for f in d.glob('harness-*.json')}
        if ids & sessions:raise ValueError('Model session reused across trials')
        sessions|=ids
        row=dict(t,state='complete',model_started=started(d),decisions=decision,
                 resources={k:details.get(k) for k in ('tokens','model_request_wall_seconds','api_cost','wall_seconds','compile_wall_seconds','simulation_wall_seconds','protocol_errors','actions','edits','public_test_calls','compilation_processes','simulation_processes')})
        metrics=json.loads((d/'metrics.json').read_text())
        row['tools']={k:metrics.get(k,0) for k in ('compile_calls','synth_calls','inspect_calls','experiment_calls','observe_calls')}
        row['first_failure_category']=decision['terminal'].get('category')
        row['delivered_public_pass_sources']=sorted({x['source_sha256'] for x in decision['public_tests'] if x['delivered'] and x['status']=='PASS'})
        row['final_differs_from_a_delivered_pass']=any(x!=decision['final_source_sha256'] for x in row['delivered_public_pass_sources'])
        rows.append(row)
    groups=[]
    for start in [x['id'] for x in plan['starts']]:
        for budget in (2,6):
            selected=[r for r in rows if r['start']==start and r['budget']==budget and r['model_started']]
            complete=[r for r in selected if r['decisions'] is not None];decisions=[r['decisions'] for r in complete]
            successes=sum(d['terminal'].get('reward')==1 for d in decisions)
            groups.append({'start':start,'budget':budget,'planned':2,'model_started':len(selected),'completed':len(complete),'missing_outcomes':len(selected)-len(complete),'valid_submissions':sum(d['submission_validity']=='confirmed' for d in decisions),'terminal_successes':successes,'terminal_failures':sum(d['terminal'].get('reward')==0 for d in decisions),'terminal_null':sum(d['terminal'].get('reward') is None for d in decisions),'held_out_successes':sum((d['held_out'] or {}).get('reward')==1 for d in decisions),'used_test3_to6_trials':sum(d['extra_public_tests_used']>0 for d in decisions),'extra_test_calls':sum(d['extra_public_tests_used'] for d in decisions),'final_public_statuses':{status:sum(d['final_public_status']==status for d in decisions) for status in ('PASS','FAIL','UNTESTED','ENV_ERROR','NOT_SUBMITTED')},'resubmitted_known_failures':sum(d['submitted_previously_failed_source'] for d in decisions),'wilson95_terminal_all_started':wilson(successes,len(selected))})
    return {'schema':'verification-budget-results-v1','planned':12,'model_started':sum(r['model_started'] for r in rows),'completed':sum(r['state']=='complete' for r in rows),'distinct_sessions_checked':True,'rows':rows,'groups':groups,'limits':['Exploratory two repetitions per start and condition, not a population-level causal estimate.','A larger test allowance is not an equal-cost intervention.','Private/held-out results never choose intermediate candidates; untested versions remain unknown.','Submitted motives are not observable; report only available evidence and actual actions.']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Preserve prior analysis')
    out.write_text(json.dumps(summarize(a.root),indent=2)+'\n')
