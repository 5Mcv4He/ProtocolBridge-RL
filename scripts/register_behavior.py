"""Observed candidate choices only; no held-out selection or posthoc grading."""
import argparse
from pathlib import Path
from environment.register_backend_v1 import read, sha, save
from scripts.check_register_replay import check
from scripts.register_grade_audit import grade_cost


def analyze(trial):
    trial = Path(trial); replay = check(trial)
    result = read(trial/'result.json'); trace = read(trial/'session/trace.json')
    calls = {x['action_index']: x for x in read(trial/'session/native-calls.json')
             if x.get('action_index') is not None}
    edits, tests = [], []
    for row in trace:
        if not row['executed']:
            continue
        tool = row['action']['tool']; obs = row['observation']; i = row['action_index']
        if tool == 'edit':
            edits.append(dict(action_index=i, source_sha256=obs['source_sha256']))
        elif tool == 'test':
            tests.append(dict(action_index=i, source_sha256=obs['source_sha256'],
                verdict=obs['status'], actual_feedback=obs,
                model_receipt_confirmed=calls[i]['model_receipt_confirmed'],
                cost=grade_cost(trial/'session'/('public-%02d'%i))))
    final = result['terminal'].get('source_sha256')
    matched = [t for t in tests if t['source_sha256']==final]
    for edit in edits:
        edit['publicly_tested_identical_source'] = any(t['source_sha256']==edit['source_sha256'] for t in tests)
    return dict(schema='register-candidate-behavior-v1', trial_id=result['trial_id'],
        result_sha256=sha(trial/'result.json'), replay=replay, edits=edits, public_tests=tests,
        final_source_sha256=final,
        final_public_verdict=matched[-1]['verdict'] if matched else 'UNTESTED' if final else 'UNSUBMITTED',
        edits_after_last_test=sum(e['action_index']>tests[-1]['action_index'] for e in edits) if tests else len(edits),
        submitted_known_public_failure=bool(matched and matched[-1]['verdict']=='FAIL'),
        terminal_reward=result['terminal']['reward'], reported_tokens=result['reported_tokens'],
        actual_failure_feedback_received=any(t['verdict']=='FAIL' and t['model_receipt_confirmed'] for t in tests),
        scope='Actual public feedback and final training-side result only. Untested edits remain unmeasured; no held-out selection.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('trial'); p.add_argument('out'); a = p.parse_args()
    if Path(a.out).exists(): raise ValueError('Never overwrite an analysis')
    save(a.out, analyze(a.trial))
