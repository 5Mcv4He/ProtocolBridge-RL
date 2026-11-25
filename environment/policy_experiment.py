"""Sequential paired fixed-model rollouts, deployed to a licensed Linux host. No parameter training."""
import argparse,hashlib,io,json,os,shlex,subprocess,tarfile,uuid,time
from pathlib import Path
from .check_baseline import check
from .policy import load,policy_hash,prompt
from .reset import ROOT
from .remote_backend import remote_command,toolchain_metadata
from .batch_contract import experiment_prompt,PROTOCOLS


def check_supervisor_state(state,starting_polls=0):
    """Bound ambiguous startup; never restart a job whose execution is unknown."""
    status=state.get('status')
    if status=='starting':
        if starting_polls>=2:
            raise RuntimeError('Supervisor startup state missing; preserve evidence, do not rerun')
        return starting_polls+1
    if status not in ('running','finished'):
        raise RuntimeError('Unknown supervisor state; preserve evidence, do not rerun')
    if status=='running' and not state.get('alive'):
        raise RuntimeError('Orphaned job; preserve evidence, do not rerun')
    return 0


def summarize(out):
    out=Path(out);manifest=json.loads((out/'experiment.json').read_text());runs=[]
    for trial in manifest['schedule']:
        p=out/trial['id']/'metrics.json'
        if p.exists():runs.append(dict(json.loads(p.read_text()),trial_id=trial['id'],repeat=trial['repeat']))
    groups={}
    for policy in manifest['policies']:
        rows=[r for r in runs if r['policy_id']==policy]
        groups[policy]={'completed_runs':len(rows),'submissions':sum(r['submitted'] for r in rows),
            'reward_1':sum(r['terminal']['reward']==1 for r in rows),'reward_0':sum(r['terminal']['reward']==0 for r in rows),
            'reward_null':sum(r['terminal']['reward'] is None for r in rows),'terminal_rewards':[r['terminal']['reward'] for r in rows],
            'held_out_rewards':[r['held_out']['reward'] if r['held_out'] else None for r in rows]}
    result={'planned_runs':len(manifest['schedule']),'completed_runs':len(runs),'groups':groups,'runs':runs}
    (out/'summary.json').write_text(json.dumps(result,indent=2));return result


