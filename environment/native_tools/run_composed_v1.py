"""Native rollout of a source-matched admitted capsule, without Task-ID dispatch.

This new execution profile preserves historical runners. Public tests use the
current candidate; terminal/held-out grading starts only after solver shutdown.
"""
import argparse,getpass,json,os,queue,shlex,subprocess,threading,time,uuid
from pathlib import Path
from environment.package_session import Session
from environment.composed_backend_v1 import Backend
from environment.composed_admission_v1 import validate as validate_admission, NATIVE_FILES, BACKEND_FILES, AUDIT_FILES
from environment.artifact_task.session_v4 import sha,save
from .controller_v3 import Controller,prompt as previous_prompt
from .audit import audit
ROOT=Path(__file__).resolve().parents[2]
VERSION='native-composed-package-rollout-v1'

def prompt(filename,actions=20,tests=2):
    return previous_prompt(filename,actions,tests)+' To finish, call submit. A prose answer is not a submission.'

def required_sources():
    return set(NATIVE_FILES+BACKEND_FILES+AUDIT_FILES+[
        'environment/native_tools/run_composed_v1.py','environment/native_tools/audit.py',
        'environment/native_tools/composed_batch_v1.py','task_families/production_lock.py'])


def unchanged(plan):
    rows=plan.get('source_files',{})
    return set(rows)==required_sources() and all((ROOT/f).is_file() and sha(ROOT/f)==h for f,h in rows.items())


