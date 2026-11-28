"""Installed-SDK native-v3 acceptance. Credentials stay in memory only."""
import argparse,getpass,json,subprocess,queue,threading,time
from pathlib import Path
from environment.artifact_task.session_v4 import Session,sha,save
from environment.native_tools.controller_v3 import Controller
parser=argparse.ArgumentParser(description='Run deterministic native SDK acceptance; no model inference or EDA.')
parser.add_argument('--out',type=Path,required=True);parser.add_argument('--config',type=Path,default=Path('.local/config.json'));parser.add_argument('--ask-sudo-password',action='store_true')
args=parser.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=False)
c=json.loads(args.config.read_text());ssh=['ssh','-F',c['ssh_config'],c['host']]
password=getpass.getpass('Temporary deployment password: ') if args.ask_sudo_password else None
sudo='sudo -n ' if password is None else 'sudo -S -p "" '
prefix='' if password is None else password+'\n'
# Installation is an administrator prerequisite, outside this acceptance command.
installed={
 '/opt/protocolbridge-runtime/opt/pb/native-tools-v3/worker_v3.py':sha('environment/native_tools/worker_v3.py'),
 '/opt/protocolbridge-runtime/opt/pb/native-tools-v3/tools_v3.mjs':sha('environment/native_tools/tools_v3.mjs'),
 '/usr/local/sbin/pb-native-sandbox-v3':sha('environment/native_tools/launch_v3.sh')}
code='import sys,json,hashlib; from pathlib import Path; d=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in d.items())'
subprocess.run(ssh+['python3 -c '+__import__('shlex').quote(code)],input=json.dumps(installed)+'\n',text=True,capture_output=True,check=True,timeout=30)
save(out/'installed-source-hashes.json',list(installed.values()))

cases={
 'permissions': [('read','{"file":"spec.md"}'),('read','{"file":"candidate.sv"}'),('edit','{"content":"bad"}'),('edit','{"file":"reference.sv","content":"bad"}'),('shell','{"cmd":"id"}'),('test',''),('read','{"file":"spec.md","file":"candidate.sv"}'),('edit','{"file":"candidate.sv","content":"accepted"}'),('test','{}'),('test','{}'),('test','{}'),('submit','{}'),('edit','{"file":"candidate.sv","content":"late"}')],
 'total_budget':[('read','{"file":"spec.md"}')]*25}
results=[]
for label,actions in cases.items():
 trial=out/label;trial.mkdir();work=trial/'work';work.mkdir();(work/'candidate.sv').write_text('initial');(work/'spec.md').write_text('spec')
 grade_calls=[]
 def grade(path,dest,phase):
  grade_calls.append((phase,sha(path)));return {'reward':1,'category':'pass','source_sha256':sha(path)}
 s=Session({'task_id':'mechanism','deliverable':'candidate.sv'},work,trial/'session',grade,20,2);ctrl=Controller(s)
 calls=[{'type':'tool-call','id':'m-'+str(i),'name':name,'arguments':args} for i,(name,args) in enumerate(actions)]
 bootstrap={'probe_only':True,'api_key':'zero-api-mechanism','filename':'candidate.sv','mechanism_calls':calls,'max_model_requests':20}
 save(trial/'input.json',bootstrap)
 p=subprocess.Popen(ssh+[sudo+'/usr/local/sbin/pb-native-sandbox-v3 /work/native-'+label],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(trial/'stderr.log').open('w'),text=True,bufsize=1)
 q=queue.Queue()
 def read():
  for line in p.stdout:q.put(line)
  q.put(None)
 threading.Thread(target=read,daemon=True).start();p.stdin.write(prefix+json.dumps(bootstrap)+'\n');p.stdin.flush()
 records=[];error=None;started=time.monotonic()
 try:
  while True:
   line=q.get(timeout=120)
   if line is None:break
   row=json.loads(line);records.append(row);save(trial/'events.json',records)
   if row.get('kind')=='tool_request':
    reply=ctrl.dispatch(row);p.stdin.write(json.dumps(reply)+'\n');p.stdin.flush();ctrl.returned(row['call_id'])
   if row.get('kind') in ('worker_error','transport_error'):raise RuntimeError(row)
  p.wait(timeout=10);assert p.returncode==0
  assert records[-1]['kind']=='stopped'
  check=next(r['checks'] for r in records if r['kind']=='isolation_probe')
  assert check['uid']==1101 and check['pid']==1 and check['no_new_privs']=='1' and int(check['cap_eff'],16)==0
  assert all(v for k,v in check.items() if k.endswith(('_absent','_denied')))
  result=next(x['result'] for x in records if x['kind']=='mechanism_result');assert len(result['results'])==len(calls)
  assert result['concluded'] is True
  if label=='permissions':
   assert s.actions==12 and s.edits==1 and s.tests==2 and s.submitted
   assert (s.out/'submission/candidate.sv').read_text()=='accepted'
   assert len(grade_calls)==2
   assert [x['observation'].get('status') for x in ctrl.calls]==[None,None,'REJECTED','REJECTED','REJECTED','REJECTED','REJECTED','EDITED','PASS','PASS','REJECTED','SUBMITTED','REJECTED']
  else:assert s.actions==20 and not grade_calls and not s.submitted and len(ctrl.calls)==25
 except Exception as e:
  error=repr(e)
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=10)
 result={'label':label,'passed':error is None,'error':error,'actions':s.actions,'tests':s.tests,'edits':s.edits,'raw_calls':len(calls),'grader_calls':len(grade_calls),'seconds':time.monotonic()-started,'model_inference_requests':0}
 save(trial/'result.json',result);results.append(result);save(out/'results.json',results);print(json.dumps(result),flush=True)
 if error:break
save(out/'sources.json',{str(p):sha(p) for p in Path('environment/native_tools').glob('*') if p.is_file()})
password=None
if not all(r['passed'] for r in results) or len(results)!=len(cases):raise SystemExit(1)
