"""Compose source-bound qualification layers for trusted route/queue composition capsules.

Shared evidence qualifies the execution mechanism only. Every concrete capsule
still needs its own full industrial positive/negative controls. This record is
not a substitute for independent grading of any future Agent submission.
"""
import argparse,json,hashlib,os,subprocess,sys
from pathlib import Path
from environment.composed_backend_v1 import Backend
from environment.environment_identity import match as match_environment
from task_families.package import verify as verify_package
from environment.instance_control_audit import audit
from scripts.composed_grade_audit import audit as audit_grade
from task_families.router_v3.toolchain import check as check_toolchain
ROOT=Path(__file__).resolve().parents[1]
NATIVE_FILES=['environment/native_tools/'+n for n in ('acceptance_v5.py','worker_v5.py','tools_v5.mjs','launch_v5.sh','controller.py','controller_v2.py','controller_v3.py')]+['environment/package_session.py','environment/artifact_task/session_v4.py']
from environment.composed_acceptance_v1 import SOURCES as BACKEND_FILES
AUDIT_FILES=['environment/composed_admission_v1.py','environment/instance_control_audit.py','environment/control_bank.py','environment/environment_identity.py','scripts/composed_grade_audit.py']
CHECKS={'initial_functional_rejection','standalone_reference_public','old_feedback_identity','third_test_no_grading','submit_same_source','closed_after_submit','terminal_requires_stop','standalone_reference_terminal','standalone_reference_heldout','private_results_not_in_feedback','source_policy_invalid','compile_error_is_not_infrastructure','infrastructure_is_not_rtl_failure','grading_roles'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n')

def normalize_sources(rows):
    normalized={}
    for name,h in rows.items():
        p=Path(name)
        if p.is_absolute():
            try:p=p.relative_to(ROOT)
            except ValueError:raise ValueError('Evidence refers to a different checkout')
        if '..' in p.parts or str(p) in normalized:raise ValueError('Invalid source inventory')
        normalized[str(p)]=h
    return normalized

def source_match(rows,required):
    rows=normalize_sources(rows)
    if set(rows)!=set(required):raise ValueError('Incomplete or different qualification dependency set')
    if any(not (ROOT/f).is_file() or sha(ROOT/f)!=h for f,h in rows.items()):raise ValueError('Qualification source mismatch')
    return rows

def qualify(native,standalone,package,config,out):
    native=Path(native).resolve();standalone=Path(standalone).resolve();package=Path(package).resolve()
    m=verify_package(package)
    if m.get('family')!='routed_retirement_windows_v2' or m.get('execution_adapter')!='composed-source-environment-v1' or m.get('control_revision')!='reset-last-assignment-v1':raise ValueError('Current qualified composed verifier required')
    r=read(standalone/'result.json');f=read(standalone/'freeze.json')
    if r.get('schema')!='composed-standalone-acceptance-v1' or r.get('passed') is not True or r.get('freeze_sha256')!=sha(standalone/'freeze.json'):raise ValueError('Standalone acceptance incomplete')
    if f['package_manifest_sha256']!=sha(package/'family-manifest.json') or f['config_sha256']!=sha(config):raise ValueError('Acceptance source/config differs')
    if len(r['checks'])!=len(CHECKS) or {c['name'] for c in r['checks']}!=CHECKS or not all(c['passed'] is True for c in r['checks']):raise ValueError('Missing real execution checks')
    sources=source_match(f['sources'],BACKEND_FILES)
    sources.update(source_match(read(native/'sources.json'),NATIVE_FILES))
    nr=read(native/'results.json')
    if [x['label'] for x in nr]!=['permissions','total_budget'] or not all(x['passed'] is True and x['model_inference_requests']==0 for x in nr):raise ValueError('Native mechanism incomplete')
    if [(x['actions'],x['tests'],x['raw_calls'],x['grader_calls']) for x in nr]!=[(12,2,13,2),(20,0,25,0)]:raise ValueError('Unexpected native mechanism scope')
    if read(standalone/'grade-calls.json')!=r['grade_calls']:raise ValueError('Recorded call inventory differs')
    if (f.get('model_requests'),f.get('max_actions'),f.get('max_tests'))!=(0,20,2):raise ValueError('Acceptance model/action/test scope differs')
    if len(r['grade_calls'])!=6:raise ValueError('Missing actual standalone grades')
    env={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
    complete=json.loads(subprocess.check_output([sys.executable,str(ROOT/'environment/composed_inputs_v1.py'),json.dumps(f['input_seeds'])],cwd=str(package),env=env,timeout=60))
    environment_entries=set()
    expected=[(0,'public'),(1,'public'),(1,'terminal'),(1,'heldout'),(None,'public'),(0,'public')]
    for call,(reward,phase) in zip(r['grade_calls'],expected):
        d=standalone/call['out'];actual=read(d/'result.json')
        if (call['reward'],call['phase'])!=(reward,phase) or actual['reward']!=reward or actual['source_sha256']!=call['source_sha256'] or actual['public']!=(phase=='public'):raise ValueError('Actual grade record differs')
        audit_grade(package,d,config,complete[phase],phase,call['source_sha256'])
        if reward==1 and actual.get('verification_complete') is not True:raise ValueError('Incomplete positive grade')
        if (d/'runtime.json').exists():environment_entries.add(read(d/'runtime.json')['inputs']['environment_entry'])
    if len(environment_entries)!=1:raise ValueError('Inconsistent observed environment identity')
    cfg=read(config)
    sources.update({n:sha(ROOT/n) for n in AUDIT_FILES})
    evidence={str(p):sha(p) for root in (native,standalone) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and 'sources' not in p.relative_to(root).parts}
    # Bind the verifier's role/source handling exactly; task-specific generated
    # scenarios and UVM logic are qualified anew in each instance's control layer.
    receipt={'schema':'composed-runtime-qualification-v1','qualified':True,'admitted':False,
             'family':m['family'],'execution_adapter':m['execution_adapter'],'control_revision':m['control_revision'],
             'campaign_sha256':sha(package/'verifier/task003/campaign.py'),'sources':sources,
             'limits':{'max_actions':20,'max_tests':2,'max_requests':20},'toolchain':cfg['toolchain'],
             'config_sha256':sha(config),'evidence_files':evidence,'environment_entry_sha256':environment_entries.pop(),
             'scope':'Native SDK permissions/budgets plus representative standalone grading. No reuse of task functional verdicts or future terminal rewards.',
             'limitations':['Trusted locally generated capsules only; manifest integrity is not third-party code security.','Ephemeral solver work/tmp, fixed shared UID and shared network namespace; no claim of complete adversarial OS isolation.']}
    write_new(out,receipt);return receipt

def runtime_check(path,config):
    r=read(path)
    if r.get('schema')!='composed-runtime-qualification-v1' or r.get('qualified') is not True:raise ValueError('Runtime not qualified')
    source_match(r['sources'],set(NATIVE_FILES+BACKEND_FILES+AUDIT_FILES))
    if sha(config)!=r['config_sha256']:raise ValueError('Runtime configuration differs')
    if not r['evidence_files'] or any(not Path(p).is_file() or sha(p)!=h for p,h in r['evidence_files'].items()):raise ValueError('Runtime evidence changed')
    return r

def admit(package,evidence,runtime,config,out,reconciliation=None):
    package=Path(package).resolve();evidence=Path(evidence).resolve();runtime=Path(runtime).resolve();m=verify_package(package);r=runtime_check(runtime,config)
    if any(m.get(k)!=r[k] for k in ('family','execution_adapter','control_revision')):raise ValueError('Package outside qualified runtime domain')
    if sha(package/'verifier/task003/campaign.py')!=r['campaign_sha256']:raise ValueError('Campaign not source-matched')
    report=audit(package,evidence)
    if report['control_layer_qualified'] is not True:raise ValueError('Instance controls not qualified')
    for identity in report['runtime_identities']:check_toolchain(identity,r['toolchain'])
    environment_binding=match_environment(config,report['environment_entry_sha256'],r['environment_entry_sha256'],reconciliation)
    record={'schema':'composed-layered-admission-v1','admitted':True,'task_id':m['task_id'],
            'package':str(package),'package_manifest_sha256':sha(package/'family-manifest.json'),
            'control_evidence':str(evidence),'control_audit':report,'runtime_qualification':str(runtime),
            'runtime_qualification_sha256':sha(runtime),'config_sha256':sha(config),
            'admission_implementation_sha256':sha(Path(__file__)),'environment_identity_implementation_sha256':sha(ROOT/'environment/environment_identity.py'),'environment_binding':environment_binding,
            'scope':'Concrete generated contract controls + source-matched shared interaction and standalone grading. Each Agent submission is independently recompiled and evaluated.'}
    write_new(out,record);return record

def validate(path,config):
    a=read(path)
    if a.get('schema')!='composed-layered-admission-v1' or a.get('admitted') is not True:raise ValueError('No admission')
    if sha(config)!=a['config_sha256']:raise ValueError('Admission configuration changed')
    if sha(Path(__file__))!=a['admission_implementation_sha256']:raise ValueError('Admission implementation changed')
    p=Path(a['package']);m=verify_package(p);r=runtime_check(a['runtime_qualification'],config)
    if sha(p/'family-manifest.json')!=a['package_manifest_sha256'] or sha(a['runtime_qualification'])!=a['runtime_qualification_sha256']:raise ValueError('Admission dependency changed')
    if m['task_id']!=a['task_id'] or any(m.get(k)!=r[k] for k in ('family','execution_adapter','control_revision')) or sha(p/'verifier/task003/campaign.py')!=r['campaign_sha256']:raise ValueError('Admission domain changed')
    if audit(p,a['control_evidence'])!=a['control_audit']:raise ValueError('Instance evidence changed')
    if sha(ROOT/'environment/environment_identity.py')!=a['environment_identity_implementation_sha256']:raise ValueError('Environment identity implementation changed')
    binding=match_environment(config,a['control_audit']['environment_entry_sha256'],r['environment_entry_sha256'],a['environment_binding'].get('proof'))
    if binding!=a['environment_binding']:raise ValueError('Environment reconciliation evidence changed')
    return a

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('qualify');q.add_argument('native');q.add_argument('standalone');q.add_argument('package');q.add_argument('config');q.add_argument('out')
    q=s.add_parser('admit');q.add_argument('package');q.add_argument('evidence');q.add_argument('runtime');q.add_argument('config');q.add_argument('out');q.add_argument('--reconciliation')
    q=s.add_parser('verify');q.add_argument('record');q.add_argument('config')
    a=vars(p.parse_args());cmd=a.pop('command');r=(validate(a['record'],a['config']) if cmd=='verify' else globals()[cmd](**a));print(json.dumps({'task_id':r.get('task_id'),'qualified':r.get('qualified'),'admitted':r['admitted']}))
