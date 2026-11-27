"""Derive published descriptive totals and inventory without raw private logs.

Offline only: no new metrics, sample selection, model request or RTL verification.
The original frozen per-trial analysis remains unchanged.
"""
import argparse,collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.summarize_verification_budget import wilson

def derive(root,base):
    root=Path(root);base=Path(base)
    s=json.loads((root/'study-results.json').read_text())
    if s['completed']!=12:raise ValueError('Expected the complete declared cohort')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    rows=s['rows'];groups=[]
    for budget in (2,6):
     rs=[r for r in rows if r['budget']==budget];ds=[r['decisions'] for r in rs];res=[r['resources'] for r in rs]
     n=len(rs);success=sum(d['terminal'].get('reward')==1 for d in ds);valid=sum(d['submission_validity']=='confirmed' for d in ds)
     edits=[e for d in ds for e in d['edits']];unique=sum(len({e['source_sha256'] for e in d['edits']}) for d in ds)
     tools=collections.Counter();errors=collections.Counter()
     for r in rs:
      events=json.loads((root/'trials'/r['id']/'tool-summary.json').read_text())['events']
      for e in events:
       if e['executed']:tools[e['action'].get('tool')]+=1
       elif e['observation'].get('reason'):errors[e['observation']['reason']]+=1
     groups.append({'budget':budget,'started':n,'valid_submissions':valid,'reward_distribution':dict(collections.Counter(('null' if d['terminal'].get('reward') is None else str(d['terminal']['reward'])) for d in ds)),
     'terminal_success_fraction_all_started':[success,n],'wilson95_all_started':wilson(success,n),'terminal_success_fraction_valid':[success,valid],'wilson95_valid':wilson(success,valid),
     'heldout_executed':sum(d['held_out'] is not None for d in ds),'heldout_successes':sum((d['held_out'] or {}).get('reward')==1 for d in ds),
     'final_public_statuses':dict(collections.Counter(d['final_public_status'] for d in ds)),
     'extra_test_exposed_trials':sum(d['extra_public_tests_used']>0 for d in ds),'extra_tests':sum(d['extra_public_tests_used'] for d in ds),
     'same_source_repeated_public_tests':sum(len(d['public_tests'])-len({x['source_sha256'] for x in d['public_tests']}) for d in ds),
     'edit_actions':len(edits),'byte_changing_edits':sum(e['changed_bytes'] for e in edits),'edits_with_later_matching_full_test':sum(bool(e['later_public_test_actions']) for e in edits),
     'distinct_edited_sources_within_trials':unique,'distinct_edited_sources_never_full_tested':sum(len(d['never_publicly_tested_edited_sources']) for d in ds),
     'post_pass_edits':sum(len(d['edited_after_delivered_pass']) for d in ds),'known_failed_full_test_submissions':sum(d['submitted_previously_failed_source'] for d in ds),
     'offline_first_candidate_passes':sum((d['offline_first_candidate'] or {}).get('reward')==1 for d in ds),
     'resource_totals':{k:sum(r[k] for r in res) for k in ('wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds','compilation_processes','simulation_processes','protocol_errors','actions')},
     'tokens':{k:sum(r['tokens'][k] for r in res) for k in res[0]['tokens']},'executed_tools':dict(tools),'rejection_reasons':dict(errors)})
    result={'schema':'verification-budget-descriptive-costs-v1','source_results_sha256':sha(root/'study-results.json'),'groups':groups,'api_currency_cost':None,
     'resource_scope':'Per-episode measured model/tool/terminal/heldout and scheduled first-candidate measurement; common preflight and industrial gate excluded. Sum of episode wall durations, not whole campaign elapsed. Compile/simulation are process wall time, not CPU time. DSH totalTokens includes cache-read tokens.',
     'definitions':'Edit coverage is action-level; repeated identical edit is separately marked. Source counts are deduplicated within each trial, not across independent trials. Heldout remains independent; no candidate selection uses it. Wilson intervals are descriptive small-sample binomial intervals, not paired causal inference.'}
    costs=result
    old=json.loads(base.read_text());ids=set();entries=[]
    for previous in old['additional_exports']:
     f=Path(previous['manifest']);m=json.loads(f.read_text());assert sha(f)==previous['manifest_sha256']
     for name,digest in m['files'].items():assert sha(f.parent/name)==digest
     for r in (f.parent/'training/rollouts.jsonl').read_text().splitlines():
      e=json.loads(r);ident=e.get('episode_id');assert ident and ident not in ids;ids.add(ident)
    for trial in json.loads((root/'study-plan.json').read_text())['schedule']:
     f=root/'trials'/trial['id']/'exchange/manifest.json';m=json.loads(f.read_text());assert m['records']==m['available_tool_trajectories']==1
     for name,digest in m['files'].items():assert sha(f.parent/name)==digest
     e=json.loads((f.parent/'training/rollouts.jsonl').read_text());ident=e['episode_id'];assert ident not in ids;ids.add(ident)
     entries.append({'trial':trial['id'],'manifest':str(f),'sha256':sha(f),'episode_id':ident,'content_hashes_verified':True})
    inventory={'schema':'reviewed-exchange-inventory-v2','records':old['records']+12,'available_tool_trajectories':old['available_tool_trajectories']+12,'base_inventory':str(base),'base_sha256':sha(base),'new_model_trials':12,'new_tool_trajectories':12,'exports':entries,'scope':'Historical inventory preserved. New full trajectories include unsuccessful and no-submit episodes; export availability does not establish training utility. No aggregate success rate across different conditions.'}
    return costs,inventory

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--base-inventory',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise ValueError('Preserve prior derived evidence')
    costs,inventory=derive(a.evidence,a.base_inventory);out.mkdir(parents=True)
    for name,value in (('cost-and-behavior.json',costs),('exchange-inventory.json',inventory)):
        (out/name).write_text(json.dumps(value,indent=2)+'\n')
