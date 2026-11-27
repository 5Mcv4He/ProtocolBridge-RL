"""Independent integer oracle, independent RTL proof, DC, and own-netlist proof."""
import argparse,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.independent_formal.campaign import ROOT,sha,source_policy as base_policy
from verifier.uart_tx.campaign_v5 import classify_compile
from .oracle import corpus
from .results import formal,synthesis,simulation
TASKS={f'bitfold_{m}_repair_v1':m for m in ('population','trailing_zero')}

def source_policy(text):
    bad=base_policy(re.sub(r'\bmodule\s+bitfold\b','module accumulator',text,count=1))
    if bad:return bad
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if '#' in clean:return 'delay_or_parameter_not_supported'
    h=re.search(r'\bmodule\s+bitfold\s*\((.*?)\)\s*;',clean,re.S)
    if not h:return 'fixed_ansi_interface_required'
    canonical=re.sub(r'\b(logic|wire|reg)\b|\s+','',h[1])
    return None if canonical=='input[7:0]data,output[3:0]result' else 'fixed_interface'

def bench():
    return '''`timescale 1ns/1ps
module tb;
 logic[7:0] data;wire[3:0] result;bitfold dut(data,result);
 integer f,n,r,a,b;
 initial begin
 f=$fopen("inputs.txt","r");r=$fscanf(f,"%d\\n",n);
 if(!f||r!=1||n!=768)begin $display("PB_BITFOLD_INFRA input");$finish;end
 for(integer i=0;i<n;i=i+1)begin
 r=$fscanf(f,"%d %d\\n",a,b);
 if(r!=2||a<0||a>255||b<0||b>8)begin $display("PB_BITFOLD_INFRA row");$finish;end
 data=a;#10;if(result!==b[3:0])begin $display("PB_BITFOLD_MISMATCH row=%0d",i);$finish;end
 end
 $display("PB_BITFOLD_COMPLETE rows=%0d",n);$finish;
 end
 initial begin #100000;$display("PB_BITFOLD_INFRA watchdog");$finish;end
endmodule
'''

def grade(task,source,out,phase='public',anchor_only=False,reference_only=False):
    if task not in TASKS:raise ValueError('Unknown bitfold task')
    rows=corpus(TASKS[task],phase);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source)
    here=Path(__file__).parent;ref=ROOT/'tasks'/task/'reference.sv';start=time.monotonic()
    result=dict(task_id=task,phase=phase,source_sha256=sha(source),reference_sha256=sha(ref),grader_sha256=sha(__file__),reward=None,category='infrastructure_error',verification_complete=False,anchor_only=anchor_only,reference_only=reference_only)
    try:
        bad=source_policy(source.read_text())
        if bad:result.update(category='invalid_submission',reason=bad);return result
        for dest,src in [('candidate.sv',source),('reference.sv',ref)]+[(n,here/n) for n in ('dc.tcl','proof.tcl','netlist.tcl')]:
            (out/dest).write_bytes(src.read_bytes())
        (out/'tb.sv').write_text(bench());(out/'inputs.txt').write_text(str(len(rows))+'\n'+'\n'.join('%d %d'%r for r in rows)+'\n');result['input_sha256']=sha(out/'inputs.txt')
        result['trusted_scripts']={n:sha(out/n) for n in ('dc.tcl','proof.tcl','netlist.tcl','tb.sv')}
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text());ssh=['ssh','-F',cfg['ssh_config'],cfg['host']];remote=cfg['remote_root']+'/bitfold-'+uuid.uuid4().hex
        def run(cmd,limit):return subprocess.run(ssh+[remote_command(cfg,cmd)],capture_output=True,text=True,timeout=limit)
        if run('mkdir -p '+shlex.quote(remote),30).returncode:return result
        names=('candidate.sv','reference.sv','dc.tcl','proof.tcl','netlist.tcl','tb.sv','inputs.txt')
        subprocess.run(['scp','-F',cfg['ssh_config']]+[str(out/n) for n in names]+[cfg['host']+':'+remote+'/'],capture_output=True,check=True,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        def tool(name,cmd,limit):
            t=time.monotonic();r=run('cd '+shlex.quote(remote)+' && '+cmd,limit);log=r.stdout+r.stderr
            (out/(name+'.log')).write_text(log);result[name+'_seconds']=round(time.monotonic()-t,4);result[name+'_exit']=r.returncode;result[name+'_log_sha256']=sha(out/(name+'.log'));return log,r.returncode
        if reference_only:
            command='mkdir proof-independent_reference && cp candidate.sv reference.sv proof.tcl proof-independent_reference/ && cd proof-independent_reference && timeout -k 5 120 fm_shell -64bit -f proof.tcl'
            log,rc=tool('independent_reference',command,150);r=formal(log,rc);result['independent_reference']=r;result.update(r);return result
        log,rc=tool('compile','timeout 60 vcs -full64 -sverilog -timescale=1ns/1ps candidate.sv tb.sv -top tb -o simv',80)
        if rc:
            if classify_compile(log)=='compile_error':result.update(reward=0.,category='compile_error')
            return result
        log,rc=tool('simulation','timeout 30 ./simv',40);r=simulation(log,rc,len(rows));result['integer_oracle']=r
        if r['reward']!=1 or anchor_only:result.update(r);return result
        log,rc=tool('synthesis','timeout -k 5 120 dc_shell -64bit -f dc.tcl',150);r=synthesis(log,rc);result['synthesis']=r
        if r['reward']!=1:result.update(reward=r['reward'],category=r['category']);return result
        # Library and mapped netlist identity are experiment metadata, never agent inputs.
        meta=run('cd '+shlex.quote(remote)+' && sha256sum "$CLASS_DB" mapped.v',30)
        hashes=[line.split()[0] for line in meta.stdout.splitlines() if re.match(r'^[0-9a-f]{64} ',line)]
        if meta.returncode or len(hashes)!=2:return result
        result.update(library_sha256=hashes[0],netlist_sha256=hashes[1])
        for name,script in [('independent_reference','proof.tcl'),('own_netlist','netlist.tcl')]:
            # A fresh proof subdirectory cannot accidentally consume DC's default SVF.
            directory='proof-'+name
            sources='candidate.sv reference.sv proof.tcl' if name=='independent_reference' else 'candidate.sv mapped.v netlist.tcl'
            command='mkdir '+directory+' && cp '+sources+' '+directory+'/ && cd '+directory+' && timeout -k 5 120 fm_shell -64bit -f '+script
            log,rc=tool(name,command,150);r=formal(log,rc);result[name]=r
            if r['reward']!=1:
                # An incorrect mapping of a correct RTL is a trusted-tool failure.
                result.update(reward=None if name=='own_netlist' else r['reward'],category='transformation_inconsistent' if name=='own_netlist' and r['reward']==0 else r['category']);return result
        result.update(reward=1.,category='pass',verification_complete=True)
    except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
    except Exception as e:result['exception_type']=type(e).__name__
    finally:
        result['wall_seconds']=round(time.monotonic()-start,4);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task',choices=TASKS);p.add_argument('source');p.add_argument('out');p.add_argument('--phase',default='public');p.add_argument('--anchor-only',action='store_true');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out,a.phase,a.anchor_only),indent=2))
