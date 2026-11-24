"""Licensed VCS backend. UVM owns functional scoring; Python orchestrates/results."""
import argparse,hashlib,json,os,re,shlex,subprocess,uuid
from pathlib import Path
from .vectors import vectors
ROOT=Path(__file__).resolve().parents[1]

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def interpret(log,rc,count):
    result={'reward':None,'category':'infrastructure_error','simulation_exit':rc,'expected_transactions':count}
    result['observed_axi_responses']=len(re.findall(r'^PB2_AXI ',log,re.M))
    result['observed_apb_transactions']=len(re.findall(r'^PB2_APB ',log,re.M))
    result['failure_details']=re.findall(r'^PB2_ERROR (.*)',log,re.M)[:20]
    result['timing_failures']=re.findall(r'UVM_ERROR[^\n]*\[PB_TIMING\] (.*)',log)[:20]
    summary=re.search(r'PB2_RESULT planned=(\d+) axi=(\d+) apb=(\d+) checked=(\d+) errors=(\d+)',log)
    cover=re.search(r'PB2_COVER aw_first=(\d+) w_first=(\d+) together=(\d+) stalls=(\d+) early=(\d+) waits=(\d+) resets=(\d+)',log)
    if cover:result['coverage']=dict(zip(('aw_first','w_first','together','stalls','early','waits','resets'),map(int,cover.groups())))
    if 'Invalid configuration passed' in log or '[check_packer_max_bytes]' in log:
        result['reason']='VIP configuration rejected at initialization'
    elif 'PB_INFRA' in log or re.search(r'LICENSING|Failed attempting|license checkout',log,re.I):
        result['reason']='VIP infrastructure failure'
    elif '[PB_TIMING]' in log:
        result.update(reward=0.0,category='protocol_timing_error')
    elif '[PB_FUNCTION]' in log and not summary:
        result.update(reward=0.0,category='transaction_functional_error')
    elif 'PB2_TIMEOUT' in log:
        result.update(reward=0.0,category='test_timeout')
    elif rc==0 and 'PB2_DONE' in log and summary:
        planned,axi,apb,checked,errors=map(int,summary.groups())
        result.update(observed_axi_responses=axi,observed_apb_transactions=apb,scoreboard={'planned':planned,'checked':checked,'errors':errors,'engine':'UVM VIP monitor analysis ports'})
        complete=planned==count==axi==apb==checked
        clean=bool(re.search(r'UVM_ERROR\s*:\s*0',log) and re.search(r'UVM_FATAL\s*:\s*0',log))
        if not complete or errors:
            result.update(reward=0.0,category='transaction_functional_error')
        elif not clean:
            result.update(reward=0.0,category='protocol_timing_error')
        elif not cover or not all(result['coverage'].values()):
            result['reason']='required stimulus coverage not reached'
        else:result.update(reward=1.0,category='pass')
    else:result['reason']='incomplete simulation or unclassified failure'
    return result

