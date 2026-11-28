"""Review generated-domain v10/v11/v12 records using training evidence only.

Reuse existing evidence-based use rules; keep distinct study conditions and
never open held-out partitions or infer correctness of untested candidates.
"""
import argparse
import collections
import json
from pathlib import Path
from research.trajectory_uses import analyze, load_training, sha, checked


def review(row, digest):
    if row.get('schema') not in ('pb-tool-trajectory-v10','pb-tool-trajectory-v11','pb-tool-trajectory-v12'):
        raise ValueError('Unsupported audited generated-task exchange')
    calls={c['action_index']:c for c in row['native_calls'] if c['action_index'] is not None}
    for e in row['tool_events']:
        if e['executed'] and e['action'].get('tool')=='test':
            c=calls.get(e['action_index'])
            if c is None or c['model_receipt_confirmed']!=e.get('observation_delivered'):
                raise ValueError('Actual test receipt differs')
    result=analyze(row,digest)
    if result['binding_issues']:
        raise ValueError('Candidate/feedback binding failed')
    final=result['final_source_sha256']
    result['actual_public_feedback_exposure']=sum(t['delivered'] for t in result['public_tests'])
    result['final_candidate_publicly_measured']=any(t['sha256']==final for t in result['public_tests']) if final else False
    if result['reward']==0 and result['actual_public_feedback_exposure'] and result['changed_edits']:
        result['next_research_candidate']='Fixed-error debugging/feedback study; no successful-repair claim'
    elif result['first_edit_final_terminal_pass']:
        result['next_research_candidate']='Sample another semantic combination before assuming this first-edit PASS generalizes'
    elif 'multi_step_repair_demonstration_review' in result['potential_uses']:
        result['next_research_candidate']='Review actual failure-to-PASS repair with its original conditions'
    else:
        result['next_research_candidate']='More evidence required; do not infer unmeasured candidate quality'
    return result


def build(root, policyfile):
    root=Path(root);policyfile=Path(policyfile);policy=json.loads(policyfile.read_text());rows=[];seen=set()
    if policy.get('schema')!='generated-trajectory-use-policy-v1':raise ValueError('Explicit reviewed inventory required')
    for item in policy['training_exports']:
        for row in load_training(root/item['manifest'],item['sha256']):
            if row['episode_id'] in seen:raise ValueError('Duplicate episode')
            seen.add(row['episode_id']);rows.append(review(row,item['sha256']))
    if len(rows)!=policy['expected_complete_records']:raise ValueError('Declared denominator differs')
    interrupted=0
    for item in policy.get('interrupted_sources',[]):
        r=checked(root/item['summary'],item['sha256'])
        if r.get('original_reward') is not None or r.get('training_exported') is not False:raise ValueError('Interruption scope differs')
        interrupted+=r['started']
    if interrupted!=policy['separately_audited_interrupted_records'] or len(rows)+interrupted!=policy['all_started_records']:raise ValueError('Started denominator differs')
    return dict(schema='generated-trajectory-use-review-v1',rules_sha256=sha(__file__),
        reused_rules_sha256=sha(Path(__file__).with_name('trajectory_uses.py')),policy_sha256=sha(policyfile),
        complete_records=len(rows),all_started_in_declared_stage=policy['all_started_records'],
        separately_audited_interrupted_records=policy['separately_audited_interrupted_records'],
        use_counts=dict(collections.Counter(u for r in rows for u in r['potential_uses'])),rows=rows,
        not_read=['evaluation partitions','private vectors'],not_used=['held-out rewards','offline candidate measurements'],
        scope='Candidate research uses, not proven training benefit. Different contracts and study profiles are not pooled into one success rate. No replacement sampling authorized.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('policy');p.add_argument('out');p.add_argument('--root',default='.')
    a=p.parse_args();r=build(a.root,a.policy)
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
