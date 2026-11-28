"""Describe audited candidate evolution without new grading or held-out selection.

Case-level regression means an identical actually executed public input passed
on one source and failed on a later source. It does not imply either entire
candidate was correct, or that the solver received the offline case details.
"""
import argparse
import json
from pathlib import Path
from environment.artifact_task.session_v4 import sha
from scripts.check_package_replay_v2 import check
from scripts.package_costs import grade_cost


def regressions(tests):
    findings=[]
    for earlier,later in zip(tests,tests[1:]):
        if earlier['source_sha256']==later['source_sha256']:continue
        old={c['name']:c for c in earlier['cases']};new={c['name']:c for c in later['cases']}
        for name in sorted(set(old)&set(new)):
            if (earlier['inputs'].get(name)==later['inputs'].get(name)
                    and name in earlier['inputs'] and old[name]['reward']==1 and new[name]['reward']==0
                    and new[name]['category'] in ('protocol_timing_error','transaction_functional_error')):
                findings.append(dict(case=name,earlier_action=earlier['action_index'],later_action=later['action_index'],
                    earlier_source_sha256=earlier['source_sha256'],later_source_sha256=later['source_sha256'],
                    scope='Same executed public input: PASS then confirmed functional/timing FAIL; offline case-level evidence'))
    return findings


def analyze(trial):
    trial=Path(trial).resolve();replay=check(trial)
    complete=json.loads((trial/'completion.json').read_text())
    if sha(trial/'result.json')!=complete['result_sha256'] or any(sha(trial/f)!=h for f,h in complete['evidence_files'].items()):
        raise ValueError('Completed source evidence changed')
    result=json.loads((trial/'result.json').read_text());trace=json.loads((trial/'session/trace.json').read_text())
    calls={c['action_index']:c for c in json.loads((trial/'session/native-calls.json').read_text()) if c.get('action_index') is not None}
    tests=[];edits=[];public_cost=[]
    for event in trace:
        action=event['action_index'];tool=event['action']['tool'];o=event['observation']
        if event['executed'] and tool=='edit':edits.append(dict(action_index=action,source_sha256=o['source_sha256']))
        if event['executed'] and tool=='test' and o['status'] in ('PASS','FAIL','ENV_ERROR'):
            d=trial/'session'/('public-%02d'%action);r=json.loads((d/'result.json').read_text())
            inputs=json.loads((d/'cases.json').read_text());receipt=calls[action]
            if r['source_sha256']!=o['source_sha256']:raise ValueError('Public candidate identity differs')
            tests.append(dict(action_index=action,source_sha256=r['source_sha256'],verdict=o['status'],
                 feedback_observation=o,transport_returned=receipt['transport_returned'],
                 model_receipt_confirmed=receipt['model_receipt_confirmed'],
                 cases=r['cases'],inputs={c['name']:c for c in inputs}))
            public_cost.append(dict(action_index=action,**grade_cost(d)))
    final=result['terminal'].get('source_sha256');matched=[t for t in tests if t['source_sha256']==final] if final else []
    terminal_cost=grade_cost(trial/'session/terminal') if result['submitted'] else None
    return dict(schema='audited-package-behavior-v1',trial_id=result['trial_id'],task_id=result['task_id'],
                result_sha256=sha(trial/'result.json'),replay=replay,analyzer_sha256=sha(__file__),
                edits=edits,public_tests=[{k:v for k,v in t.items() if k not in ('cases','inputs')} for t in tests],
                final_source_sha256=final,final_public_verdict=matched[-1]['verdict'] if matched else 'UNTESTED' if final else 'UNSUBMITTED',
                submitted_known_public_failure=bool(matched and matched[-1]['verdict']=='FAIL'),
                edits_after_last_public_test=sum(e['action_index']>tests[-1]['action_index'] for e in edits) if tests else len(edits),
                public_case_regressions=regressions(tests),
                terminal_reward=result['terminal']['reward'],terminal_category=result['terminal']['category'],
                costs=dict(reported_tokens=result['reported_tokens'],whole_trial_wall_seconds=result['wall_seconds'],
                    public=public_cost,terminal=terminal_cost,model_request_wall_seconds=None,api_currency_cost=None),
                scope='Offline analysis of actual public executions and final training-side grade. No held-out outcomes, new candidate tests, candidate ranking or training selection. Model request timing and currency cost unavailable in this profile.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial');p.add_argument('out');a=p.parse_args();r=analyze(a.trial)
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(dict(trial=r['trial_id'],final_public_verdict=r['final_public_verdict'],case_regressions=len(r['public_case_regressions']))))
