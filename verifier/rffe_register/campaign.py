"""RFFE VIP transactions plus physical pin decoding and independent register state."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha,source_policy as base_policy
from verifier.uart_tx.campaign_v5 import classify_compile
from .corpus import corpus
TASKS={f'rffe_register_{m}_v1':m for m in ('rw','w1c')}

def source_policy(text):
    bad=base_policy(re.sub(r'\bmodule\s+rffe_register\b','module accumulator',text,count=1))
    if bad:return bad
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if '#' in clean:return 'delay_or_parameter_not_supported'
    header=re.search(r'\bmodule\s+rffe_register\s*\((.*?)\)\s*;',clean,re.S)
    if not header:return 'fixed_ansi_interface_required'
    actual=[];direction=None;width=1
    for port in header[1].split(','):
        d=re.search(r'\b(input|output|inout)\b',port)
        if d:direction,width=d[1],1
        bounds=re.search(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]',port)
        if bounds:width=abs(int(bounds[1])-int(bounds[2]))+1
        elif '[' in port:return 'literal_interface_width_required'
        words=re.findall(r'[A-Za-z_][A-Za-z_0-9]*',re.sub(r'\[[^\]]*\]','',port))
        actual.append((words[-1] if words else None,direction,width))
    expected=[(n,'input',1) for n in ('clk','rst_n','sclk','sdata')]+[(n,'output',1) for n in ('sdata_out','sdata_oe')]
    return None if actual==expected else 'fixed_interface'


def interpret(log,rc,coverage):
    result=dict(reward=None,category='infrastructure_error',verification_complete=False)
    if rc in (124,137):return dict(result,category='infrastructure_timeout')
    if rc or 'PB_RFFE_INFRA' in log:return result
    failures=re.findall(r'^PB_RFFE_MISMATCH (.*)$',log,re.M)
    if failures:
        kind='protocol_timing_error' if failures[0].startswith('park ') else 'transaction_mismatch'
        return dict(result,reward=0.,category=kind,first_failure=failures[0])
    done=re.findall(r'^PB_RFFE_COMPLETE frames=(\d+) reads=(\d+) resets=(\d+)\s*$',log,re.M)
    expected=[tuple(str(coverage[k]) for k in ('frames','reads','resets'))]
    counts={k:re.findall(r'^UVM_'+k+r'\s*:\s*(\d+)\s*$',log,re.M) for k in ('WARNING','ERROR','FATAL')}
    if done==expected and counts=={'WARNING':['0'],'ERROR':['0'],'FATAL':['0']}:
        return dict(result,reward=1.,category='pass',verification_complete=True,activity=coverage)
    return dict(result,category='unclassified_verifier_result')

def grade(task,source,out,phase='public'):
    if task not in TASKS:raise ValueError('Unknown RFFE task')
    mode=TASKS[task];rows,coverage=corpus(mode,phase);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source)
    tb=Path(__file__).with_name('tb.sv');start=time.monotonic()
    result=dict(task_id=task,phase=phase,source_sha256=sha(source),grader_sha256=sha(__file__),testbench_sha256=sha(tb),corpus_sha256=sha(Path(__file__).with_name('corpus.py')),reward=None,category='infrastructure_error',verification_complete=False)
    try:
        bad=source_policy(source.read_text())
        if bad:result.update(category='invalid_submission',reason=bad);return result
        (out/'candidate.sv').write_bytes(source.read_bytes());(out/'tb.sv').write_bytes(tb.read_bytes());(out/'commands.txt').write_text(str(len(rows))+'\n'+'\n'.join(' '.join(map(str,r)) for r in rows)+'\n');result['input_sha256']=sha(out/'commands.txt')
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        base=cfg['rffe_vip_setup_root'];uvm=cfg['rffe_uvm_root']+'/src';remote=cfg['remote_root']+'/rffe-task-'+uuid.uuid4().hex
        def run(cmd,timeout):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,text=True,timeout=timeout)
        if run('mkdir -p '+shlex.quote(remote),30).returncode:return result
        subprocess.run(['scp','-F',cfg['ssh_config']]+[str(out/f) for f in ('candidate.sv','tb.sv','commands.txt')]+[cfg['host']+':'+remote+'/'],check=True,capture_output=True,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        args=['vcs','-full64','-sverilog','-timescale=1ns/1ps','+define+SVT_UVM_TECHNOLOGY','+define+SYNOPSYS_SV','+define+UVM_PACKER_MAX_BYTES=1500000','+define+UVM_DISABLE_AUTO_ITEM_RECORDING','-CFLAGS','-DVCS','+incdir+'+uvm,uvm+'/dpi/uvm_dpi.cc']
        args+=['+incdir+'+base+'/'+d for d in ('src/sverilog/vcs','include/sverilog','src/verilog/vcs','include/verilog')]
        args+=['-y',base+'/src/verilog/vcs','+libext+.v','-top','top','-o','simv','candidate.sv','tb.sv']
        t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && timeout 180 '+shlex.join(args),210);log=r.stdout+r.stderr
        result.update(compile_exit=r.returncode,compile_seconds=round(time.monotonic()-t,4));(out/'compile.log').write_text(log)
        if r.returncode:
            if classify_compile(log)=='compile_error':result.update(reward=0.,category='compile_error')
            return result
        t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && timeout 120 ./simv +ntb_random_seed='+str({'public':123,'terminal':345,'evaluation':567}[phase])+' +UVM_VERBOSITY=UVM_LOW',140)
        result.update(simulation_exit=r.returncode,simulation_seconds=round(time.monotonic()-t,4));(out/'simulation.log').write_text(r.stdout+r.stderr)
        result.update(interpret(r.stdout+r.stderr,r.returncode,coverage));result['simulation_sha256']=sha(out/'simulation.log')
    except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
    except Exception as e:result['exception_type']=type(e).__name__
    finally:
        result['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task',choices=TASKS);p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase),indent=2))
