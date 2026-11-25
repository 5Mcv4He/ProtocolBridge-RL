"""Task002 independent VCS/UVM campaign. Functional checking stays in SystemVerilog.
Supports SSH orchestration and local execution on the licensed UTM Linux host.
"""
import argparse,hashlib,json,os,re,shlex,subprocess,uuid
from pathlib import Path
from .scenarios import suite,target
ROOT=Path(__file__).resolve().parents[2]

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_policy(source):
    # Restricted synthesizable single-module submission language. No string literals,
    # compiler directives, external modules, hierarchical reads, or system side effects.
    code=re.sub(r'/\*.*?\*/|//[^\n]*',' ',Path(source).read_text(),flags=re.S)
    if '"' in code or '`' in code or '\\' in code or '::' in code:return 'Strings, directives and escaped identifiers are not accepted'
    if re.search(r'\$(?!clog2\b|bits\b)[A-Za-z_]',code):return 'System tasks/functions outside the synthesis allowlist'
    if re.search(r'\b(initial|final|bind|force|release|import|export|program|class|interface|package)\b',code):return 'Unsupported simulation or external construct'
    if re.search(r'\.\s*[A-Za-z_]\w*\s*(?!\s*\()',code):
        # This task submits one self-contained module; no instance connections needed.
        return 'Hierarchical/member access is not accepted'
    modules=re.findall(r'\bmodule\s+(\w+)',code)
    if modules!=['bridge']:return 'Submit exactly one module named bridge'
    return None