def run(planfile,trial_id,out,sudo_password=None):
    planfile=Path(planfile);plan=json.loads(planfile.read_text());out=Path(out).resolve()
    if not unchanged(plan):raise ValueError('Frozen source mismatch or incomplete dependency set')
    if plan.get('schema')!='native-composed-package-study-v1':raise ValueError('Unsupported study')
    if not 1<=len(plan['trials'])<=plan['max_trials']<=6 or len({t['trial_id'] for t in plan['trials']})!=len(plan['trials']):raise ValueError('Trial bound or identity error')
    if not 1<=plan['max_output_tokens']<=8192 or not 0<plan['max_solver_seconds']<=7200:raise ValueError('Invalid resource bound')
    if plan.get('reasoning_effort')!='off':raise ValueError('Installed worker uses reasoning off')
    if plan.get('max_terminal_grader_seconds')!=2400 or plan.get('max_heldout_grader_seconds')!=2400:raise ValueError('Verifier subprocess bounds differ')
    row=next(x for x in plan['trials'] if x['trial_id']==trial_id)
    if not (plan['max_actions']==20 and plan['max_requests']==20 and plan['max_tests']==2):raise ValueError('Unaccepted native condition')
    config_path=Path(plan['config']).resolve()
    if sha(config_path)!=plan['config_sha256']:raise ValueError('Execution configuration differs')
    if sha(row['admission'])!=row['admission_sha256']:raise ValueError('Admission record differs')
    admission=validate_admission(row['admission'],config_path)
    if admission['task_id']!=row['task_id']:raise ValueError('Task identity differs')
    backend=Backend(admission['package'],admission['package_manifest_sha256'],config_path,row['inputs'],row['seeds'])
    if backend.input_sha256!=row['input_sha256']:raise ValueError('Input identity differs')
    runtime_qualification=json.loads(Path(admission['runtime_qualification']).read_text())
    def grade(source,dest,phase):
        r=backend.grade(source,dest,phase)
        evidence=Path(dest)/'runtime.json'
        if evidence.exists() and json.loads(evidence.read_text())['inputs']['environment_entry']!=runtime_qualification['environment_entry_sha256']:
            raise RuntimeError('Execution environment changed')
        return r
    def anchor(source,dest):return grade(source,dest,'heldout')
    taskdir=backend.taskdir;task=backend.task
    if not os.environ.get('DEEPSEEK_API_KEY'):raise ValueError('API credential unavailable')
    initial=prompt(task['deliverable'],plan['max_actions'],plan['max_tests'])
    if initial!=plan['prompts'][task['deliverable']]:raise ValueError('Prompt mismatch')
    out.mkdir(parents=True,exist_ok=False);save(out/'freeze.json',plan)
    work=out/'work';work.mkdir()
    for name,src in [('spec.md',taskdir/'spec.md'),(task['deliverable'],taskdir/'workspace'/task['deliverable'])]:
        (work/name).write_bytes(src.read_bytes())
    s=Session(task,work,out/'session',grade,plan['max_actions'],plan['max_tests']);controller=Controller(s,plan['max_requests'])
    config=json.loads(config_path.read_text())
    ssh=['ssh','-F',config['ssh_config'],config['host']]
    # Preflight every independent trial, not just the surrounding batch.
    resource_code="import json,shutil;from pathlib import Path;busy=[]\nfor p in Path('/proc').glob('[0-9]*/comm'):\n try:\n  if p.read_text().strip() in ('simv','vcs','vcs1','dc_shell','fm_shell'):busy.append(p.parent.name)\n except FileNotFoundError:pass\nprint(json.dumps({'free_bytes':shutil.disk_usage("+repr(config['remote_root'])+").free,'busy':busy}))"
    resource=subprocess.run(ssh+['python3 -c '+shlex.quote(resource_code)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    if resource.returncode:raise RuntimeError('Resource preflight failed')
    resource=json.loads(resource.stdout);save(out/'resource-before.json',resource)
    if resource['free_bytes']<4*1024**3 or resource['busy']:raise RuntimeError('Resource bound prevents model launch')
    command='source '+shlex.quote(config['eda_env_script'])+' || exit 125; sha256sum '+shlex.quote(config['eda_env_script'])
    probe=subprocess.run(ssh+['bash -lc '+shlex.quote(command)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         env={k:os.environ[k] for k in ('PATH','HOME','LANG','SSH_AUTH_SOCK') if k in os.environ},timeout=30)
    import hashlib
    if probe.returncode or hashlib.sha256(probe.stdout).hexdigest()!=runtime_qualification['environment_entry_sha256']:
        raise RuntimeError('Qualified environment identity changed before model startup')
    installed={
      '/opt/protocolbridge-runtime/opt/pb/native-tools-v5/worker_v5.py':sha(ROOT/'environment/native_tools/worker_v5.py'),
      '/opt/protocolbridge-runtime/opt/pb/native-tools-v5/tools_v5.mjs':sha(ROOT/'environment/native_tools/tools_v5.mjs'),
      '/usr/local/sbin/pb-native-sandbox-v5':sha(ROOT/'environment/native_tools/launch_v5.sh')}
    code='import sys,json,hashlib; from pathlib import Path; d=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in d.items())'
    subprocess.run(ssh+['python3 -c '+shlex.quote(code)],input=json.dumps(installed)+'\n',text=True,capture_output=True,check=True,timeout=30)
    sudo='sudo -n ' if sudo_password is None else 'sudo -S -p "" '
    prefix='' if sudo_password is None else sudo_password+'\n'
    name='native-'+uuid.uuid4().hex
    command=ssh+[sudo+'/usr/local/sbin/pb-native-sandbox-v5 /work/'+name]
    probe=subprocess.run(command,input=prefix+json.dumps({'probe_only':True,'api_key':'startup-only-no-inference','filename':s.filename})+'\n',text=True,capture_output=True,timeout=90)
    records=[json.loads(line) for line in probe.stdout.splitlines() if line.startswith('{')]
    checks=next((r['checks'] for r in records if r.get('kind')=='isolation_probe'),{})
    ready=next((r for r in records if r.get('kind')=='ready'),{})
    if (probe.returncode or checks.get('uid')!=1101 or checks.get('pid')!=1 or checks.get('no_new_privs')!='1'
        or checks.get('cap_eff')!='0000000000000000' or not all(checks.get(k) is True for k in ('tmp_canary_absent','host_project_absent','host_evaluator_absent','worker_write_denied','old_worker_write_denied','chroot_denied'))
        or ready.get('tools')!=['edit','read','submit','test'] or ready.get('work_siblings')!=[name]
        or not records[-1].get('runtime_closed')):raise RuntimeError('Isolation startup acceptance failed')
    save(out/'isolation.json',{'records':records,'installed_hashes':list(installed.values()),'network_namespace_shared':True})
    messages=queue.Queue();events=[];p=None;stopped=False;failure=None;run_error=None;start=time.monotonic()
    with (out/'worker-stderr.log').open('w') as err:
      try:
        p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
        def reader():
            for line in p.stdout:messages.put(line)
            messages.put(None)
        threading.Thread(target=reader,daemon=True).start()
        bootstrap={'api_key':os.environ['DEEPSEEK_API_KEY'],'filename':s.filename,'prompt':initial,'model':plan['model'],
          'max_tokens':plan['max_output_tokens'],'max_model_requests':plan['max_requests'],'max_model_responses':plan['max_requests'],'timeout_seconds':180}
        save(out/'started.json',{'plan_sha256':sha(planfile),'trial_id':trial_id,'phase':'before_model_bootstrap_delivery'})
        p.stdin.write(prefix+json.dumps(bootstrap)+'\n');p.stdin.flush()
        while True:
            remaining=plan['max_solver_seconds']-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError('Trial wall budget')
            try:line=messages.get(timeout=min(30,remaining))
            except queue.Empty:
                print(json.dumps({'trial':trial_id,'status':'running','actions':s.actions,'elapsed_seconds':round(time.monotonic()-start)}),flush=True);continue
            if line is None:break
            record=json.loads(line);events.append(record);save(out/'events.json',events)
            kind=record.get('kind')
            if kind in ('tool_request','model_request'):
                if not unchanged(plan):raise RuntimeError('Frozen source changed')
                backend.check()
                reply=controller.dispatch(record)
                if reply['observation'].get('status')=='ENV_ERROR':
                    failure='public_environment_error';s.done=True;reply['stop']=True
                p.stdin.write(json.dumps(reply)+'\n');p.stdin.flush()
                if kind=='tool_request':
                    controller.returned(record['call_id'])
                    print(json.dumps({'trial':trial_id,'action':s.actions,'tool':record['name'],'status':reply['observation'].get('status','READ')}),flush=True)
            elif kind=='notification':controller.response_received(record['notification'].get('payload',{}).get('event',{}))
            elif kind=='run_error':run_error=record['category']
            elif kind in ('worker_error','transport_error'):raise RuntimeError(kind)
            elif kind=='ready':
                if record['tools']!=['edit','read','submit','test'] or record['uid']!=1101 or record['pid']!=1 or record['work_siblings']!=[name]:raise RuntimeError('Runtime surface differs')
            elif kind=='stopped':stopped=record.get('runtime_closed') is True and not record['transport_errors']
        p.wait(timeout=15)
        if p.returncode or not stopped:raise RuntimeError('Unconfirmed solver shutdown')
        if run_error and not any(not r['allowed'] for r in controller.requests):raise RuntimeError('Unexpected model/runtime failure')
      except Exception as e:failure=type(e).__name__ if failure is None else failure
      finally:
        if p is not None and p.poll() is None:
            p.terminate()
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
    if not unchanged(plan):failure='source_changed'
    if not failure:
        try:validate_admission(row['admission'],config_path);backend.check()
        except Exception:failure='admission_or_input_changed'
    if stopped and not failure:
        try:save(out/'audit.json',audit(events,controller.calls,controller.requests,s.submitted))
        except Exception as e:failure='audit_'+type(e).__name__
    if stopped and not failure:
        try:terminal=s.finalize(True)
        except Exception as e:terminal={'reward':None,'category':'infrastructure_error','exception_type':type(e).__name__}
    else:terminal={'reward':None,'category':'infrastructure_error','exception_type':failure}
    save(out/'terminal.json',terminal)
    evaluation=None
    if stopped and not failure and s.submitted:
        try:evaluation=anchor(s.out/'submission'/s.filename,out/'reserved-evaluation')
        except Exception as e:evaluation={'reward':None,'category':'infrastructure_error','exception_type':type(e).__name__}
    save(out/'reserved-evaluation.json',evaluation)
    result={'schema':VERSION,'trial_id':trial_id,'task_id':task['task_id'],'plan_sha256':sha(planfile),'model':plan['model'],
      'terminal':terminal,'reserved_evaluation':evaluation,'submitted':s.submitted,'actions':s.actions,'edits':s.edits,'public_test_calls':s.tests,
      'solver_stop_confirmed':stopped,'error':failure,'run_error':run_error,'frozen_sources_unchanged':unchanged(plan),
      'model_requests_allowed':sum(r['allowed'] for r in controller.requests),
      'model_responses':sum(r['response_received'] for r in controller.requests),
      'reported_tokens':sum((r.get('usage') or {}).get('totalTokens',0) for r in controller.requests),
      'wall_seconds':round(time.monotonic()-start,4),'package_manifest_sha256':backend.manifest_sha256,
      'admission_sha256':sha(row['admission']),'input_sha256':backend.input_sha256,'input_seeds':backend.seeds,
      'heldout_not_training_reward':True}
    save(out/'result.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan');parser.add_argument('trial');parser.add_argument('out');parser.add_argument('--ask-sudo-password',action='store_true');args=parser.parse_args()
    password=getpass.getpass('Temporary deployment password: ') if args.ask_sudo_password else None
    print(json.dumps(run(args.plan,args.trial,args.out,password),indent=2))
