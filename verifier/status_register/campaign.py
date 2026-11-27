"""Independent reference equivalence plus synchronous, per-bit semantic anchor."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha,source_policy as base_policy
from verifier.uart_tx.campaign_v4 import classify_compile
from .formal import interpret as formal_interpret
from .oracle import corpus
TASKS={f'status_{m}_repair_v1':m for m in ('set_dominant','clear_dominant')}

def source_policy(text):
 bad=base_policy(re.sub(r'\bmodule\s+status_register\b','module accumulator',text,count=1))
 if bad:return bad
 clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
 if '#' in clean:return 'delay_or_parameter_not_supported'
 return None

def bench():
 return '''`timescale 1ns/1ps
module tb;
 bit clk=0;always #5 clk=~clk;
 bit rst_n,sw_write;bit[7:0] hw_set,sw_data;wire[7:0] status;
 status_register dut(.clk(clk),.rst_n(rst_n),.sw_write(sw_write),.hw_set(hw_set),.sw_data(sw_data),.status(status));
 integer f,n,r,a,b,c,d,e;reg[7:0] prior;
 initial begin
  f=$fopen("events.txt","r");r=$fscanf(f,"%d\\n",n);
  if(!f || r!=1 || n<1)begin $display("PB_STATUS_INFRA");$finish;end
  for(integer i=0;i<n;i=i+1)begin
   @(negedge clk);prior=status;r=$fscanf(f,"%d %d %d %d %d\\n",a,b,c,d,e);
   if(r!=5)begin $display("PB_STATUS_INFRA");$finish;end
   rst_n=a;sw_write=b;hw_set=c;sw_data=d;
   #1;if(i>0 && status!==prior)begin $display("PB_STATUS_ASYNC row=%0d",i);$finish;end
   @(posedge clk);#1;
   if(status!==e[7:0])begin $display("PB_STATUS_MISMATCH row=%0d expected=%0d observed=%0d",i,e,status);$finish;end
  end
  $display("PB_STATUS_COMPLETE rows=%0d",n);$finish;
 end
 initial begin #10000000;$display("PB_STATUS_INFRA");$finish;end
endmodule
'''

def interpret_anchor(log,rc,n):
 if rc in (124,137):return dict(reward=None,category='infrastructure_timeout')
 if rc or 'PB_STATUS_INFRA' in log:return dict(reward=None,category='infrastructure_error')
 done=re.findall(r'^PB_STATUS_COMPLETE rows=(\d+)\s*$',log,re.M)
 bad=re.findall(r'^PB_STATUS_(ASYNC|MISMATCH) row=(\d+)(?: expected=\d+ observed=[0-9xz]+)?\s*$',log,re.M)
 if len(bad)==1 and not done:return dict(reward=0.,category='transition_mismatch',first_failure=dict(kind=bad[0][0],row=int(bad[0][1])))
 if done==[str(n)] and not bad:return dict(reward=1.,category='pass',checked_cycles=n,verification_complete=True)
 return dict(reward=None,category='missing_activity')

def grade(task,source,out,phase='public',anchor_only=False):
 if task not in TASKS:raise ValueError('Unknown status-register task')
 mode=TASKS[task];rows=corpus(mode,phase);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source)
 ref=ROOT/'tasks'/task/'reference.sv';proof=Path(__file__).with_name('proof.tcl')
 result=dict(task_id=task,phase=phase,source_sha256=sha(source),reference_sha256=sha(ref),grader_sha256=sha(__file__),oracle_sha256=sha(Path(__file__).with_name('oracle.py')),reward=None,category='infrastructure_error',verification_complete=False,comparison='independent_reference_and_truth_table' if not anchor_only else 'truth_table_only')
 start=time.monotonic()
 try:
  invalid=source_policy(source.read_text())
  if invalid:result.update(category='invalid_submission',reason=invalid);return result
  for dest,src in [('candidate.sv',source),('reference.sv',ref),('proof.tcl',proof)]:(out/dest).write_bytes(src.read_bytes())
  (out/'tb.sv').write_text(bench());(out/'events.txt').write_text(str(len(rows))+'\n'+'\n'.join(' '.join(map(str,r)) for r in rows)+'\n');result['input_sha256']=sha(out/'events.txt')
  cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']];remote=cfg['remote_root']+'/status-'+uuid.uuid4().hex
  def command(cmd,limit):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,text=True,timeout=limit)
  r=command('mkdir -p '+shlex.quote(remote),30)
  if r.returncode:return result
  subprocess.run(['scp','-F',cfg['ssh_config']]+[str(out/f) for f in ('candidate.sv','reference.sv','proof.tcl','tb.sv','events.txt')]+[cfg['host']+':'+remote+'/'],check=True,capture_output=True,timeout=30)
  (out/'deployment.json').write_text(json.dumps({'remote':remote}))
  if not anchor_only:
   t=time.monotonic();r=command('cd '+shlex.quote(remote)+' && timeout -k 5 120 fm_shell -64bit -f proof.tcl',150);log=r.stdout+r.stderr;(out/'formal.log').write_text(log)
   f=formal_interpret(log,r.returncode);result.update(formal=f,formal_seconds=round(time.monotonic()-t,4),formal_log_sha256=sha(out/'formal.log'))
   if f['reward']!=1:result.update(reward=f['reward'],category=f['category']);return result
  t=time.monotonic();r=command('cd '+shlex.quote(remote)+' && timeout 60 vcs -full64 -sverilog -timescale=1ns/1ps candidate.sv tb.sv -top tb -o simv',80)
  result.update(compile_exit=r.returncode,compile_seconds=round(time.monotonic()-t,4));(out/'compile.log').write_text(r.stdout+r.stderr)
  if r.returncode:
   if classify_compile(r.stdout+r.stderr)=='compile_error':result.update(reward=0.,category='compile_error')
   return result
  t=time.monotonic();r=command('cd '+shlex.quote(remote)+' && timeout 30 ./simv',40);result.update(simulation_exit=r.returncode,simulation_seconds=round(time.monotonic()-t,4));(out/'simulation.log').write_text(r.stdout+r.stderr)
  result.update(interpret_anchor(r.stdout+r.stderr,r.returncode,len(rows)));result['simulation_sha256']=sha(out/'simulation.log')
 except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
 except Exception as e:result['exception_type']=type(e).__name__
 finally:
  result['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('task',choices=TASKS);p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');p.add_argument('--anchor-only',action='store_true');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase,a.anchor_only),indent=2))
