"""Compose source-bound qualification layers for trusted router capsules.

Shared evidence qualifies the execution mechanism only. Every concrete capsule
still needs its own full industrial positive/negative controls. This record is
not a substitute for independent grading of any future Agent submission.
"""
import argparse,json,hashlib
from pathlib import Path
from environment.package_backend_v2 import Backend
from environment.environment_identity import match as match_environment
from task_families.router_v2.generate import verify as verify_package
from task_families.router_v3.audit_controls_v2 import audit
from task_families.router_v3.toolchain import check as check_toolchain
ROOT=Path(__file__).resolve().parents[1]
NATIVE_FILES=['environment/native_tools/'+n for n in ('acceptance_v5.py','worker_v5.py','tools_v5.mjs','launch_v5.sh','controller.py','controller_v2.py','controller_v3.py')]+['environment/package_session.py','environment/artifact_task/session_v4.py']
BACKEND_FILES=['environment/'+n for n in ('package_acceptance_v2.py','package_backend.py','package_backend_v2.py','package_inputs.py','package_grade_entry.py','package_session.py')]+['task_families/router_v2/generate.py','task_families/router_v3/toolchain.py']
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
    if m.get('family')!='x2p_three_target_router_v5' or m.get('verifier_revision')!='response-ownership-v1':raise ValueError('Current response-owner verifier required')
    r=read(standalone/'result.json');f=read(standalone/'freeze.json')
    if r.get('schema')!='router-standalone-acceptance-v2' or r.get('passed') is not True or r.get('freeze_sha256')!=sha(standalone/'freeze.json'):raise ValueError('Standalone acceptance incomplete')
    if f['package_manifest_sha256']!=sha(package/'family-manifest.json') or f['config_sha256']!=sha(config):raise ValueError('Acceptance source/config differs')
    if len(r['checks'])!=len(CHECKS) or {c['name'] for c in r['checks']}!=CHECKS or not all(c['passed'] is True for c in r['checks']):raise ValueError('Missing real execution checks')
    sources=source_match(f['sources'],BACKEND_FILES)
    sources.update(source_match(read(native/'sources.json'),NATIVE_FILES))
    nr=read(native/'results.json')
    if [x['label'] for x in nr]!=['permissions','total_budget'] or not all(x['passed'] is True and x['model_inference_requests']==0 for x in nr):raise ValueError('Native mechanism incomplete')
    if [(x['actions'],x['tests'],x['raw_calls'],x['grader_calls']) for x in nr]!=[(12,2,13,2),(20,0,25,0)]:raise ValueError('Unexpected native mechanism scope')
    if len(r['grade_calls'])!=6:raise ValueError('Missing actual standalone grades')
    environment_entries=set()
    expected=[(0,'public'),(1,'public'),(1,'terminal'),(1,'heldout'),(None,'public'),(0,'public')]
    for call,(reward,phase) in zip(r['grade_calls'],expected):
        d=standalone/call['out'];actual=read(d/'result.json')
        if (call['reward'],call['phase'])!=(reward,phase) or actual['reward']!=reward or actual['source_sha256']!=call['source_sha256'] or actual['public']!=(phase=='public'):raise ValueError('Actual grade record differs')
        if reward==1 and actual.get('verification_complete') is not True:raise ValueError('Incomplete positive grade')
        if (d/'runtime.json').exists():environment_entries.add(read(d/'runtime.json')['inputs']['environment_entry'])
    if len(environment_entries)!=1:raise ValueError('Inconsistent observed environment identity')
    cfg=read(config)
    evidence={str(p):sha(p) for root in (native,standalone) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and 'sources' not in p.relative_to(root).parts}
    # Bind the verifier's role/source handling exactly; task-specific generated
    # scenarios and UVM logic are qualified anew in each instance's control layer.
    receipt={'schema':'router-runtime-qualification-v2','qualified':True,'admitted':False,
             'family':m['family'],'execution_adapter':m['execution_adapter'],'qualification_revision':2,'verifier_revision':'response-ownership-v1',
             'campaign_sha256':sha(package/'verifier/task002/campaign.py'),'sources':sources,
             'limits':{'max_actions':20,'max_tests':2,'max_requests':20},'toolchain':cfg['toolchain'],
             'config_sha256':sha(config),'evidence_files':evidence,'environment_entry_sha256':environment_entries.pop(),
             'scope':'Native SDK permissions/budgets plus representative standalone grading. No reuse of task functional verdicts or future terminal rewards.',
             'limitations':['Trusted locally generated capsules only; manifest integrity is not third-party code security.','Ephemeral solver work/tmp, fixed shared UID and shared network namespace; no claim of complete adversarial OS isolation.']}
    write_new(out,receipt);return receipt

def runtime_check(path,config):
    r=read(path)
    if r.get('schema')!='router-runtime-qualification-v2' or r.get('qualified') is not True:raise ValueError('Runtime not qualified')
    source_match(r['sources'],set(NATIVE_FILES+BACKEND_FILES))
    if sha(config)!=r['config_sha256']:raise ValueError('Runtime configuration differs')
    if not r['evidence_files'] or any(not Path(p).is_file() or sha(p)!=h for p,h in r['evidence_files'].items()):raise ValueError('Runtime evidence changed')
    return r

def admit(package,evidence,runtime,config,out,reconciliation=None):
    package=Path(package).resolve();evidence=Path(evidence).resolve();runtime=Path(runtime).resolve();m=verify_package(package);r=runtime_check(runtime,config)
    if any(m.get(k)!=r[k] for k in ('family','execution_adapter','qualification_revision','verifier_revision')):raise ValueError('Package outside qualified runtime domain')
    if sha(package/'verifier/task002/campaign.py')!=r['campaign_sha256']:raise ValueError('Campaign not source-matched')
    report=audit(package,evidence)
    if report['control_layer_qualified'] is not True:raise ValueError('Instance controls not qualified')
    for identity in report['runtime_identities']:check_toolchain(identity,r['toolchain'])
    environment_binding=match_environment(config,report['environment_entry_sha256'],r['environment_entry_sha256'],reconciliation)
    record={'schema':'router-layered-admission-v3','admitted':True,'task_id':m['task_id'],
            'package':str(package),'package_manifest_sha256':sha(package/'family-manifest.json'),
            'control_evidence':str(evidence),'control_audit':report,'runtime_qualification':str(runtime),
            'runtime_qualification_sha256':sha(runtime),'config_sha256':sha(config),
            'admission_implementation_sha256':sha(Path(__file__)),'environment_identity_implementation_sha256':sha(ROOT/'environment/environment_identity.py'),'environment_binding':environment_binding,
            'scope':'Concrete generated contract controls + source-matched shared interaction and standalone grading. Each Agent submission is independently recompiled and evaluated.'}
    write_new(out,record);return record

def validate(path,config):
    a=read(path)
    if a.get('schema')!='router-layered-admission-v3' or a.get('admitted') is not True:raise ValueError('No admission')
    if sha(Path(__file__))!=a['admission_implementation_sha256']:raise ValueError('Admission implementation changed')
    p=Path(a['package']);m=verify_package(p);r=runtime_check(a['runtime_qualification'],config)
    if sha(p/'family-manifest.json')!=a['package_manifest_sha256'] or sha(a['runtime_qualification'])!=a['runtime_qualification_sha256']:raise ValueError('Admission dependency changed')
    if m['task_id']!=a['task_id'] or any(m.get(k)!=r[k] for k in ('family','execution_adapter','qualification_revision','verifier_revision')) or sha(p/'verifier/task002/campaign.py')!=r['campaign_sha256']:raise ValueError('Admission domain changed')
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
