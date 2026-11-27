"""Trusted local controller; the existing isolated remote DSH worker samples actions.

The worker has no direct filesystem/tools. Every visible observation is recorded
before its next request, and terminal checking starts only after worker exit.
"""
import argparse,json,os,select,shlex,subprocess,time,uuid
from pathlib import Path
from environment.policy import parse_action
from .session_v2 import Session,sha,save,prompt

ROOT=Path(__file__).resolve().parents[2]
VERSION='artifact-rollout-v3'

def runtime(cfg,out):
    ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
    files={'/opt/protocolbridge-runtime/opt/pb/utm_worker.py':sha(ROOT/'environment/utm_worker.py'),
           '/usr/local/sbin/pb-sandbox':sha(ROOT/'environment/utm_sandbox.sh')}
    code='import json,hashlib,sys; from pathlib import Path; d=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in d.items())'
    subprocess.run(ssh+['python3 -c '+shlex.quote(code)],input=json.dumps(files)+'\n',text=True,capture_output=True,check=True,timeout=30)
    name='trial-'+uuid.uuid4().hex
    subprocess.run(ssh+['sudo -n install -d -o 1101 -g 1000 -m 0770 /opt/protocolbridge-runtime/work/'+name],capture_output=True,check=True,timeout=30)
    command='sudo -n /usr/local/sbin/pb-sandbox /work/'+name
    r=subprocess.run(ssh+[command],input='{"probe_only":true}\n',text=True,capture_output=True,check=True,timeout=30)
    p=json.loads(r.stdout)['isolation_probe']
    expected={'uid':1101,'pid':1,'host_home_visible':False,'host_verifier_visible':False,'no_new_privs':'1','effective_capabilities':'0000000000000000','chroot_escape_denied':True,'worker_write_denied':True}
    if p!=expected:raise RuntimeError('Isolation probe mismatch')
    save(out/'isolation.json',{'checks':p,'runtime_hashes':list(files.values())})
    save(out/'deployment.json',{'worker_directory':name})
    return ssh+[command]

def unchanged(plan):
    return all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in plan['source_files'].items())

def run(planfile,trial_id,out):
    planfile=Path(planfile);plan=json.loads(planfile.read_text());out=Path(out).resolve()
    row=next(x for x in plan['trials'] if x['trial_id']==trial_id)
    if not unchanged(plan):raise RuntimeError('Frozen source differs')
    if plan['max_actions']!=20 or not 0<plan['max_tests']<20:raise ValueError('Invalid budgets')
    out.mkdir(parents=True,exist_ok=False);save(out/'freeze.json',plan)
    taskdir=ROOT/'tasks'/row['task_id'];task=json.loads((taskdir/'task.json').read_text())
    work=out/'work';work.mkdir()
    (work/'spec.md').write_bytes((taskdir/'spec.md').read_bytes())
    (work/task['deliverable']).write_bytes((taskdir/'workspace'/task['deliverable']).read_bytes())
    from .dispatch_v2 import graders
    grade,anchor=graders(row['task_id'])
    s=Session(task,work,out/'session',grade,plan['max_actions'],plan['max_tests'])
    cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    initial=prompt(task['deliverable'],plan['max_actions'],plan['max_tests'])
    expected_prompt=plan.get('prompts',{}).get(task['deliverable'],plan.get('prompt'))
    if initial!=expected_prompt:raise ValueError('Prompt differs')
    process=None;stopped=False;error=None;requests=[];start=time.monotonic()
    stderr=(out/'worker-stderr.log').open('w')
    try:
        command=runtime(cfg,out)
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1)
        def send(obj):process.stdin.write(json.dumps(obj)+'\n');process.stdin.flush()
        send({'api_key':os.environ['DEEPSEEK_API_KEY'],'model':plan['model']})
        next_prompt=initial
        while not s.done:
            if time.monotonic()-start>plan['max_trial_seconds']:raise TimeoutError('Trial time budget')
            if not unchanged(plan):raise RuntimeError('Frozen source changed')
            sent={'prompt':next_prompt};t=time.monotonic();send(sent)
            # Successful transport is distinct from a completed model response.
            request={'index':s.actions+1,'input':sent,'response_received':False}
            requests.append(request);save(out/'requests.json',requests)
            if not select.select([process.stdout],[],[],240)[0]:raise TimeoutError('Worker response timeout')
            line=process.stdout.readline()
            if not line:raise RuntimeError('Worker stopped early')
            message=json.loads(line)
            request['seconds']=round(time.monotonic()-t,4)
            request['response_received']='response' in message;save(out/'requests.json',requests)
            save(out/('harness-%02d.json'%s.actions),message)
            if 'response' not in message:raise RuntimeError('Worker failed')
            if s.trace:
                s.trace[-1]['observation_delivered']=True;save(s.out/'trace.json',s.trace)
            text=message['response']['final_response']
            try:action=parse_action(text)
            except (ValueError,TypeError):action={'tool':'invalid'}
            obs=s.handle(action);next_prompt=json.dumps({'tool_result':obs},ensure_ascii=False)
            print(json.dumps({'trial':trial_id,'action':s.actions,'tool':action.get('tool'),'status':obs.get('status')}),flush=True)
            if obs.get('status')=='ENV_ERROR':raise RuntimeError('Indeterminate public checker; stop affected trial')
        send({'stop':True});process.stdin.close();process.wait(timeout=30);stopped=process.returncode==0
        if not stopped:raise RuntimeError('Worker exit unsuccessful')
    except Exception as e:
        error=type(e).__name__
    finally:
        if process is not None and process.poll() is None:
            # No grading after uncertain remote termination. The bounded worker
            # request timeout remains effective; do not assert remote exit here.
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        stderr.close()
    if error or not stopped or not unchanged(plan):
        terminal={'reward':None,'category':'infrastructure_error','exception_type':error,'solver_stop_confirmed':stopped}
    else:
        try:terminal=s.finalize(True)
        except Exception as e:terminal={'reward':None,'category':'infrastructure_error','exception_type':type(e).__name__}
    save(out/'terminal.json',terminal)
    evaluation=None
    if stopped and not error and s.submitted and unchanged(plan):
        try:evaluation=anchor(s.out/'submission'/s.filename,out/'reserved-evaluation')
        except Exception as e:evaluation={'reward':None,'category':'infrastructure_error','exception_type':type(e).__name__}
    save(out/'reserved-evaluation.json',evaluation)
    result={'schema':VERSION,'trial_id':trial_id,'task_id':task['task_id'],'plan_sha256':sha(planfile),
        'model':plan['model'],'terminal':terminal,'reserved_evaluation':evaluation,'submitted':s.submitted,
        'actions':s.actions,'edits':s.edits,'public_test_calls':s.tests,'solver_stop_confirmed':stopped,
        'frozen_sources_unchanged':unchanged(plan),'model_request_seconds':sum(r.get('seconds',0) for r in requests),
        'wall_seconds':round(time.monotonic()-start,4),'requests':len(requests)}
    save(out/'result.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('trial');p.add_argument('out');a=p.parse_args()
    r=run(a.plan,a.trial,a.out);print(json.dumps(r,indent=2))
