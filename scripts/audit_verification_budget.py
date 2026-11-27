"""Offline cross-trial checks against the pre-sampling plan; never runs a model.

Per-episode semantics remain the responsibility of the source-matched auditor.
This adds the study-level pairing, prompt, input and execution-order checks.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(root):
    root=Path(root);plan=json.loads((root/'plan.json').read_text());rows=[];common=None;sessions=set();times=[]
    for name,digest in plan['runner_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Frozen analysis/runner changed: '+name)
    starts={x['id']:x['source_sha256'] for x in plan['starts']}
    for t in plan['schedule']:
        trial=root/t['id'];d=trial/'r01-test_diagnostic'
        if not (d/'metrics.json').exists():continue
        m=json.loads((trial/'experiment.json').read_text());f=json.loads((d/'freeze.json').read_text());metrics=json.loads((d/'metrics.json').read_text())
        if not json.loads((trial/'audit.json').read_text())['accepted']:raise ValueError('Episode not audited')
        condition=plan['conditions'][str(t['budget'])]
        checks={'task':m['task_id']==plan['task_id'],'model':m['model']==plan['model'],
          'protocol':m['protocol']==plan['protocol'],'capabilities':m['capabilities']==plan['capabilities'],
          'starting_source':m['starting_rtl_sha256']==f['initial_rtl_sha256']==starts[t['start']],
          'exact_policy':f['policy']==condition['policy'],
          'exact_prompt':sha(d/'initial-prompt.txt')==f['prompt_sha256']==condition['prompt_sha256'],
          'total_budget':metrics['actions']<=20,'public_budget':metrics['public_test_calls']<=t['budget'],
          'reward_input':f['private_reward_suite_sha256']==plan['input_sha256']['reward'],
          'heldout_input':f['reserved_evaluation_suite_sha256']==plan['input_sha256']['evaluation'],
          'toolchain':m['toolchain']==plan['toolchain']}
        identity={k:m[k] for k in ('source_files','installed_runtime_files','task_admission','synthesis_binding')}
        identity['worker_settings']=f['worker_settings']
        if common is None:common=identity
        checks['shared_execution_dependencies']=identity==common
        if metrics['submitted']:
            h=sha(d/'submission/bridge.sv')
            checks['terminal_source']=metrics['terminal'].get('source_sha256')==h
            if metrics.get('held_out'):checks['heldout_source']=metrics['held_out'].get('source_sha256')==h
        for p in d.glob('public-*/result.json'):
            r=json.loads(p.read_text())
            checks['public_suite_'+p.parent.name]=r.get('suite_sha256')==plan['public_suite_sha256']
        ids={json.loads(p.read_text())['response']['session_id'] for p in d.glob('harness-*.json')}
        checks['fresh_session']=bool(ids) and not (ids & sessions);sessions|=ids
        job=json.loads((trial/'r01-test_diagnostic-job.json').read_text());times.append(job['started'])
        if not all(checks.values()):raise ValueError(t['id']+': '+str([k for k,v in checks.items() if not v]))
        rows.append({'trial':t['id'],'checks':checks})
    if times!=sorted(times):raise ValueError('Execution order differs from plan')
    prefix=[x['id'] for x in plan['schedule'][:len(rows)]]
    if [x['trial'] for x in rows]!=prefix:raise ValueError('Completed trials are not a schedule prefix')
    return {'schema':'verification-budget-cross-trial-audit-v1','accepted':True,'completed_checked':len(rows),'planned':len(plan['schedule']),
        'all_planned_completed':len(rows)==len(plan['schedule']),'frozen_runner_files_unchanged':True,'execution_order_matches':True,
        'rows':rows,'scope':'Offline cross-trial source, input, budget, prompt and session identity. Uses existing source-specific audits; no new model call, RTL grade, candidate selection or statistical exclusion.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');a=p.parse_args();dest=Path(a.out)
    if dest.exists():raise ValueError('Preserve prior audit')
    dest.write_text(json.dumps(audit(a.root),indent=2)+'\n')
