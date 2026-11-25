"""Task003 queue/arbiter VCS/VIP campaign; transaction reference model is UVM."""
import argparse,hashlib,json,os,re,shlex,subprocess,uuid
from pathlib import Path
from .scenarios import suite,REQUIRED_BINS
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
    planned=len(case['rows'])+len(case.get('recovery',[]));stage=case.get('reset_stage',0)
    result={'reward':None,'category':'infrastructure_error','simulation_exit':rc,'planned':planned,
            'failures':re.findall(r'^PBQ_ERROR (.*)',log,re.M)[:12],
            'timing_failures':re.findall(r'UVM_ERROR[^\n]*\[PB_TIMING\] (.*)',log)[:12]}
    count=re.search(r'PBQ_RESULT planned=(\d+) axi=(\d+) apb=(\d+) checked=(\d+) aborted=(\d+) aborted_apb=(\d+) errors=(\d+)',log)
    credits=re.search(r'PBQ_CREDITS aw=(\d+) w=(\d+) ar=(\d+) retired_w=(\d+) retired_r=(\d+) canceled_aw=(\d+) canceled_w=(\d+) canceled_ar=(\d+) resets=(\d+) grants=(\d+)',log)
    if count:result['scoreboard']=dict(zip(('planned','axi','apb','checked','aborted','aborted_apb','errors'),map(int,count.groups())))
    if credits:result['credits']=dict(zip(('aw','w','ar','retired_w','retired_r','canceled_aw','canceled_w','canceled_ar','resets','grants'),map(int,credits.groups())))
    result['coverage_bins']=sorted(set(re.findall(r'^PBQ_COVER (\S+)',log,re.M)))
    result['reset_observations']=[dict(zip(('stage','canceled','aw','w','ar','apb_completed'),map(int,x))) for x in re.findall(r'^PBQ_RESET stage=(\d+) canceled=(\d+) aw=(\d+) w=(\d+) ar=(\d+) apb_completed=(\d+)',log,re.M)]
    result['sequence']=re.findall(r'^PBQ_SEQUENCE (\S+)',log,re.M)
    result['vip_protocol_errors']=re.findall(r'UVM_ERROR[^\n]*\[(register_fail:AMBA:[^\]]+)\]',log)
    if 'PB_INFRA' in log or re.search(r'Invalid configuration passed|check_packer_max_bytes|LICENSING|license checkout|Failed attempting|UVM_WARNING[^\n]*\[is_valid\][^\n]*Invalid',log,re.I):result['reason']='Initialization or infrastructure failure'
    elif '[PB_TIMING]' in log or result['vip_protocol_errors']:result.update(reward=0.0,category='protocol_timing_error')
    elif '[PB_FUNCTION]' in log:result.update(reward=0.0,category='transaction_functional_error')
    elif 'PBQ_TIMEOUT' in log:result['reason']='Simulation watchdog expired without a classified RTL violation; verification incomplete'
    elif rc==0 and count and credits and 'PBQ_DONE' in log and planned:
        c=result['scoreboard'];q=result['credits'];aborts=result['reset_observations']
        complete=(c['planned']==planned and c['planned']==c['checked']+c['aborted'] and c['axi']==c['checked'] and c['apb']==c['checked']+c['aborted_apb'] and q['retired_w']+q['retired_r']==c['checked'])
        ledger=(q['aw']==q['retired_w']+q['canceled_aw'] and q['w']==q['retired_w']+q['canceled_w'] and q['ar']==q['retired_r']+q['canceled_ar'])
        if c['planned']!=planned:result['reason']='Issued stimulus count differs from the declared case'
        elif not complete or not ledger or c['errors']:result.update(reward=0.0,category='transaction_functional_error')
        elif not re.search(r'UVM_ERROR\s*:\s*0',log) or not re.search(r'UVM_FATAL\s*:\s*0',log):result.update(reward=0.0,category='protocol_timing_error')
        elif result['sequence']!=[case['sequence']] or q['resets']!=int(bool(stage)) or [x['stage'] for x in aborts]!=([stage] if stage else []):result['reason']='Required scenario not executed'
        elif stage and (not (0<c['aborted']<=len(case['rows'])) or sum(x['canceled'] for x in aborts)!=c['aborted'] or any(sum(x[k] for x in aborts)!=q['canceled_'+k] for k in ('aw','w','ar'))):result['reason']='Reset accounting does not match scenario'
        elif stage in (3,4,5,6) and c['aborted_apb']!=0:result.update(reward=0.0,category='transaction_functional_error')
        elif stage in (7,8) and c['aborted_apb']!=1:result.update(reward=0.0,category='transaction_functional_error')
        elif not stage and (c['aborted'] or c['aborted_apb'] or any(q[k] for k in ('canceled_aw','canceled_w','canceled_ar'))):result['reason']='Unexpected abort without reset'
        elif not stage and (q['aw']!=sum(r[0] for r in case['rows']+case.get('recovery',[])) or q['w']!=q['aw'] or q['ar']!=planned-q['aw']):result['reason']='Requested traffic not observed'
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
        inputs={p.name:sha(p) for p in (ROOT/'verifier/task003').glob('*.sv')};inputs['candidate']=sha(source)
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
            assets=' '.join(shlex.quote(prior['remote']+'/'+name) for name in ('simv','simv.daidir','bridge.sv','tb.sv','vip.sv','scoreboard.sv'))
            rc,log=shell('cp -a '+assets+' '+shlex.quote(remote+'/'),120)
            if rc:raise RuntimeError('Build copy failed')
            result['compile_reused']=True
        else:
            copy([out/'bridge.sv',ROOT/'verifier/task003/tb.sv',ROOT/'verifier/task003/vip.sv',ROOT/'verifier/task003/scoreboard.sv'],remote)
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
            (directory/'vectors.txt').write_text('%d %d %d\n'%(c.get('reset_stage',0),len(c['rows']),len(c.get('recovery',[])))+''.join('%d %08x %08x %x %d %d %d %d %d %d\n'%tuple(row) for row in c['rows']+c.get('recovery',[])))
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
        if not public:
            observed=set(x for c in result['cases'] for x in c['coverage_bins'])
            missing=sorted(REQUIRED_BINS-observed)
            result['functional_cross']={'required':len(REQUIRED_BINS),'observed':len(observed&REQUIRED_BINS),'missing':missing,'kind':'requirement_bins_not_cartesian_cross'}
            if missing:result.update(reward=None,category='infrastructure_error',verification_complete=False,reason='Required queue stimulus/coverage was not observed')
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
