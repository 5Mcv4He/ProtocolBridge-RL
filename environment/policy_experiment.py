"""Sequential paired fixed-model rollouts, deployed to UTM. No parameter training."""
import argparse,hashlib,io,json,os,shlex,subprocess,tarfile,uuid
from pathlib import Path
from .check_baseline import check
from .policy import load,policy_hash,prompt
from .reset import ROOT
from .remote_backend import remote_command,toolchain_metadata


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


def experiment(out,policies,model,repeats):
    if repeats<1 or len(set(policies))!=len(policies):raise ValueError('Invalid experiment dimensions')
    selected={p:load(p) for p in policies}
    if check()['status']!='pass':raise RuntimeError('Revision 3 baseline drift')
    # Fail before deployment if credential unavailable; never print it.
    key=os.environ['DEEPSEEK_API_KEY']
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    remote_command(cfg, 'true');toolchain_metadata(cfg)
    ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
    base=cfg.get('evaluator_root',str(Path(cfg['remote_root']).parent/'protocolbridge-evaluator'))
    release=base+'/policy-experiments/'+uuid.uuid4().hex
    installed={'/opt/protocolbridge-runtime/opt/pb/utm_worker.py':hashlib.sha256((ROOT/'environment/utm_worker.py').read_bytes()).hexdigest(),
               '/usr/local/sbin/pb-sandbox':hashlib.sha256((ROOT/'environment/utm_sandbox.sh').read_bytes()).hexdigest()}
    code='import hashlib,json,sys; from pathlib import Path; x=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in x.items())'
    subprocess.run(ssh+[remote_command(cfg,'python3 -c '+shlex.quote(code))],input=json.dumps(installed)+'\n',universal_newlines=True,check=True)
    files=[p for d in ('environment','verifier','fixtures','tasks','tests') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
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
    manifest={'toolchain':toolchain_metadata(cfg),'model':model,'repeats':repeats,'policies':{p:{'config':v,'sha256':policy_hash(v),
        'prompt_sha256':hashlib.sha256(prompt(v).encode()).hexdigest()} for p,v in selected.items()},'schedule':schedule,
        'source_commit':source_commit,'source_files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'installed_runtime_files':installed,'pairing':'same reward/evaluation inputs within each repeat; separate split seeds',
        'sampling':'fixed SDK settings; provider temperature/seed defaults, not deterministic',
        'budget_accounting':'Every started public invocation consumes budget, including ENV_ERROR; denied calls do not start verifier.'}
    setup='''import json,random
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
    r=subprocess.run(ssh+[remote_command(cfg,'cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(setup))],input=json.dumps({'config':config,'repeats':repeats})+'\n',universal_newlines=True,stdout=subprocess.PIPE,check=True)
    manifest['paired_suite_hashes']=json.loads(r.stdout)
    (out/'experiment.json').write_text(json.dumps(manifest,indent=2))
    (out/'deployment.json').write_text(json.dumps({'release':release},indent=2))
    def remote(module,args,logname,bootstrap=None):
        command='cd '+shlex.quote(release)+' && python3 -m '+module+' '+' '.join(shlex.quote(a) for a in args)
        with (out/logname).open('w') as log:
            proc=subprocess.Popen(ssh+[remote_command(cfg,command)],stdin=subprocess.PIPE,stdout=log,stderr=log,universal_newlines=True)
            if bootstrap is not None:proc.stdin.write(json.dumps(bootstrap)+'\n')
            proc.stdin.close();return proc.wait()
    def fetch(name):
        subprocess.run(['scp','-q','-F',cfg['ssh_config'],'-r',cfg['host']+':'+release+'/'+name,str(out/name)],check=True)
    def clean_builds():
        # Only this newly-created experiment's disposable compiler products. All raw
        # logs/vectors/source evidence are in trial output dirs and already copied.
        code='import shutil; from pathlib import Path; p=Path('+repr(release)+')/"builds"; shutil.rmtree(str(p)) if p.exists() else None'
        subprocess.run(ssh+[remote_command(cfg,'python3 -c '+shlex.quote(code))],check=True)
    print('Running real deterministic mechanism acceptance in UTM',flush=True)
    rc=remote('environment.policy_mechanism',['mechanism','private/r01-reward.json'],'mechanism-controller.log')
    fetch('mechanism');clean_builds()
    accepted=json.loads((out/'mechanism/result.json').read_text())['accepted']
    if rc or not accepted:raise RuntimeError('Real mechanism acceptance failed; no model trials started')
    for trial in schedule:
        print('Starting '+trial['id'],flush=True)
        rep=trial['repeat']
        bootstrap={'api_key':key,'model':model,'policy':trial['policy'],'source_commit':source_commit,
                   'private_suite':release+'/private/r%02d-reward.json'%rep,
                   'evaluation_suite':release+'/private/r%02d-evaluation.json'%rep}
        rc=remote('environment.policy_utm_agent',[trial['id']],trial['id']+'-controller.log',bootstrap)
        fetch(trial['id'])
        if not (out/trial['id']/'metrics.json').exists():raise RuntimeError('Trial did not produce metrics; retain outputs for inspection')
        clean_builds();summarize(out)
        print('Finished '+trial['id']+' controller_exit='+str(rc),flush=True)
    return summarize(out)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--policies',default='spec_only,test_verdict,test_diagnostic')
    p.add_argument('--model',default='deepseek-flash');p.add_argument('--repeats',type=int,default=1);p.add_argument('--summarize',action='store_true')
    a=p.parse_args()
    r=summarize(a.out) if a.summarize else experiment(a.out,a.policies.split(','),a.model,a.repeats)
    print(json.dumps({k:v for k,v in r.items() if k!='runs'},indent=2))
if __name__=='__main__':main()