def experiment(out,policies,model,repeats,resume=False,limit=None,max_seconds=14400,max_tokens=2000000,starting_rtl=None,protocol=PROTOCOLS[0],task_id='axil_to_apb4_001',admission=None):
    if task_id not in ('axil_to_apb4_001','axil_to_apb4_router_002','axil_to_apb4_queue_003'):raise ValueError('Unsupported task')
    admission_record=None
    if task_id!='axil_to_apb4_001':
        if admission is None:raise ValueError('A matching Task Quality Gate admission is required')
        from .task_quality import require_admission
        admission_record=require_admission(ROOT/'tasks'/task_id,admission)
    scenario_module={'axil_to_apb4_001':'verifier.scenarios','axil_to_apb4_router_002':'verifier.task002.scenarios','axil_to_apb4_queue_003':'verifier.task003.scenarios'}[task_id]
    mechanism_module={'axil_to_apb4_001':'environment.policy_mechanism','axil_to_apb4_router_002':'environment.task002_mechanism','axil_to_apb4_queue_003':'environment.task003_mechanism'}[task_id]
    if protocol not in PROTOCOLS:raise ValueError('Unknown action protocol')
    if repeats<1 or not policies or (limit is not None and (limit<1 or limit>repeats*len(policies))) or max_seconds<=0 or max_tokens<=0 or len(set(policies))!=len(policies):raise ValueError('Invalid experiment dimensions')
    selected={p:load(p) for p in policies}
    if check()['status']!='pass':raise RuntimeError('Revision 3 baseline drift')
    # Fail before deployment if credential unavailable; never print it.
    key=os.environ['DEEPSEEK_API_KEY']
    out=Path(out).resolve()
    if repeats*len(policies)>30:raise ValueError('At most 30 planned trials per batch')
    if not resume:out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    remote_command(cfg, 'true');toolchain_metadata(cfg)
    ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
    if not resume:
        base=cfg.get('evaluator_root',str(Path(cfg['remote_root']).parent/'protocolbridge-evaluator'))
        release=base+'/policy-experiments/'+uuid.uuid4().hex
        installed={'/opt/protocolbridge-runtime/opt/pb/utm_worker.py':hashlib.sha256((ROOT/'environment/utm_worker.py').read_bytes()).hexdigest(),
                   '/usr/local/sbin/pb-sandbox':hashlib.sha256((ROOT/'environment/utm_sandbox.sh').read_bytes()).hexdigest()}
        code='import hashlib,json,sys; from pathlib import Path; x=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in x.items())'
        subprocess.run(ssh+[remote_command(cfg,'python3 -c '+shlex.quote(code))],input=json.dumps(installed)+'\n',universal_newlines=True,check=True)
        files=[p for d in ('environment','verifier','fixtures','tasks','tests') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
        if protocol==PROTOCOLS[1]:files += [ROOT/'scripts'/name for name in ('analyze_policy.py','audit_policy.py','batch_analysis.py','batch_tables.py')]
        archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w:gz') as tar:
            for p in files:tar.add(str(p),arcname=str(p.relative_to(ROOT)))
        subprocess.run(ssh+[remote_command(cfg,'umask 077; mkdir -p '+shlex.quote(release)+'; tar -xzf - -C '+shlex.quote(release))],input=archive.getvalue(),check=True)
        config={k:cfg[k] for k in ('vip_root','axi_vip_root','designware_home','compile_cache') if k in cfg}
        config.update(execution='local',remote_root=release+'/builds')
        schedule=[]
        # Rotate order per paired repetition, fixed before outcomes are observed.
        for rep in range(repeats):
            order=policies[rep%len(policies):]+policies[:rep%len(policies)]
            for policy in order:schedule.append({'id':'r%02d-%s'%(rep+1,policy),'repeat':rep+1,'policy':policy})
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),universal_newlines=True).strip()
        manifest={'task_id':task_id,'task_admission':admission_record,'protocol':protocol,'study':('repair' if starting_rtl else 'independent')+('-v2' if protocol==PROTOCOLS[1] else '-v1'),'quality_watch_after_pilot':protocol==PROTOCOLS[1],'limits':{'max_seconds':max_seconds,'max_tokens':max_tokens},'toolchain':toolchain_metadata(cfg),'model':model,'repeats':repeats,'policies':{p:{'config':v,'sha256':policy_hash(v),
            'prompt_sha256':hashlib.sha256(experiment_prompt(v,bool(starting_rtl),protocol).encode()).hexdigest()} for p,v in selected.items()},'schedule':schedule,
            'source_commit':source_commit,'source_files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'installed_runtime_files':installed,'pairing':'same reward/evaluation inputs within each repeat; separate split seeds',
            'sampling':'fixed SDK settings; provider temperature/seed defaults, not deterministic',
            'budget_accounting':'Every started public invocation consumes budget, including ENV_ERROR; denied calls do not start verifier.'}
        setup='''
    import json,random
    from pathlib import Path
    from verifier.scenarios import suite
    from verifier.campaign import sha
    x=json.loads(input());Path('.local').mkdir();Path('.local/config.json').write_text(json.dumps(x['config']))
    p=Path('private');p.mkdir(mode=0o700);hashes={}
    for rep in range(1,x['repeats']+1):
     hashes[str(rep)]={}
     for split in ('reward','evaluation'):
      seed=random.SystemRandom().getrandbits(64);dest=p/('r%02d-%s.json'%(rep,split))
      dest.write_text(json.dumps(suite(False,seed),indent=2));hashes[str(rep)][split]=sha(dest)
    print(json.dumps(hashes))
    '''
        setup=__import__('textwrap').dedent(setup).replace('from verifier.scenarios import suite','from '+scenario_module+' import suite')
        r=subprocess.run(ssh+[remote_command(cfg,'cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(setup))],input=json.dumps({'config':config,'repeats':repeats})+'\n',universal_newlines=True,stdout=subprocess.PIPE,check=True)
        manifest['paired_suite_hashes']=json.loads(r.stdout)
        if starting_rtl:
            content=Path(starting_rtl).read_bytes();manifest['starting_rtl_sha256']=hashlib.sha256(content).hexdigest()
            subprocess.run(ssh+[remote_command(cfg,'cat > '+shlex.quote(release+'/starting.sv'))],input=content,check=True)
            (out/'starting.sv').write_bytes(content)
        (out/'experiment.json').write_text(json.dumps(manifest,indent=2))
        (out/'deployment.json').write_text(json.dumps({'release':release},indent=2))
    else:
        manifest=json.loads((out/'experiment.json').read_text());release=json.loads((out/'deployment.json').read_text())['release']
        source_commit=manifest['source_commit'];schedule=manifest['schedule']
        if manifest.get('task_id','axil_to_apb4_001')!=task_id or manifest.get('task_admission')!=admission_record:raise ValueError('Resume task/admission mismatch')
        if model!=manifest['model'] or policies!=list(manifest['policies']) or repeats!=manifest['repeats']:raise ValueError('Resume configuration mismatch')
        if protocol!=manifest.get('protocol',PROTOCOLS[0]):raise ValueError('Resume protocol mismatch')
        if (out/'quality-stop.json').exists():raise RuntimeError('This batch stopped at its quality gate; use a separately frozen study')
        for name,digest in manifest['source_files'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen source drift: '+name)
    def remote(module,args,logname,bootstrap=None):
        name=logname.replace('-controller.log','')
        request={'name':name,'module':module,'args':args,'bootstrap':bootstrap or {}}
        command='cd '+shlex.quote(release)+' && python3 -m environment.durable_job'
        subprocess.run(ssh+[remote_command(cfg,command)],input=json.dumps(request)+'\n',universal_newlines=True,check=True,timeout=45)
        probe="import json,os; from pathlib import Path; p=Path('.jobs')/"+repr(name)+"/'state.json'; s=json.loads(p.read_text()) if p.exists() else {'status':'starting'}; q=Path('/proc/'+str(s.get('pid',0))+'/stat'); s['alive']=q.exists() and q.read_text().split()[21]==s.get('proc_start'); print(json.dumps(s))"
        starting_polls=0
        while True:
            r=subprocess.run(ssh+[remote_command(cfg,'cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(probe))],stdout=subprocess.PIPE,universal_newlines=True,check=True,timeout=45)
            state=json.loads(r.stdout);(out/(name+'-job.json')).write_text(json.dumps(state,indent=2))
            print(json.dumps({'job':name,'status':state['status'],'elapsed':round(time.time()-state.get('started',time.time()))}),flush=True)
            starting_polls=check_supervisor_state(state,starting_polls)
            if state['status']=='finished':
                logdir=out/(name+'-job-evidence')
                if not logdir.exists():subprocess.run(['scp','-q','-F',cfg['ssh_config'],'-r',cfg['host']+':'+release+'/.jobs/'+name,str(logdir)],check=True,timeout=60)
                return state.get('exit_code')
            time.sleep(20)
    def fetch(name):
        if (out/name).exists():return
        temp=out/(name+'.partial')
        if temp.exists():
            import shutil;shutil.rmtree(str(temp))
        subprocess.run(['scp','-q','-F',cfg['ssh_config'],'-r',cfg['host']+':'+release+'/'+name,str(temp)],check=True,timeout=180)
        os.replace(str(temp),str(out/name))
    def clean_builds(name):
        # Only this newly-created experiment's disposable compiler products. All raw
        # logs/vectors/source evidence are in trial output dirs and already copied.
        code="import json,shutil; from pathlib import Path; root=Path("+repr(release)+"); builds=root/'builds'; result=root/"+repr(name)+"; paths={json.loads(p.read_text()).get('remote','') for p in result.rglob('runtime.json')}; [shutil.rmtree(str(Path(p)),ignore_errors=True) for p in paths if Path(p).parent==builds and len(Path(p).name)==32]"
        subprocess.run(ssh+[remote_command(cfg,'python3 -c '+shlex.quote(code))],check=True)
    print('Running real deterministic mechanism acceptance on configured backend',flush=True)
    rc=0 if (out/'mechanism/result.json').exists() else remote(mechanism_module,['mechanism','private/r01-reward.json','--protocol',protocol],'mechanism-controller.log')
    fetch('mechanism')
    if not resume:clean_builds('mechanism')
    accepted=json.loads((out/'mechanism/result.json').read_text())['accepted']
    if rc or not accepted:raise RuntimeError('Real mechanism acceptance failed; no model trials started')
    for trial in schedule[:limit]:
        if (out/trial['id']/'metrics.json').exists() or (out/(trial['id']+'-failed.json')).exists():continue
        used=0;elapsed=0
        from scripts.analyze_policy import usage
        for entry in schedule:
            d=out/entry['id']
            if (d/'metrics.json').exists():
                elapsed+=json.loads((d/'metrics.json').read_text()).get('wall_seconds',0)
                used+=(usage(list(d.glob('harness-*.json')))['totals'] or {}).get('totalTokens',0) or 0
        if elapsed>=manifest['limits']['max_seconds'] or used>=manifest['limits']['max_tokens']:raise RuntimeError('Between-trial budget exhausted')
        probe="import json,os,shutil; print(json.dumps({'free_disk_bytes':shutil.disk_usage('.').free,'loadavg':os.getloadavg(),'cpus':os.cpu_count()}))"
        r=subprocess.run(ssh+[remote_command(cfg,'cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(probe))],stdout=subprocess.PIPE,universal_newlines=True,check=True,timeout=30)
        resources=json.loads(r.stdout);(out/(trial['id']+'-resources.json')).write_text(json.dumps(resources))
        if resources['free_disk_bytes']<4*1024**3:raise RuntimeError('Disk reserve below 4 GiB; no trial started')
        print('Starting '+trial['id'],flush=True)
        rep=trial['repeat']
        bootstrap={'task_id':task_id,'api_key':key,'model':model,'policy':trial['policy'],'protocol':protocol,'source_commit':source_commit,
                   'private_suite':release+'/private/r%02d-reward.json'%rep,
                   'evaluation_suite':release+'/private/r%02d-evaluation.json'%rep}
        if 'starting_rtl_sha256' in manifest:bootstrap.update(starting_rtl=release+'/starting.sv',starting_rtl_sha256=manifest['starting_rtl_sha256'])
        rc=remote('environment.policy_utm_agent',[trial['id']],trial['id']+'-controller.log',bootstrap)
        fetch(trial['id'])
        if not (out/trial['id']/'metrics.json').exists():
            (out/(trial['id']+'-failed.json')).write_text(json.dumps({'reward':None,'category':'infrastructure_error','controller_exit':rc,'evidence':trial['id']}))
            raise RuntimeError('Trial ended without metrics; failure preserved, resume will not rerun it')
        clean_builds(trial['id']);summarize(out)
        from scripts.analyze_policy import analyze
        analyze(out)
        print('Finished '+trial['id']+' controller_exit='+str(rc),flush=True)
        completed=summarize(out)['completed_runs']
        if manifest.get('quality_watch_after_pilot') and completed>=9 and completed%len(policies)==0:
            from scripts.batch_analysis import report
            gate=report(out,completed)['quality_gate']
            if not gate['passed']:
                (out/'quality-stop.json').write_text(json.dumps({'completed_runs':completed,'quality_gate':gate,'resume_forbidden':True},indent=2))
                print('Quality gate stopped further trials; all outcomes preserved',flush=True);break
    return summarize(out)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--policies',default='spec_only,test_verdict,test_diagnostic')
    p.add_argument('--model',default='deepseek-flash');p.add_argument('--repeats',type=int,default=1);p.add_argument('--summarize',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--limit',type=int);p.add_argument('--max-seconds',type=int,default=14400);p.add_argument('--max-tokens',type=int,default=2000000);p.add_argument('--starting-rtl')
    p.add_argument('--protocol',choices=PROTOCOLS,default=PROTOCOLS[0])
    p.add_argument('--task',choices=('axil_to_apb4_001','axil_to_apb4_router_002','axil_to_apb4_queue_003'),default='axil_to_apb4_001');p.add_argument('--admission')
    a=p.parse_args()
    import fcntl
    lock=Path(a.out).resolve().with_name(Path(a.out).name+'.lock');lock.parent.mkdir(parents=True,exist_ok=True)
    handle=lock.open('a');fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    r=summarize(a.out) if a.summarize else experiment(a.out,a.policies.split(','),a.model,a.repeats,a.resume,a.limit,a.max_seconds,a.max_tokens,a.starting_rtl,a.protocol,a.task,a.admission)
    print(json.dumps({k:v for k,v in r.items() if k!='runs'},indent=2))
if __name__=='__main__':main()
