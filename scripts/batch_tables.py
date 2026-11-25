"""Human-readable derived study tables; does not call models or change raw evidence."""
import csv,json
from collections import Counter
from pathlib import Path


def aggregate(rows):
    n=len(rows)
    return {
        'trials':n,
        'json_parse_errors':sum(r.get('parse_errors',0) for r in rows),
        'schema_or_argument_errors':sum(r.get('schema_or_argument_errors',0) for r in rows),
        'compilation_processes':sum(r.get('compilation_processes',0) for r in rows),
        'simulation_processes':sum(r.get('simulation_processes',0) for r in rows),
        'edits':sum(r.get('edits',0) for r in rows),
        'public_calls':sum(r.get('public_test_calls',0) for r in rows),
        'failed_feedback_trials':sum(bool(r.get('failed_feedback')) for r in rows),
        'changed_after_feedback':sum(bool(r.get('changed_after_feedback')) for r in rows),
        'changed_after_failed_feedback':sum(bool(r.get('changed_after_failed_feedback')) for r in rows),
        'protocol_errors_without_candidate':sum(r['protocol_errors']>0 and not r.get('effective_edit') for r in rows),
        'terminal_categories':dict(Counter(r.get('terminal_category','infrastructure_error') for r in rows)),
        'primary_outcomes':dict(Counter(r.get('primary_outcome','infrastructure_error') for r in rows)),
        'first_candidate_public_pass':sum((r.get('first_candidate_public') or {}).get('reward')==1 for r in rows),
        'first_candidate_public_fail':sum((r.get('first_candidate_public') or {}).get('reward')==0 for r in rows),
        'first_candidate_unmeasured':sum((r.get('first_candidate_public') or {}).get('reward') is None for r in rows),
        'final_public_pass_private_fail':sum((r.get('final_candidate_public') or {}).get('reward')==1 and r['reward']==0 for r in rows),
        'held_out_successes':sum(r.get('held_out')==1 for r in rows),
        'terminal_held_out_disagreements':sum(r.get('held_out') in (0,1) and r['reward'] in (0,1) and r['held_out']!=r['reward'] for r in rows),
        'trials_with_protocol_errors':sum(r['protocol_errors']>0 for r in rows),
        'failure_labels_nonexclusive':dict(Counter(x for r in rows for x in r['labels'])),
        'tokens':{k:sum((r.get('tokens') or {}).get(k,0) or 0 for r in rows) if all(isinstance((r.get('tokens') or {}).get(k),(int,float)) for r in rows) else None for k in ('inputTokens','outputTokens','cacheReadTokens','cacheWriteTokens','totalTokens')},
        'seconds':{k:round(sum(r.get(k,0) or 0 for r in rows),3) for k in ('wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds')},
        'timing_observed_trials':{k:sum(r.get(k) is not None for r in rows) for k in ('wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds')},
        'api_currency_cost':None,
    }


def render(root,result):
    root=Path(root);groups=result['groups'];rows=result['rows']
    lines=['# Batch analysis','',
        'All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.','',
        '| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |',
        '|---|---:|---:|---:|---|---:|---:|---|']
    for policy,g in groups.items():
        ci=g['wilson95'];bounds='unknown' if ci is None else '%.1f–%.1f%%'%(100*ci[0],100*ci[1]);d=g['reward_distribution']
        lines.append('| %s | %s | %s | %s | %s | %s | %s | %s / %s / %s |'%(policy,g['started'],g['conditional']['valid_submission']['n'],g['successes'],bounds,g['feedback_exposed'],g['edited_after_feedback'],d['0'],d['1'],d['null']))
    lines+=['','| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |',
        '|---|---|---:|---:|---|---:|---:|---:|---:|---:|']
    for policy,g in groups.items():
        a=g['measurements'];s=a['seconds']
        lines.append('| %s | %s / %s / %s | %s | %s | %s / %s | %s | %.1f | %.1f | %.1f | %.1f |'%(policy,a['first_candidate_public_pass'],a['first_candidate_public_fail'],a['first_candidate_unmeasured'],a['public_calls'],a['changed_after_feedback'],g['protocol_error_actions'],g['total_actions'],a['tokens']['totalTokens'],s['wall_seconds'],s['model_request_wall_seconds'],s['compile_wall_seconds'],s['simulation_wall_seconds']))
    lines+=['','First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.','',
        'Quality gate: `'+json.dumps(result['quality_gate'],sort_keys=True)+'`.','',
        '| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        lines.append('| %s | %s | %s | %s | %s | %s | %s |'%(r['trial'],r['reward'],r.get('held_out'),r.get('edits'),r.get('public_test_calls'),r['protocol_errors'],', '.join(r['labels']) or 'none'))
    lines+=['','| Paired round | '+' | '.join(groups)+' |','|---|'+'---:|'*len(groups)]
    for rep in sorted(set(r['repeat'] for r in rows)):
        values={r['policy']:str(r['reward']) for r in rows if r['repeat']==rep}
        lines.append('| %s | '%rep+' | '.join(values.get(p,'not started') for p in groups)+' |')
    (root/'batch-analysis.md').write_text('\n'.join(lines)+'\n')
    keys=('trial','repeat','policy','reward','held_out','effective_edit','valid_submission','feedback','failed_feedback','changed_after_feedback','edits','actions','protocol_errors','public_test_calls','wall_seconds','model_request_wall_seconds','compile_wall_seconds','simulation_wall_seconds')
    with (root/'trial-measurements.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for r in rows:writer.writerow({k:r.get(k) for k in keys})
