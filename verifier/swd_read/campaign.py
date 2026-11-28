"""Industrial SWD host plus independent pin-level read/ownership checker."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha,source_policy as base_policy
from verifier.uart_tx.campaign_v5 import classify_compile
from .corpus import corpus
TASK='swd_read_v1'
VERSION='swd-read-verifier-v2'
def candidate_compile_error(log):
    # Require a candidate location inside an actual error block. Merely parsing
    # candidate.sv before a trusted-bench error cannot classify that error as RTL.
    return classify_compile(log)=='compile_error' and any(
        re.search(r'''(?m)^\s*["']?candidate\.sv["']?[,:( ]''',block)
        for block in re.split(r'(?m)^Error-\[',log)[1:])

def source_policy(text):
    bad=base_policy(re.sub(r'\bmodule\s+swd_read\b','module accumulator',text,count=1))
    if bad:return bad
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if '#' in clean:return 'delay_or_parameter_not_supported'
    header=re.search(r'\bmodule\s+swd_read\s*\((.*?)\)\s*;',clean,re.S)
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
    expected=[(n,'input',1) for n in ('clk','rst_n','swclk','swdio')]+[('read_value','input',32),('dout','output',1),('oe','output',1)]
    return None if actual==expected else 'fixed_interface'

def interpret(log,rc,coverage):
    result=dict(reward=None,category='infrastructure_error',verification_complete=False)
    if rc in (124,137):return dict(result,category='infrastructure_timeout')
    if rc or 'PB_SWD_INFRA' in log:return result
    failures=re.findall(r'^PB_SWD_MISMATCH (timing|data) (.*)$',log,re.M)
    if failures:return dict(result,reward=0.,category='protocol_timing_error' if failures[0][0]=='timing' else 'transaction_mismatch',first_failure=failures[0][1])
    done=re.findall(r'^PB_SWD_COMPLETE pins=(\d+) responses=(\d+) lines=(\d+) resets=(\d+)\s*$',log,re.M)
    expected=[tuple(str(coverage[k]) for k in ('reads','reads','line_resets','physical_resets'))]
    counts={k:re.findall(r'^UVM_'+k+r'\s*:\s*(\d+)\s*$',log,re.M) for k in ('WARNING','ERROR','FATAL')}
    if done==expected and counts=={'WARNING':['0'],'ERROR':['0'],'FATAL':['0']}:
        return dict(result,reward=1.,category='pass',verification_complete=True,activity=coverage)
    return dict(result,category='unclassified_verifier_result')

def grade(task,source,out,phase='public'):
    if task!=TASK:raise ValueError('Unknown SWD task')
    rows,coverage=corpus(phase);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source)
    tb=Path(__file__).with_name('tb.sv');start=time.monotonic();remote=None;cfg={}
    result=dict(task_id=task,phase=phase,verifier_version=VERSION,source_sha256=sha(source),grader_sha256=sha(__file__),testbench_sha256=sha(tb),corpus_sha256=sha(Path(__file__).with_name('corpus.py')),reward=None,category='infrastructure_error',verification_complete=False)
    try:
        bad=source_policy(source.read_text())
        if bad:result.update(category='invalid_submission',reason=bad);return result
        (out/'candidate.sv').write_bytes(source.read_bytes());(out/'tb.sv').write_bytes(tb.read_bytes())
        (out/'commands.txt').write_text(str(len(rows))+'\n'+'\n'.join('%d %08x %08x'%r for r in rows)+'\n');result['input_sha256']=sha(out/'commands.txt')
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        base=cfg['swd_vip_setup_root'];uvm=cfg['swd_uvm_root']+'/src';remote=cfg['remote_root']+'/swd-task-'+uuid.uuid4().hex
        def run(cmd,timeout):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,text=True,timeout=timeout)
        space=run('df -Pk '+shlex.quote(cfg['remote_root'])+" | tail -1 | awk '{print $4}'",30)
        if space.returncode or int(space.stdout.strip())<512*1024:
            result['reason']='insufficient_storage_reserve';return result
        if run('mkdir -p '+shlex.quote(remote),30).returncode:return result
        subprocess.run(['scp','-F',cfg['ssh_config']]+[str(out/f) for f in ('candidate.sv','tb.sv','commands.txt')]+[cfg['host']+':'+remote+'/'],check=True,capture_output=True,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        args=['vcs','-full64','-sverilog','-timescale=1ns/1ps','+define+SVT_SWD','+define+SVT_UVM_TECHNOLOGY','+define+SYNOPSYS_SV','+define+UVM_PACKER_MAX_BYTES=1500000','+define+UVM_DISABLE_AUTO_ITEM_RECORDING','-CFLAGS','-DVCS','+incdir+'+uvm,uvm+'/dpi/uvm_dpi.cc']
        args+=['+incdir+'+base+'/'+d for d in ('src/sverilog/vcs','include/sverilog','src/verilog/vcs','include/verilog')]
        args+=['-y',base+'/src/verilog/vcs','+libext+.v','-top','top','-o','simv','candidate.sv','tb.sv']
        t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && timeout 180 '+shlex.join(args),210);log=r.stdout+r.stderr
        result['toolchain_observed']={'vcs':sorted(set(re.findall(r'Version (O-[0-9.]+-SP[0-9]+)_Full64',log))), 'vip':sorted(set(re.findall(r'/swd_svt/(R-[0-9.]+)/',log)))}
        result.update(compile_exit=r.returncode,compile_seconds=round(time.monotonic()-t,4));(out/'compile.log').write_text(log)
        if r.returncode:
            if candidate_compile_error(log):result.update(reward=0.,category='compile_error')
            return result
        t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && timeout 60 ./simv +ntb_random_seed='+str({'public':123,'terminal':345,'evaluation':567}[phase])+' +UVM_VERBOSITY=UVM_LOW',80)
        result.update(simulation_exit=r.returncode,simulation_seconds=round(time.monotonic()-t,4));(out/'simulation.log').write_text(r.stdout+r.stderr)
        result['toolchain_observed']['uvm']=sorted(set(re.findall(r'^UVM-([0-9.a-z]+)$',r.stdout,re.M)))
        result.update(interpret(r.stdout+r.stderr,r.returncode,coverage));result['simulation_sha256']=sha(out/'simulation.log')
    except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
    except Exception as e:result['exception_type']=type(e).__name__
    finally:
        # Only this invocation's reproducible binaries may be pruned; submitted
        # source, bench, vectors, results and all original logs stay intact.
        if remote and cfg.get('swd_prune_derived_builds') is True:
            try:
                cleanup=run('cd '+shlex.quote(remote)+' && rm -rf -- csrc simv simv.daidir ucli.key vc_hdrs.h',30)
                result['derived_build_pruned']=cleanup.returncode==0
            except Exception:result['derived_build_pruned']=False
        result['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');a=p.parse_args();print(json.dumps(grade(TASK,a.source,a.out,a.phase),indent=2))
