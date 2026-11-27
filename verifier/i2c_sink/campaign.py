"""VIP write driving/monitoring plus independent pin and delivery accounting."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha,source_policy as base_policy
from verifier.uart_tx.campaign_v5 import classify_compile
from .corpus import corpus,encode
TASKS={f'i2c_sink_{m}_v1':m for m in ('byte','word')}

def source_policy(text):
    bad=base_policy(re.sub(r'\bmodule\s+i2c_sink\b','module accumulator',text,count=1))
    if bad:return bad
    s=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if '#' in s:return 'delay_or_parameter_not_supported'
    header=re.search(r'\bmodule\s+i2c_sink\s*\((.*?)\)\s*;',s,re.S)
    if not header:return 'missing_fixed_interface'
    names=[]
    for port in header.group(1).split(','):
        tokens=re.findall(r'[A-Za-z_][A-Za-z_0-9]*',re.sub(r'\[[^\]]*\]','',port))
        names.append(tokens[-1] if tokens else None)
    return None if names==['clk','rst_n','scl','sda','sda_drive_low','item_valid','item_data'] else 'fixed_interface_names_or_order'

def interpret(log,rc,mode,frames):
    r=dict(reward=None,category='infrastructure_error',verification_complete=False)
    if rc in (124,137):return dict(r,category='infrastructure_timeout')
    if 'PB_I2C_INVALID_INTERFACE' in log:return dict(r,category='invalid_submission')
    if rc or 'PB_I2C_INFRA' in log or '[PB_INFRA]' in log:return r
    failures=re.findall(r'^PB_I2C_FAIL (.*)$',log,re.M)
    if failures:return dict(r,reward=0.,category='protocol_timing_error' if failures[0] in ('ack hold window','drive changes while SCL high') else 'transaction_mismatch',first_failure=failures[0])
    counts={k:re.findall(r'^UVM_'+k+r'\s*:\s*(\d+)\s*$',log,re.M) for k in ('WARNING','ERROR','FATAL')}
    n=len(frames);b=sum(map(len,frames));items=sum(len(f) if mode=='byte' else len(f)//2 for f in frames);odd=sum(len(f)%2 for f in frames)
    expected=[tuple(map(str,(n,b,items,b+n,odd)))]
    done=re.findall(r'^PB_I2C_COMPLETE frames=(\d+) bytes=(\d+) items=(\d+) acks=(\d+) odd=(\d+)\s*$',log,re.M)
    # Unexplained vendor failures remain indeterminate: do not infer DUT blame from a count.
    if counts=={'WARNING':['0'],'ERROR':['0'],'FATAL':['0']} and done==expected:
        return dict(r,reward=1.,category='pass',verification_complete=True,activity=dict(frames=n,bytes=b,items=items,acks=b+n,odd_frames=odd))
    if re.search(r'^UVM_ERROR[^\n]*\[PB_SEMANTIC\]',log,re.M):return dict(r,reward=0.,category='transaction_mismatch')
    return dict(r,category='unclassified_verifier_result')

def grade(task,source,out,phase='public'):
    if task not in TASKS:raise ValueError('Unknown I2C task')
    mode=TASKS[task];frames=corpus(mode,phase);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source)
    tb=Path(__file__).with_name('tb.sv');start=time.monotonic()
    result=dict(task_id=task,phase=phase,source_sha256=sha(source),grader_sha256=sha(__file__),testbench_sha256=sha(tb),corpus_sha256=sha(Path(__file__).with_name('corpus.py')),reward=None,category='infrastructure_error',verification_complete=False)
    try:
        bad=source_policy(source.read_text())
        if bad:result.update(category='invalid_submission',reason=bad);return result
        (out/'candidate.sv').write_bytes(source.read_bytes());(out/'tb.sv').write_bytes(tb.read_bytes());(out/'stimulus.txt').write_text(encode(mode,frames));result['input_sha256']=sha(out/'stimulus.txt')
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        base=cfg['i2c_vip_setup_root'];uvm=cfg['i2c_uvm_root']+'/src';remote=cfg['remote_root']+'/i2c-task-'+uuid.uuid4().hex
        def run(cmd,timeout):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,text=True,timeout=timeout)
        if run('mkdir -p '+shlex.quote(remote),30).returncode:return result
        subprocess.run(['scp','-F',cfg['ssh_config']]+[str(out/f) for f in ('candidate.sv','tb.sv','stimulus.txt')]+[cfg['host']+':'+remote+'/'],check=True,capture_output=True,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        args=['vcs','-full64','-sverilog','-timescale=100ps/100ps','+define+SVT_UVM_TECHNOLOGY','+define+SYNOPSYS_SV','+define+UVM_PACKER_MAX_BYTES=1500000','+define+UVM_DISABLE_AUTO_ITEM_RECORDING','-CFLAGS','-DVCS','+incdir+'+uvm,uvm+'/dpi/uvm_dpi.cc']
        args+=['+incdir+'+base+'/'+d for d in ('src/sverilog/vcs','include/sverilog','src/verilog/vcs','include/verilog')]
        args+=['-y',base+'/src/verilog/vcs','+libext+.v','-top','tb','-o','simv','candidate.sv','tb.sv']
        t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && timeout 180 '+shlex.join(args),210);log=r.stdout+r.stderr
        result.update(compile_exit=r.returncode,compile_seconds=round(time.monotonic()-t,4));(out/'compile.log').write_text(log)
        if r.returncode:
            if classify_compile(log)=='compile_error':result.update(reward=0.,category='compile_error')
            return result
        t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && timeout 120 ./simv +ntb_random_seed='+str({'public':123,'terminal':345,'evaluation':567}[phase])+' +UVM_VERBOSITY=UVM_LOW',140)
        result.update(simulation_exit=r.returncode,simulation_seconds=round(time.monotonic()-t,4));(out/'simulation.log').write_text(r.stdout+r.stderr)
        result.update(interpret(r.stdout+r.stderr,r.returncode,mode,frames));result['simulation_sha256']=sha(out/'simulation.log')
    except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
    except Exception as e:result['exception_type']=type(e).__name__
    finally:
        result['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task',choices=TASKS);p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase),indent=2))