def grade(source,out,public=False,reuse_build=None,runtime_args=(),fresh_runtime=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    result={'reward':None,'category':'infrastructure_error','public':public,'source_sha256':digest(source)}
    try:
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
        ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        rows=vectors(public)
        (out/'vectors.json').write_text(json.dumps(rows))
        (out/'bridge.sv').write_bytes(Path(source).read_bytes())
        (out/'vectors.txt').write_text(''.join('%d %08x %08x %x %d %d %d %d\n'%tuple(x) for x in rows))
        inputs={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'verifier/v2').glob('*.sv')}
        inputs['candidate']=digest(source)
        def run(cmd,timeout):
            child_env={k:os.environ[k] for k in ('PATH','HOME','LANG','SSH_AUTH_SOCK') if k in os.environ}
            p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=child_env)
            return p.returncode,p.stdout.decode(errors='replace')
        def copy(files,remote):
            rc,log=run(['scp','-F',cfg['ssh_config'],*map(str,files),cfg['host']+':'+remote+'/'],40)
            if rc:raise RuntimeError('SCP failed')
        if reuse_build:
            build=json.loads((Path(reuse_build)/'backend.json').read_text())
            if build['inputs']!=inputs or build['host']!=cfg['host']:raise RuntimeError('Compiled inputs changed')
            remote=build['remote']
            if fresh_runtime:
                fresh=cfg['remote_root']+'/'+uuid.uuid4().hex
                rc,log=run(ssh+['mkdir -p '+shlex.quote(fresh)+' && cp -a '+shlex.quote(remote+'/.')+' '+shlex.quote(fresh+'/')],90)
                if rc:raise RuntimeError('Compiled simulation copy failed')
                remote=fresh;build={**build,'remote':fresh}
            copy([out/'vectors.txt'],remote)
            result['compile_reused']=True
        else:
            remote=cfg['remote_root']+'/'+uuid.uuid4().hex
            rc,log=run(ssh+['mkdir -p '+shlex.quote(remote)],20)
            if rc:raise RuntimeError('SSH setup failed')
            copy([out/'bridge.sv',out/'vectors.txt',ROOT/'verifier/v2/tb.sv',ROOT/'verifier/v2/vip.sv'],remote)
            inc=' '.join('+incdir+'+shlex.quote(cfg[k]+s) for k in ('vip_root','axi_vip_root') for s in ('/include/sverilog','/src/sverilog/vcs'))
            cache_flag=(' -Mlib='+shlex.quote(cfg['compile_cache'])) if cfg.get('compile_cache') else ''
            defines=' +define+SVT_APB_MAX_DATA_WIDTH=32 +define+SVT_APB_MAX_ADDR_WIDTH=32 +define+SVT_AXI_MAX_DATA_WIDTH=32 +define+SVT_AXI_MAX_ADDR_WIDTH=32 +define+UVM_PACKER_MAX_BYTES=1500000 +define+UVM_DISABLE_AUTO_ITEM_RECORDING +define+SVT_AXI_MAX_NUM_MASTERS_1 +define+SVT_AXI_MAX_NUM_SLAVES_1 +define+SVT_APB_MAX_NUM_SLAVES_1 '
            command='source ~/.bashrc; cd '+shlex.quote(remote)+'; timeout 1200 vcs -full64 -sverilog -ntb_opts uvm -timescale=1ns/1ps'+cache_flag+defines+'+incdir+. '+inc+' bridge.sv tb.sv -top tb -o simv > compile.log 2>&1; r=$?; cat compile.log; exit $r'
            rc,log=run(ssh+[command],1230);(out/'compile.log').write_text(log);result['compile_exit']=rc
            if rc:
                errors=re.findall(r'Error-\[.*?(?=\nError-|\Z)',log,re.S)
                if errors and all('bridge.sv' in e[:300] for e in errors) and not re.search(r'LICENS|Cannot find',log):result.update(reward=0.0,category='compile_error')
                (out/'result.json').write_text(json.dumps(result,indent=2));return result
            build={'remote':remote,'host':cfg['host'],'inputs':inputs}
        (out/'backend.json').write_text(json.dumps(build,indent=2))
        args=' '.join(shlex.quote(x) for x in runtime_args)
        command='source ~/.bashrc; export DESIGNWARE_HOME='+shlex.quote(cfg['designware_home'])+'; cd '+shlex.quote(remote)+'; timeout 240 ./simv +ntb_random_seed=17 '+args+' > simulation.log 2>&1; r=$?; cat simulation.log; exit $r'
        rc,log=run(ssh+[command],260);(out/'simulation.log').write_text(log)
        result.update(interpret(log,rc,len(rows)))
    except Exception as e:result['reason']=type(e).__name__+': '+str(e)[:160]
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--public',action='store_true');a=p.parse_args()
    print(json.dumps(grade(a.source,a.out,a.public),indent=2))
