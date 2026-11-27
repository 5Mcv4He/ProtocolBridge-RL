"""Independent integer-oracle VCS cross-check of the bounded state contract.

Used to qualify the trusted references, and as a separate post-solver evaluation.
This does not replace the independent-reference Formality terminal verdict.
"""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from .campaign import ROOT,TASKS,sha,source_policy

def run(task,source,out):
    if task not in TASKS.values():raise ValueError('Unknown task')
    kind=next(k for k,v in TASKS.items() if v==task);source=Path(source)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    tb=Path(__file__).with_name('anchor_tb.sv');result={'task_id':task,'source_sha256':sha(source),'oracle_sha256':sha(tb),'reward':None,'category':'infrastructure_error','accepted':False};start=time.monotonic()
    try:
        if source_policy(source.read_text()):result['category']='invalid_submission';return result
        (out/'candidate.sv').write_bytes(source.read_bytes())
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        remote=cfg['remote_root']+'/formal-anchor-'+uuid.uuid4().hex
        def command(cmd,limit):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,universal_newlines=True,timeout=limit)
        if command('mkdir -p '+shlex.quote(remote),30).returncode:raise RuntimeError('Setup failed')
        subprocess.run(['scp','-F',cfg['ssh_config'],str(out/'candidate.sv'),str(tb),cfg['host']+':'+remote+'/'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        compiled=command('cd '+shlex.quote(remote)+'; timeout 60 vcs -full64 -sverilog -timescale=1ns/1ps candidate.sv anchor_tb.sv -top tb -o simv',80)
        (out/'compile.log').write_text(compiled.stdout+compiled.stderr);result['compile_exit']=compiled.returncode
        if compiled.returncode:return result
        simulated=command('cd '+shlex.quote(remote)+'; timeout 30 ./simv +mode='+str(int(kind=='saturating')),40)
        (out/'simulation.log').write_text(simulated.stdout+simulated.stderr);result['simulation_exit']=simulated.returncode
        counts=re.findall(r'PB_ANCHOR_PASS checked=(\d+) state_operand_pairs=(\d+)',simulated.stdout)
        if simulated.returncode==0 and counts==[('196610','65536')]:result.update(reward=1.0,category='pass',accepted=True,checks=196610,state_operand_pairs=65536)
        elif simulated.returncode==0 and re.search(r'^PB_ANCHOR_(FAIL|ASYNC_RESET|RESET_FAIL)\b',simulated.stdout,re.M):result.update(reward=0.0,category='transition_mismatch')
        result['simulation_sha256']=sha(out/'simulation.log')
    except Exception as e:result['exception_type']=type(e).__name__
    finally:
        result['wall_seconds']=round(time.monotonic()-start,4)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('source');p.add_argument('out');a=p.parse_args();print(json.dumps(run(a.task,a.source,a.out),indent=2))
