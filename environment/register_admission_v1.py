"""Separate APB register admission: shared native mechanism plus new backend checks.

Historical router admission is never accepted as register task admission. Only
the byte-identical native worker/controller/session mechanism can be reused;
the register adapter needs actual public/terminal/heldout execution and every
concrete register contract needs its own audited functional control bank.
"""
import argparse
import json
from pathlib import Path
from environment.register_acceptance_v1 import SOURCES, CHECKS
from environment.register_backend_v1 import ROOT, sha, read, Backend
from environment.register_instance_controls import inputs
from task_families.apb_register_v1.results import simulation_result, compile_result
from task_families.router_v3.toolchain import observed, check as check_toolchain
from scripts.audit_register_controls import audit as audit_controls

NATIVE_FILES = ['environment/native_tools/'+n for n in (
    'acceptance_v5.py', 'worker_v5.py', 'tools_v5.mjs', 'launch_v5.sh',
    'controller.py', 'controller_v2.py', 'controller_v3.py')] + [
    'environment/package_session.py', 'environment/artifact_task/session_v4.py']
RECEIPT_SOURCES = sorted(set(SOURCES + NATIVE_FILES + [
    'environment/register_admission_v1.py', 'scripts/audit_register_controls.py']))


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def source_match(rows, required):
    normalized = {}
    for name, h in rows.items():
        p = Path(name)
        if p.is_absolute():
            p = p.relative_to(ROOT)
        if '..' in p.parts or str(p) in normalized:
            raise ValueError('Invalid source inventory')
        normalized[str(p)] = h
    if set(normalized) != set(required) or any(sha(ROOT/n) != h for n, h in normalized.items()):
        raise ValueError('Incomplete or changed qualification sources')
    return normalized


def qualify(native, standalone, package, config, out):
    native, standalone, package = (Path(p).resolve() for p in (native, standalone, package))
    report = read(standalone/'result.json')
    freeze = read(standalone/'freeze.json')
    if (report.get('schema') != 'register-standalone-acceptance-v1'
            or report.get('passed') is not True or report.get('model_inference_requests') != 0
            or report['freeze_sha256'] != sha(standalone/'freeze.json')
            or freeze['manifest_sha256'] != sha(package/'manifest.json')
            or freeze['config_sha256'] != sha(config)):
        raise ValueError('Actual standalone qualification differs or incomplete')
    if (len(report['checks']) != len(CHECKS) or {x['name'] for x in report['checks']} != CHECKS
            or not all(x['passed'] is True for x in report['checks'])):
        raise ValueError('Missing backend/session acceptance')
    source_match(freeze['sources'], SOURCES)
    source_match(read(native/'sources.json'), NATIVE_FILES)
    nr = read(native/'results.json')
    if ([x['label'] for x in nr] != ['permissions', 'total_budget']
            or not all(x['passed'] is True and x['model_inference_requests'] == 0 for x in nr)
            or [(x['actions'], x['tests'], x['raw_calls'], x['grader_calls']) for x in nr]
                != [(12, 2, 13, 2), (20, 0, 25, 0)]):
        raise ValueError('Native mechanism evidence outside the reused scope')
    backend = Backend(package, freeze['manifest_sha256'], config, freeze['inputs'], freeze['seeds'])
    if backend.input_sha256 != freeze['input_sha256']:
        raise ValueError('Frozen acceptance inputs differ')
    cfg = read(config)
    calls = report['grade_calls']
    if len(calls) != 6 or read(standalone/'grade-calls.json') != calls:
        raise ValueError('Missing actual grading calls')
    expected = [(0, 'public'), (1, 'public'), (1, 'terminal'), (1, 'heldout'), (None, 'public'), (0, 'public')]
    for call, (reward, role) in zip(calls, expected):
        d = standalone/call['out']
        r = read(d/'result.json')
        if (call['reward'], call['phase']) != (reward, role) or call['result_sha256'] != sha(d/'result.json'):
            raise ValueError('Recorded call differs')
        if r['reward'] != reward or r['evaluation_role'] != role or r['source_sha256'] != call['source_sha256']:
            raise ValueError('Actual grading outcome differs')
        if reward is None:
            if r['category'] != 'invalid_submission' or (d/'deployment.json').exists():
                raise ValueError('Invalid source was not rejected before deployment')
            continue
        e = d/'evidence'
        g = e/'grade'
        deployment = read(d/'deployment.json')
        if sha(d/'evidence.tgz') != r['evidence_sha256'] or read(d/'job.json').get('exit_code') != 0:
            raise ValueError('Incomplete executed evidence')
        if (read(e/'request.json') != deployment['request'] or read(e/'input.json') != read(backend.inputs[role])
                or sha(g/'candidate.sv') != r['source_sha256']
                or sha(g/'tb.sv') != sha(package/'verification/tb.sv')):
            raise ValueError('Executed candidate, checker or inputs differ')
        original = read(g/'result.json')
        if any(original[k] != r[k] for k in ('reward', 'category', 'verification_complete', 'source_sha256')):
            raise ValueError('Adapter changed grading semantics')
        if r['category'] == 'compile_error':
            projected = compile_result((g/'compile.log').read_text(), r['compile_exit'])
        else:
            if r['compile_exit'] != 0:
                raise ValueError('Functional check did not compile')
            log = (g/'simulation.log').read_text()
            check_toolchain(observed(log), cfg['toolchain'])
            if read(g/'backend.json')['inputs']['environment_entry'] != cfg['environment_entry_sha256']:
                raise ValueError('Execution environment differs')
            rows = read(e/'input.json')['vectors']
            transfers = sum(x[0] != 2 for x in rows)
            projected = simulation_result(log, r['simulation_exit'], transfers,
                1+sum(x[0] == 2 for x in rows), transfers*backend.contract['wait_cycles'], len(backend.contract['registers']))
        if any(r[k] != projected[k] for k in ('reward', 'category', 'verification_complete')):
            raise ValueError('Outcome not supported by logs')
    failure = read(standalone/'infrastructure-result/result.json')
    if failure['reward'] is not None or failure['category'] != 'infrastructure_error':
        raise ValueError('Missing infrastructure classification check')
    # Evidence is a trusted local record, not a security signature. Bind all
    # actual records so a later omission or replacement cannot inherit it.
    evidence = {str(p): sha(p) for root in (native, standalone)
                for p in sorted(root.rglob('*')) if p.is_file()
                and '__pycache__' not in p.parts}
    receipt = dict(schema='register-runtime-qualification-v1', qualified=True, admitted=False,
        family=backend.task['family'], config_sha256=sha(config), toolchain=cfg['toolchain'],
        environment_entry_sha256=cfg['environment_entry_sha256'],
        sources={n: sha(ROOT/n) for n in RECEIPT_SOURCES}, evidence_files=evidence,
        limits=dict(max_actions=20, max_tests=2, max_requests=20),
        scope='Unchanged native SDK mechanism plus actual finite-register adapter/session acceptance; no inheritance of router task verdicts.',
        limitations=['Trusted locally produced materials only.',
                     'Ephemeral solver work/tmp; shared fixed UID and network namespace. No complete adversarial OS-isolation claim.'])
    write_new(out, receipt)
    return receipt


