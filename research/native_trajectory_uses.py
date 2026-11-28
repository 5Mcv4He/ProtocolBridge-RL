"""Native-v9 research-use review, using training evidence only.

Adds functional-regression evidence when a complete-function measurement was
PASS for function but FAIL for resource budget. Never promotes an untested edit.
"""
import argparse,collections,json
from pathlib import Path
from .trajectory_uses import analyze,load_training,sha
VERSION='native-trajectory-use-rules-v1'
FUNCTIONAL_FAILURES={'transaction_mismatch','transaction_functional_error','protocol_timing_error','not_equivalent','transition_mismatch'}
def review(row,digest):
    if row.get('schema')!='pb-tool-trajectory-v9':raise ValueError('Expected audited native exchange')
    result=analyze(row,digest)
    calls={c['action_index']:c for c in row['native_calls'] if c['action_index'] is not None}
    for event in row['tool_events']:
        if event['action'].get('tool')=='test' and event['executed']:
            call=calls.get(event['action_index'])
            if call is None or call['model_receipt_confirmed']!=event['observation_delivered']:raise ValueError('Receipt evidence differs')
    measured=[];regressions=[]
    for e in row['tool_events']:
        o=e['observation'];m=o.get('measurement')
        if e['executed'] and e['action'].get('tool')=='test' and m and m.get('functional_checks_passed') is True:
            measured.append({'action':e['action_index'],'source_sha256':o['source_sha256'],'measurement':m,'received':e['observation_delivered']})
    for before in measured:
        for after in result['public_tests']:
            if (after['action']>before['action'] and after['sha256']!=before['source_sha256'] and after['status']=='FAIL' and after['category'] in FUNCTIONAL_FAILURES
                and any(e['executed'] and e['action'].get('tool')=='edit' and before['action']<e['action_index']<after['action'] and e['observation'].get('source_sha256')==after['sha256'] for e in row['tool_events'])):
                regressions.append({'before_action':before['action'],'after_action':after['action'],'before_sha256':before['source_sha256'],'after_sha256':after['sha256'],'scope':'Verified function preserved before edit; verified functional violation after edit. Resource success is not implied.'})
    if result['binding_issues']:regressions=[]
    if regressions:result['potential_uses'].append('verified_functional_regression_analysis')
    result.update(functional_measurements=measured,functional_regression_evidence=regressions,
      native_receipt_crosscheck=True,unsubmitted_public_pass=not row['outcome']['submitted'] and any(t['status']=='PASS' for t in result['public_tests']))
    return result

def build(root,policyfile):
    root=Path(root);policyfile=Path(policyfile);policy=json.loads(policyfile.read_text());rows=[];seen=set()
    for item in policy['training_exports']:
        p=root/item['manifest']
        for row in load_training(p,item['sha256']):
            if row['episode_id'] in seen:raise ValueError('Duplicate episode')
            seen.add(row['episode_id']);rows.append(review(row,item['sha256']))
    if len(rows)!=policy['expected_records']:raise ValueError('Declared denominator mismatch')
    return {'schema':VERSION,'rules_sha256':sha(__file__),'policy_sha256':sha(policyfile),'records':len(rows),'use_counts':dict(collections.Counter(u for r in rows for u in r['potential_uses'])),
      'rows':rows,'not_read':['evaluation partitions','offline analyses','private grades','posthoc candidate measurements'],
      'scope':'Review candidates and research evidence, not demonstrated training benefit. Cohorts remain separate.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('policy');p.add_argument('out');p.add_argument('--root',default='.');a=p.parse_args();r=build(a.root,a.policy)
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
