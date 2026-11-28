"""Bounded native rollout; unchanged admitted artifact graders run only after exit."""
import argparse,getpass,json,os,queue,shlex,subprocess,threading,time,uuid
from pathlib import Path
from environment.artifact_task.session_v4 import Session,sha,save
from environment.artifact_task.dispatch_v11 import graders
from .controller_v3 import Controller,prompt as previous_prompt
from .audit import audit
ROOT=Path(__file__).resolve().parents[2]
VERSION='native-artifact-rollout-v5'

def prompt(filename,actions=20,tests=4):
    return previous_prompt(filename,actions,tests)+' To finish, call submit. A prose answer is not a submission.'

def unchanged(plan):
    return all((ROOT/f).is_file() and sha(ROOT/f)==h for f,h in plan['source_files'].items())

def run(planfile,trial_id,out,sudo_password=None):
    planfile=Path(planfile);plan=json.loads(planfile.read_text());out=Path(out).resolve()
    if not unchanged(plan):raise ValueError('Frozen source mismatch')
    row=next(x for x in plan['trials'] if x['trial_id']==trial_id)
    if not (plan['max_actions']==20 and plan['max_requests']==20 and plan['max_tests']==4):raise ValueError('Unaccepted native condition')
    grade,anchor=graders(row['task_id'])
    taskdir=ROOT/'tasks'/row['task_id'];task=json.loads((taskdir/'task.json').read_text())
    initial=prompt(task['deliverable'],plan['max_actions'],plan['max_tests'])
    if initial!=plan['prompts'][task['deliverable']]:raise ValueError('Prompt mismatch')
    out.mkdir(parents=True,exist_ok=False);save(out/'freeze.json',plan)
    work=out/'work';work.mkdir()
    for name,src in [('spec.md',taskdir/'spec.md'),(task['deliverable'],taskdir/'workspace'/task['deliverable'])]:
        (work/name).write_bytes(src.read_bytes())
    s=Session(task,work,out/'session',grade,plan['max_actions'],plan['max_tests']);controller=Controller(s,plan['max_requests'])
    config=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    ssh=['ssh','-F',config['ssh_config'],config['host']]
    installed={
      '/opt/protocolbridge-runtime/opt/pb/native-tools-v3/worker_v3.py':sha(ROOT/'environment/native_tools/worker_v3.py'),
      '/opt/protocolbridge-runtime/opt/pb/native-tools-v3/tools_v3.mjs':sha(ROOT/'environment/native_tools/tools_v3.mjs'),
      '/usr/local/sbin/pb-native-sandbox-v3':sha(ROOT/'environment/native_tools/launch_v3.sh')}
    code='import sys,json,hashlib; from pathlib import Path; d=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in d.items())'
    subprocess.run(ssh+['python3 -c '+shlex.quote(code)],input=json.dumps(installed)+'\n',text=True,capture_output=True,check=True,timeout=30)
    sudo='sudo -n ' if sudo_password is None else 'sudo -S -p "" '
    prefix='' if sudo_password is None else sudo_password+'\n'
    name='native-'+uuid.uuid4().hex
    command=ssh+[sudo+'/usr/local/sbin/pb-native-sandbox-v3 /work/'+name]
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
        p.stdin.write(prefix+json.dumps(bootstrap)+'\n');p.stdin.flush()
        save(out/'started.json',{'plan_sha256':sha(planfile),'trial_id':trial_id})
        while True:
            remaining=plan['max_trial_seconds']-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError('Trial wall budget')
            try:line=messages.get(timeout=min(30,remaining))
            except queue.Empty:
                print(json.dumps({'trial':trial_id,'status':'running','actions':s.actions,'elapsed_seconds':round(time.monotonic()-start)}),flush=True);continue
            if line is None:break
            record=json.loads(line);events.append(record);save(out/'events.json',events)
            kind=record.get('kind')
            if kind in ('tool_request','model_request'):
                if not unchanged(plan):raise RuntimeError('Frozen source changed')
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
      'wall_seconds':round(time.monotonic()-start,4)}
    save(out/'result.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan');parser.add_argument('trial');parser.add_argument('out');parser.add_argument('--ask-sudo-password',action='store_true');args=parser.parse_args()
    password=getpass.getpass('Temporary deployment password: ') if args.ask_sudo_password else None
    print(json.dumps(run(args.plan,args.trial,args.out,password),indent=2))
