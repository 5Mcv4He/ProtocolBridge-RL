"""UART verifier revision 2: busy offers and adjacent frames are required actual activity.

Trusted control builds may be reused within a source-matched quality campaign;
Agent submissions cannot select a variant or supply a compiled build.
"""
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

def grade(task,source,out,phase='public',trusted_controls=False,selection=0,reuse_build=None):
 if task not in TASKS or phase not in ('public','terminal','evaluation'):raise ValueError('Unknown task/phase')
 if type(selection)!=int or not 0<=selection<64 or (not trusted_controls and (selection or reuse_build)):raise ValueError('Invalid trusted control selection')
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source);tb=Path(__file__).with_name('tb_v2.sv');start=time.monotonic()
 r={'task_id':task,'source_sha256':sha(source),'verifier_sha256':sha(tb),'grader_sha256':sha(__file__),'reward':None,'category':'infrastructure_error','verification_complete':False,'phase':phase,'verifier_revision':2}
 try:
  invalid=None if trusted_controls else source_policy(source.read_text())
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
  flags+=['+incdir+'+uvm,uvm+'/dpi/uvm_dpi.cc','candidate.sv','tb_v2.sv','-top','tb','-o','simv']
  inputs={'candidate':sha(source),'testbench':sha(tb),'grader':sha(__file__),'environment':__import__('hashlib').sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()}
  if reuse_build:
   prior=json.loads((Path(reuse_build)/'backend.json').read_text())
   if prior['inputs']!=inputs:raise RuntimeError('Control build inputs differ')
   assets=' '.join(shlex.quote(prior['remote']+'/'+n) for n in ('simv','simv.daidir'))
   copied=command('cp -a '+assets+' '+shlex.quote(remote+'/'),60)
   if copied.returncode:raise RuntimeError('Control build reuse failed')
   r.update(compile_reused=True,compile_seconds=0,compile_exit=0)
  else:
   t=time.monotonic();c=command('cd '+shlex.quote(remote)+'; timeout 180 '+ ' '.join(map(shlex.quote,flags)),210)
   r['compile_seconds']=round(time.monotonic()-t,4);r['compile_exit']=c.returncode;(out/'compile.log').write_text(c.stdout+c.stderr)
   if c.returncode:
    errors=re.findall(r'Error-\[.*?(?=\nError-|\Z)',c.stdout,re.S)
    if errors and all('candidate.sv' in e[:400] for e in errors) and not re.search('licens|cannot find',c.stdout,re.I):r.update(reward=0.,category='compile_error')
    return r
  (out/'backend.json').write_text(json.dumps({'remote':remote,'inputs':inputs}))
  t=time.monotonic();s=command('cd '+shlex.quote(remote)+'; timeout 30 ./simv +parity='+str(TASKS[task])+' +order='+str(('public','terminal','evaluation').index(phase))+' +variant='+str(selection)+' +UVM_VERBOSITY=UVM_LOW',45)
  r['simulation_seconds']=round(time.monotonic()-t,4);(out/'simulation.log').write_text(s.stdout+s.stderr)
  r.update(interpret(s.stdout,s.returncode,TASKS[task]));r['simulation_sha256']=sha(out/'simulation.log')
  exposure=re.findall(r'^PB_UART_EXPOSURE busy=(\d+) adjacent=(\d+) accepted=(\d+)\s*$',s.stdout,re.M)
  expected=(str(256*(25 if TASKS[task] else 23)),'255','256')
  if r['reward']==1:
   if exposure!=[expected]:r.update(reward=None,category='missing_activity',verification_complete=False)
   else:r['activity']={'busy_offers':int(expected[0]),'adjacent_frames':255,'accepted':256}
 except Exception as e:r['exception_type']=type(e).__name__
 finally:
  r['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase),indent=2))
