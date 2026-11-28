"""Bounded VCS transport for trusted event benches; no task semantics live here.

Inputs are supplied only by trusted task-specific code. Candidate RTL never
chooses the bench, events, parser or commands. Existing graders are unchanged.
"""
import json,os,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha
from verifier.uart_tx.campaign_v4 import classify_compile

def run(source,out,*,task,bench,rows,source_policy,interpret,identity):
    out=Path(out).resolve();source=Path(source);out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    result=dict(task_id=task,source_sha256=sha(source),reward=None,category='infrastructure_error',verification_complete=False,**identity)
    try:
        invalid=source_policy(source.read_text())
        if invalid:result.update(category='invalid_submission',reason=invalid);return result
        (out/'candidate.sv').write_bytes(source.read_bytes());(out/'tb.sv').write_text(bench)
        (out/'events.txt').write_text(str(len(rows))+'\n'+'\n'.join(' '.join(map(str,r)) for r in rows)+'\n')
        result['input_sha256']=sha(out/'events.txt')
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        remote=cfg['remote_root'].rstrip('/')+'/event-checker-'+uuid.uuid4().hex
        def command(s,seconds):return subprocess.run(ssh+[remote_command(cfg,s)],capture_output=True,text=True,timeout=seconds)
        if command('mkdir -p '+shlex.quote(remote),30).returncode:return result
        subprocess.run(['scp','-F',cfg['ssh_config']]+[str(out/f) for f in ('candidate.sv','tb.sv','events.txt')]+[cfg['host']+':'+remote+'/'],capture_output=True,check=True,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        t=time.monotonic();c=command('cd '+shlex.quote(remote)+' && timeout -k 5 120 vcs -full64 -sverilog -timescale=1ns/1ps candidate.sv tb.sv -top tb -o simv',150)
        result.update(compile_exit=c.returncode,compile_seconds=round(time.monotonic()-t,4));(out/'compile.log').write_text(c.stdout+c.stderr)
        if c.returncode:
            if c.returncode in (124,137):result['category']='infrastructure_timeout'
            elif classify_compile(c.stdout+c.stderr)=='compile_error':result.update(reward=0.,category='compile_error')
            return result
        t=time.monotonic();s=command('cd '+shlex.quote(remote)+' && timeout -k 2 10 ./simv',30)
        result.update(simulation_exit=s.returncode,simulation_seconds=round(time.monotonic()-t,4));log=s.stdout+s.stderr;(out/'simulation.log').write_text(log)
        result.update(interpret(log,s.returncode,len(rows)));result['simulation_sha256']=sha(out/'simulation.log')
    except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
    except Exception as error:result['exception_type']=type(error).__name__
    finally:
        result['wall_seconds']=round(time.monotonic()-start,4)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