def runtime_check(path, config):
    r = read(path)
    if r.get('schema') != 'register-runtime-qualification-v1' or r.get('qualified') is not True:
        raise ValueError('Register runtime not qualified')
    source_match(r['sources'], RECEIPT_SOURCES)
    if r['config_sha256'] != sha(config) or not r['evidence_files'] or any(
            not Path(p).is_file() or sha(p) != h for p, h in r['evidence_files'].items()):
        raise ValueError('Runtime configuration or evidence differs')
    return r


def admit(package, evidence, runtime, config, out):
    package, evidence, runtime = (Path(p).resolve() for p in (package, evidence, runtime))
    r = runtime_check(runtime, config)
    c, meta = inputs(package)
    if meta['family'] != r['family']:
        raise ValueError('Task outside qualified runtime domain')
    report = audit_controls(package, evidence)
    cfg = read(config)
    if (read(evidence/'.local/config.json') != {k: cfg[k] for k in ('eda_env_script', 'apb_vip_root')}
            or report['environment_entry_sha256'] != r['environment_entry_sha256']):
        raise ValueError('Control and runtime deployment differ')
    for path in (evidence/'controls').glob('control-*/simulation.log'):
        check_toolchain(observed(path.read_text()), r['toolchain'])
    record = dict(schema='register-layered-admission-v1', admitted=True, task_id=c['task_id'],
        package=str(package), package_manifest_sha256=sha(package/'manifest.json'),
        control_evidence=str(evidence), control_audit=report,
        runtime_qualification=str(runtime), runtime_qualification_sha256=sha(runtime),
        config_sha256=sha(config), admission_implementation_sha256=sha(__file__),
        scope='This concrete contract control bank and source-matched register runtime; each future submission is independently evaluated.')
    write_new(out, record)
    return record


def validate(path, config):
    a = read(path)
    if a.get('schema') != 'register-layered-admission-v1' or a.get('admitted') is not True:
        raise ValueError('No register admission')
    if (a['admission_implementation_sha256'] != sha(__file__) or a['config_sha256'] != sha(config)
            or sha(a['runtime_qualification']) != a['runtime_qualification_sha256']):
        raise ValueError('Admission dependency changed')
    r = runtime_check(a['runtime_qualification'], config)
    c, meta = inputs(a['package'])
    if (c['task_id'] != a['task_id'] or meta['family'] != r['family']
            or sha(Path(a['package'])/'manifest.json') != a['package_manifest_sha256']
            or audit_controls(a['package'], a['control_evidence']) != a['control_audit']):
        raise ValueError('Concrete task evidence differs')
    return a


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest='command', required=True)
    q = s.add_parser('qualify')
    for n in ('native', 'standalone', 'package', 'config', 'out'):
        q.add_argument(n)
    a = s.add_parser('admit')
    for n in ('package', 'evidence', 'runtime', 'config', 'out'):
        a.add_argument(n)
    v = s.add_parser('verify')
    v.add_argument('record'); v.add_argument('config')
    args = vars(p.parse_args()); command = args.pop('command')
    result = validate(args['record'], args['config']) if command == 'verify' else globals()[command](**args)
    print(json.dumps(dict(admitted=result.get('admitted'), qualified=result.get('qualified'), task_id=result.get('task_id'))))