def interpret(log,rc,case):
    rows=case['rows'];aborts=[r for r in rows if r[9]]
    result={'reward':None,'category':'infrastructure_error','simulation_exit':rc,
            'planned':len(rows),'expected_aborted':len(aborts),
            'failures':re.findall(r'^PB2_ERROR (.*)',log,re.M)[:12],
            'timing_failures':re.findall(r'UVM_ERROR[^\n]*\[PB_TIMING\] (.*)',log)[:12]}
    if not rows:
        result['reason']='Empty case cannot establish a verdict';return result
    m=re.search(r'PB2_RESULT planned=(\d+) axi=(\d+) apb=(\d+) checked=(\d+) aborted=(\d+) aborted_apb=(\d+) errors=(\d+)',log)
    if m:result['scoreboard']=dict(zip(('planned','axi','apb','checked','aborted','aborted_apb','errors'),map(int,m.groups())))
    cover=re.search(r'PB2_COVER aw_first=(\d+) w_first=(\d+) together=(\d+) stalls=(\d+) early=(\d+) waits=(\d+) resets=(\d+)',log)
    if cover:result['coverage']=dict(zip(('aw_first','w_first','together','stalls','early','waits','resets'),map(int,cover.groups())))
    route=re.search(r'PB2_ROUTE mapped=(\d+) unmapped=(\d+) target0=(\d+) target1=(\d+) target2=(\d+)',log)
    if route:result['routing']=dict(zip(('mapped','unmapped','target0','target1','target2'),map(int,route.groups())))
    result['latency_samples']=[dict(zip(('accept_to_setup','completion_to_valid','waits','stalls'),map(int,x))) for x in re.findall(r'^PB2_LATENCY accept_to_setup=(-?\d+) completion_to_valid=(-?\d+) waits=(\d+) stalls=(\d+)',log,re.M)]
    result['reset_offsets']=list(map(int,re.findall(r'^PB2_RESET_OFFSET cycles=(\d+)',log,re.M)))
    result['reset_stages']=list(map(int,re.findall(r'^PB2_RESET stage=(\d+)',log,re.M)))
    result['cross_bins']=sorted(set(re.findall(r'^PB2_CROSS (.*)',log,re.M)))
    result['sequence']=re.findall(r'^PB2_SEQUENCE (\S+)',log,re.M)
    result['vip_protocol_errors']=re.findall(r'UVM_ERROR[^\n]*\[(register_fail:AMBA:[^\]]+)\]',log)
    elapsed=re.search(r'^Time:\s+(\d+)\s+ps\s*$',log,re.M)
    if elapsed:
        result['simulation_cycles_including_driver_reset_and_drain']=int(elapsed.group(1))/10000.0
    if 'PB_INFRA' in log or re.search(r'Invalid configuration passed|check_packer_max_bytes|LICENSING|license checkout|Failed attempting|UVM_WARNING[^\n]*\[is_valid\][^\n]*Invalid',log,re.I):
        result['reason']='Initialization or infrastructure failure'
    elif '[PB_TIMING]' in log:result.update(reward=0.0,category='protocol_timing_error')
    elif result['vip_protocol_errors']:result.update(reward=0.0,category='protocol_timing_error')
    elif '[PB_FUNCTION]' in log:result.update(reward=0.0,category='transaction_functional_error')
    elif 'PB2_TIMEOUT' in log:result.update(reward=0.0,category='test_timeout')
    elif rc==0 and m and 'PB2_DONE' in log:
        s=result['scoreboard'];completed=len(rows)-len(aborts);mapped=sum(target(r[1])>=0 for r in rows if not r[9]);apb_completed=mapped+sum(r[9]%100 in (7,8) and target(r[1])>=0 for r in aborts)
        exact=(s['planned']==len(rows) and s['checked']==s['axi']==completed and s['aborted']==len(aborts) and s['apb']==apb_completed and s['aborted_apb']==apb_completed-mapped)
        clean=bool(re.search(r'UVM_ERROR\s*:\s*0',log) and re.search(r'UVM_FATAL\s*:\s*0',log))
        if not exact or s['errors']:result.update(reward=0.0,category='transaction_functional_error')
        elif not route or result['routing']['mapped']!=mapped or result['routing']['unmapped']!=completed-mapped or sum(result['routing']['target%d'%i] for i in range(3))!=apb_completed:result['reason']='Routing observation incomplete or inconsistent'
        elif any(result['routing']['target%d'%i]!=sum(target(r[1])==i and (not r[9] or r[9]%100 in (7,8)) for r in rows) for i in range(3)):result.update(reward=0.0,category='transaction_functional_error')
        elif not clean:result.update(reward=0.0,category='protocol_timing_error')
        elif result['reset_stages']!=[r[9]%100 for r in aborts] or result['sequence']!=[case['sequence']] or result['reset_offsets']!=[r[9]//100 for r in aborts]:result['reason']='Required scenario was not executed'
        elif len(result['latency_samples'])!=completed or any(not (0<=x['accept_to_setup']<=16 and 0<=x['completion_to_valid']<=16) for x in result['latency_samples']):result['reason']='Latency observation incomplete or inconsistent'
        elif any(x['waits']!=(r[6] if target(r[1])>=0 else 0) or x['stalls']!=(0 if case['ready_mode']=='early' else r[7]+1) for x,r in zip(result['latency_samples'],[r for r in rows if not r[9]])):result['reason']='Observed wait/backpressure does not match requested stimulus'
        else:result.update(reward=1.0,category='pass')
    else:result['reason']='Incomplete or unclassified simulation'
    return result

def grade(source,out,public=False,reuse_build=None,cases=None,seed=20261124,trusted_controls=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);source=Path(source)
    result={'reward':None,'category':'infrastructure_error','public':public,'source_sha256':None,'cases':[],'verification_complete':False}
    def save():
        result['verdict_determinate']=result['reward'] is not None
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
    try:
        result['source_sha256']=sha(source)
        if not trusted_controls:
            rejected=source_policy(source)
            if rejected:
                result.update(category='invalid_submission',reason=rejected);return save()
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
        local=cfg.get('execution')=='local'
        ssh=[] if local else ['ssh','-F',cfg['ssh_config'],cfg['host']]
        selected=cases if cases is not None else suite(public,17 if public else seed)
        if not selected or any(not c['rows'] for c in selected):raise ValueError('Empty suite/case is not a valid evaluation')
        (out/'cases.json').write_text(json.dumps(selected,indent=2))
        result['suite_sha256']=sha(out/'cases.json');result['required_cases']=[c['name'] for c in selected]
        inputs={p.name:sha(p) for p in (ROOT/'verifier/task002').glob('*.sv')};inputs['candidate']=sha(source)
        def run(command,timeout):
            child_env={k:os.environ[k] for k in ('PATH','HOME','LANG','SSH_AUTH_SOCK') if k in os.environ}
            p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=child_env)
            return p.returncode,p.stdout.decode(errors='replace')
        def shell(command,timeout):return run((['/bin/bash','-lc',command] if local else ssh+[command]),timeout)
        def copy(files,remote):
            if local:
                import shutil
                for f in files:shutil.copyfile(str(f),remote+'/'+Path(f).name)
            else:
                rc,log=run(['scp','-F',cfg['ssh_config'],*map(str,files),cfg['host']+':'+remote+'/'],60)
                if rc:raise RuntimeError('SCP failed')
        remote=cfg['remote_root']+'/'+uuid.uuid4().hex
        rc,log=shell('mkdir -p '+shlex.quote(remote),30)
        if rc:raise RuntimeError('Runtime setup failed')
        (out/'runtime.json').write_text(json.dumps({'remote':remote,'inputs':inputs}))
        (out/'bridge.sv').write_bytes(source.read_bytes())
        if reuse_build:
            prior=json.loads((Path(reuse_build)/'backend.json').read_text())
            if prior['inputs']!=inputs:raise RuntimeError('Compiled inputs changed')
            # ldd verified that this VCS build loads generated libraries from
            # simv.daidir. Do not duplicate compiler intermediates or old runtime logs.
            assets=' '.join(shlex.quote(prior['remote']+'/'+name) for name in ('simv','simv.daidir','bridge.sv','tb.sv','vip.sv'))
            rc,log=shell('cp -a '+assets+' '+shlex.quote(remote+'/'),120)
            if rc:raise RuntimeError('Build copy failed')
            result['compile_reused']=True
        else:
            copy([out/'bridge.sv',ROOT/'verifier/task002/tb.sv',ROOT/'verifier/task002/vip.sv'],remote)
            inc=' '.join('+incdir+'+shlex.quote(cfg[k]+s) for k in ('vip_root','axi_vip_root') for s in ('/include/sverilog','/src/sverilog/vcs'))
            cache=(' -Mlib='+shlex.quote(cfg['compile_cache'])) if cfg.get('compile_cache') else ''
            defines=' +define+SVT_AXI_MAX_WVALID_DELAY=128 +define+SVT_AXI_MAX_ADDR_VALID_DELAY=128 +define+SVT_AXI_MAX_ADDR_DELAY=128 +define+SVT_AXI_MAX_ARVALID_DELAY=128 +define+SVT_AXI_MAX_RREADY_DELAY=128 +define+SVT_AXI_MAX_WRITE_RESP_DELAY=128 +define+SVT_APB_MAX_DATA_WIDTH=32 +define+SVT_APB_MAX_ADDR_WIDTH=32 +define+SVT_AXI_MAX_DATA_WIDTH=32 +define+SVT_AXI_MAX_ADDR_WIDTH=32 +define+UVM_PACKER_MAX_BYTES=1500000 +define+UVM_DISABLE_AUTO_ITEM_RECORDING +define+SVT_AXI_MAX_NUM_MASTERS_1 +define+SVT_AXI_MAX_NUM_SLAVES_1 +define+SVT_APB_MAX_NUM_SLAVES_1 '
            cmd='source ~/.bashrc; cd '+shlex.quote(remote)+'; timeout 1500 vcs -full64 -sverilog -ntb_opts uvm -timescale=1ns/1ps'+cache+defines+'+incdir+. '+inc+' bridge.sv tb.sv -top tb -o simv > compile.log 2>&1; r=$?; cat compile.log; exit $r'
            rc,log=shell(cmd,1530);(out/'compile.log').write_text(log);result['compile_exit']=rc
            if rc:
                errors=re.findall(r'Error-\[.*?(?=\nError-|\Z)',log,re.S)
                if errors and all('bridge.sv' in e[:300] for e in errors) and not re.search(r'LICENS|Cannot find',log):result.update(reward=0.0,category='compile_error')
                return save()
        (out/'backend.json').write_text(json.dumps({'remote':remote,'inputs':inputs},indent=2))
        for c in selected:
            directory=out/c['name'];directory.mkdir()
            (directory/'vectors.txt').write_text(''.join('%d %08x %08x %x %d %d %d %d %d %d %d\n'%tuple(row) for row in c['rows']))
            copy([directory/'vectors.txt'],remote)
            selection=' +variant='+str(cfg['variant']) if 'variant' in cfg else ''
            if c['ready_mode']=='early':selection+=' +PB_READY_EARLY'
            cmd='source ~/.bashrc; export DESIGNWARE_HOME='+shlex.quote(cfg['designware_home'])+'; cd '+shlex.quote(remote)+'; timeout 600 ./simv +ntb_random_seed=17 +UVM_MAX_QUIT_COUNT=1 +UVM_VERBOSITY=UVM_NONE +PB_SEQUENCE='+shlex.quote(c['sequence'])+selection+' > simulation.log 2>&1; r=$?; cat simulation.log; exit $r'
            rc,log=shell(cmd,630);(directory/'simulation.log').write_text(log)
            verdict=interpret(log,rc,c);verdict.update(name=c['name'],requirements=c['requirements'])
            (directory/'result.json').write_text(json.dumps(verdict,indent=2)+'\n');result['cases'].append(verdict)
            print(json.dumps({'case':c['name'],'reward':verdict['reward'],'category':verdict['category']}),flush=True)
            if verdict['reward']!=1:
                result.update(reward=verdict['reward'],category=verdict['category'],failed_case=c['name']);return save()
        result.update(reward=1.0,category='pass',verification_complete=True,
                      planned=sum(c['scoreboard']['planned'] for c in result['cases']),
                      checked=sum(c['scoreboard']['checked'] for c in result['cases']),
                      aborted=sum(c['scoreboard']['aborted'] for c in result['cases']))
        result['latency_summary']={}
        for c in result['cases']:
            samples=c['latency_samples']
            result['latency_summary'][c['name']]={k:{'min':min(x[k] for x in samples),'max':max(x[k] for x in samples),'mean':sum(x[k] for x in samples)/len(samples)} for k in ('accept_to_setup','completion_to_valid','waits','stalls')}
        cross=[c for c in result['cases'] if c['name'].startswith('strobe_cross')]
        if not public and cross:
            expected={'target=%d strobe=%d order=%d error=%d wait=%d stall=%d'%(t,s,o,e,w,b) for t in range(3) for s in range(16) for o in range(3) for e in range(2) for w in range(3) for b in range(2)}
            observed=set(b for c in cross for b in c['cross_bins'])
            missing=sorted(expected-observed)
            result['functional_cross']={'required':len(expected),'observed':len(observed&expected),'missing':missing}
            if missing:result.update(reward=None,category='infrastructure_error',verification_complete=False,reason='Required functional cross bins not observed')
    except Exception as e:result['reason']=type(e).__name__+': '+str(e)[:200]
    return save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--public',action='store_true');p.add_argument('--case');p.add_argument('--reuse');p.add_argument('--cases-file');a=p.parse_args()
    selected=[c for c in suite(a.public) if c['name']==a.case] if a.case else None
    if a.case and not selected:p.error('Unknown case')
    if a.cases_file:
        if a.case or a.public:p.error('--cases-file is a private/full suite input, separate from --case/--public')
        selected=json.loads(Path(a.cases_file).read_text())
    result=grade(a.source,a.out,a.public,reuse_build=a.reuse,cases=selected)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))
