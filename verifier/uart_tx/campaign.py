"""Finite UART transmit task: industrial receive monitor plus independent cycle oracle."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha,source_policy as formal_policy
TASKS={'uart_tx_8n1_v1':0,'uart_tx_8e1_v1':1}
def source_policy(source):
 text=re.sub(r'\bmodule\s+uart_tx\b','module accumulator',source,count=1)
 return formal_policy(text) or ('delay_or_parameter_not_supported' if '#' in text else None)
def interpret(log,rc,parity):
 r={'reward':None,'category':'infrastructure_error','verification_complete':False,'simulation_exit':rc}
 if rc in (124,137):r['category']='infrastructure_timeout';return r
 if rc or re.search(r'licens.*(fail|error)|PB_INFRA',log,re.I):return r
 if 'PB_UART_FUNCTIONAL_FAIL' in log:
  r.update(reward=0.,category='transition_mismatch',diagnostic=re.findall(r'^PB_UART_FUNCTIONAL_FAIL (.*)',log,re.M)[:1]);return r
 if 'PB_UART_TIMEOUT' in log:r.update(reward=0.,category='test_timeout');return r
 counts={k:[int(x) for x in re.findall(r'^UVM_'+k+r'\s*:\s*(\d+)\s*$',log,re.M)] for k in ('WARNING','ERROR','FATAL')}
 done=re.findall(r'^PB_UART_COMPLETE frames=(\d+) cycle_checks=(\d+)\s*$',log,re.M)
 if counts=={'WARNING':[0],'ERROR':[0],'FATAL':[0]} and done==[('256',str(256*16*(11 if parity else 10)))]:
  r.update(reward=1.,category='pass',verification_complete=True,frames=256,cycle_checks=int(done[0][1]))
 elif re.search(r'UVM_ERROR[^\n]*\[PB_(DATA|COUNT)\]',log):r.update(reward=0.,category='transition_mismatch')
 return r

def grade(task,source,out,phase='public'):
 if task not in TASKS or phase not in ('public','terminal','evaluation'):raise ValueError('Unknown task/phase')
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source);tb=Path(__file__).with_name('tb.sv');start=time.monotonic()
 r={'task_id':task,'source_sha256':sha(source),'verifier_sha256':sha(tb),'grader_sha256':sha(__file__),'reward':None,'category':'infrastructure_error','verification_complete':False,'phase':phase}
 try:
  invalid=source_policy(source.read_text())
  if invalid:r.update(category='invalid_submission',reason=invalid);return r
  (out/'candidate.sv').write_bytes(source.read_bytes())
  cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
  base=cfg['uart_vip_setup_root'];uvm=cfg['uart_uvm_root']+'/src';remote=cfg['remote_root']+'/uart-task-'+uuid.uuid4().hex
  def command(cmd,timeout):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,text=True,timeout=timeout)
  if command('mkdir -p '+shlex.quote(remote),30).returncode:raise RuntimeError('Setup failed')
  subprocess.run(['scp','-F',cfg['ssh_config'],str(out/'candidate.sv'),str(tb),cfg['host']+':'+remote+'/'],check=True,capture_output=True,timeout=30)
  (out/'deployment.json').write_text(json.dumps({'remote':remote}))
  flags=['vcs','-full64','-sverilog','-timescale=1ns/1ps','-CFLAGS','-DVCS','+define+SVT_UART','+define+SVT_UVM_TECHNOLOGY','+define+SYNOPSYS_SV','+define+UVM_PACKER_MAX_BYTES=8000']
  flags+=['+incdir+'+base+'/'+d for d in ('src/sverilog/vcs','include/sverilog','src/verilog/vcs','include/verilog')]
  flags+=['+incdir+'+uvm,uvm+'/dpi/uvm_dpi.cc','candidate.sv','tb.sv','-top','tb','-o','simv']
  t=time.monotonic();c=command('cd '+shlex.quote(remote)+'; timeout 180 '+ ' '.join(map(shlex.quote,flags)),210)
  r['compile_seconds']=round(time.monotonic()-t,4);r['compile_exit']=c.returncode;(out/'compile.log').write_text(c.stdout+c.stderr)
  if c.returncode:
   errors=re.findall(r'Error-\[.*?(?=\nError-|\Z)',c.stdout,re.S)
   if errors and all('candidate.sv' in e[:400] for e in errors) and not re.search('licens|cannot find',c.stdout,re.I):r.update(reward=0.,category='compile_error')
   return r
  t=time.monotonic();s=command('cd '+shlex.quote(remote)+'; timeout 30 ./simv +parity='+str(TASKS[task])+' +order='+str(('public','terminal','evaluation').index(phase))+' +UVM_VERBOSITY=UVM_LOW',45)
  r['simulation_seconds']=round(time.monotonic()-t,4);(out/'simulation.log').write_text(s.stdout+s.stderr)
  r.update(interpret(s.stdout,s.returncode,TASKS[task]));r['simulation_sha256']=sha(out/'simulation.log')
 except Exception as e:r['exception_type']=type(e).__name__
 finally:
  r['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase),indent=2))
