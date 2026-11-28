"""Real register-backend/session qualification, separately from instance controls.

Reuses the unchanged four-action session and native controller contract. This
is a deterministic engineering check, not a model trial or runtime admission.
"""
import argparse
import json
import time
from pathlib import Path
from environment.package_session import Session
from environment.register_backend_v1 import Backend, EXECUTION_FILES, ROOT, sha, read, save

SOURCES = sorted(set(EXECUTION_FILES + ['environment/'+n for n in (
    'register_acceptance_v1.py', 'register_backend_v1.py', 'register_instance_controls.py',
    'package_session.py', 'artifact_task/session_v4.py')] + ['task_families/router_v3/toolchain.py']))
CHECKS = {
    'initial_functional_rejection', 'reference_public_pass', 'old_feedback_identity',
    'third_test_no_execution', 'forbidden_files', 'submit_same_source',
    'closed_after_submit', 'terminal_requires_stop', 'reference_terminal_pass',
    'reference_heldout_pass', 'private_results_not_feedback', 'source_policy_before_eda',
    'candidate_compile_error', 'environment_not_rtl_failure', 'all_roles_executed',
    'twenty_action_bound', 'recovery_without_regrading'}


def run(package, config, input_plan, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    package = Path(package).resolve()
    plan = read(input_plan)
    backend = Backend(package, sha(package/'manifest.json'), config, plan['inputs'], plan['seeds'])
    reference = package/'fixtures/reference.sv'
    save(out/'freeze.json', dict(schema='register-standalone-freeze-v1',
        sources={n: sha(ROOT/n) for n in SOURCES}, manifest_sha256=backend.manifest_sha256,
        config_sha256=backend.config_sha256, inputs=plan['inputs'], seeds=plan['seeds'],
        input_sha256=backend.input_sha256, reference_sha256=sha(reference),
        max_actions=20, max_tests=2, model_inference_requests=0))
    work = out/'work'
    work.mkdir()
    for name, src in [('spec.md', package/'spec.md'), ('bridge.sv', package/'workspace/bridge.sv')]:
        (work/name).write_bytes(src.read_bytes())
    checks, calls = [], []
    start = time.monotonic()

    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        save(out/'checks.json', checks)
        print(json.dumps(checks[-1]), flush=True)
        if not passed:
            raise RuntimeError('Failed mechanism: '+name)

    def grade(source, dest, phase):
        r = backend.grade(source, dest, phase)
        calls.append(dict(phase=phase, source_sha256=sha(source), out=str(dest.relative_to(out)),
                          reward=r['reward'], category=r['category'], result_sha256=sha(dest/'result.json')))
        save(out/'grade-calls.json', calls)
        return r

    s = Session(backend.task, work, out/'session', grade, 20, 2)
    error = None
    try:
        for name in ('spec.md', 'bridge.sv'):
            s.handle(dict(tool='read', file=name))
        initial = s.handle(dict(tool='test'))
        check('initial_functional_rejection', initial['status']=='FAIL' and calls[-1]['reward']==0)
        s.handle(dict(tool='edit', content=reference.read_text()))
        public = s.handle(dict(tool='test'))
        check('reference_public_pass', public['status']=='PASS' and public['source_sha256']==sha(reference))
        check('old_feedback_identity', initial['source_sha256']!=public['source_sha256']
              and s.trace[2]['observation']['source_sha256']==initial['source_sha256'])
        check('third_test_no_execution', s.handle(dict(tool='test')).get('reason')=='test_budget_exhausted' and len(calls)==2)
        check('forbidden_files', all(s.handle(dict(tool='read', file=f)).get('reason')=='file_not_allowed'
              for f in ('../contract.json', 'fixtures/reference.sv', 'verification/tb.sv', 'policy.json')))
        s.handle(dict(tool='submit'))
        submitted = s.out/'submission/bridge.sv'
        check('submit_same_source', sha(submitted)==sha(reference))
        check('closed_after_submit', s.handle(dict(tool='edit', content='late')).get('reason')=='episode_closed'
              and sha(submitted)==sha(reference))
        trace = json.loads(json.dumps(s.trace))
        try:
            s.finalize(False)
        except ValueError:
            refused = True
        else:
            refused = False
        check('terminal_requires_stop', refused and len(calls)==2)
        terminal = s.finalize(True)
        save(out/'terminal.json', terminal)
        check('reference_terminal_pass', terminal['reward']==1 and terminal['evaluation_role']=='terminal')
        heldout = grade(submitted, out/'heldout', 'heldout')
        save(out/'heldout.json', heldout)
        check('reference_heldout_pass', heldout['reward']==1 and heldout['evaluation_role']=='heldout')
        check('private_results_not_feedback', s.trace==trace and all(
            set(r['observation']) <= {'status','category','source_sha256','remaining_test_calls'}
            for r in s.trace if r['action'].get('tool')=='test' and r['executed']))
        invalid = out/'invalid.sv'
        invalid.write_text('module bridge; initial $finish; endmodule\n')
        r = grade(invalid, out/'invalid-result', 'public')
        check('source_policy_before_eda', r['reward'] is None and r['category']=='invalid_submission'
              and not (out/'invalid-result/deployment.json').exists())
        broken = out/'compile-error.sv'
        broken.write_text(reference.read_text().replace('endmodule', 'not_valid_syntax !\nendmodule'))
        r = grade(broken, out/'compile-result', 'public')
        check('candidate_compile_error', r['reward']==0 and r['category']=='compile_error')
        badcfg = read(config)
        badcfg['eda_env_script']='/nonexistent/pb-acceptance-env.sh'
        save(out/'unavailable-environment.json', badcfg)
        bad = Backend(package, backend.manifest_sha256, out/'unavailable-environment.json', plan['inputs'], plan['seeds'])
        r = bad.grade(reference, out/'infrastructure-result', 'public')
        check('environment_not_rtl_failure', r['reward'] is None and r['category']=='infrastructure_error'
              and not (out/'infrastructure-result/evidence/grade/compile.log').exists())
        check('all_roles_executed', [c['phase'] for c in calls[:4]]==['public','public','terminal','heldout'])
        budget = Session(backend.task, work, out/'budget-session', grade, 20, 2)
        for _ in range(21):
            last = budget.handle(dict(tool='read', file='spec.md'))
        check('twenty_action_bound', budget.actions==20 and last.get('reason')=='episode_closed' and len(calls)==6)
        completed = read(out/'heldout/job.json')
        recovered = backend.collect(out/'heldout')
        check('recovery_without_regrading', recovered==heldout and read(out/'heldout/job.json')==completed)
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)[:200]
    passed = error is None and len(checks)==len(CHECKS) and {x['name'] for x in checks}==CHECKS
    result = dict(schema='register-standalone-acceptance-v1', passed=passed, error=error,
                  runtime_admitted=False, checks=checks, grade_calls=calls,
                  freeze_sha256=sha(out/'freeze.json'), wall_seconds=time.monotonic()-start,
                  model_inference_requests=0)
    save(out/'result.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('package', 'config', 'input_plan', 'out'):
        p.add_argument(name)
    a = p.parse_args()
    r = run(a.package, a.config, a.input_plan, a.out)
    print(json.dumps(r))
    raise SystemExit(0 if r['passed'] else 1)
