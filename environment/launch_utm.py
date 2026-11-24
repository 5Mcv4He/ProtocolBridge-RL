"""Deploy original project sources and launch the Agent inside UTM.
The API key is sent over SSH stdin, never embedded in a command or saved to Git.
"""
import argparse,hashlib,io,json,os,shlex,subprocess,tarfile,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def launch(out,model='deepseek-flash'):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    base=cfg.get('evaluator_root',str(Path(cfg['remote_root']).parent/'protocolbridge-evaluator'))
    release=base+'/releases/'+uuid.uuid4().hex
    ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
    installed={
        '/opt/protocolbridge-runtime/opt/pb/utm_worker.py':hashlib.sha256((ROOT/'environment/utm_worker.py').read_bytes()).hexdigest(),
        '/usr/local/sbin/pb-sandbox':hashlib.sha256((ROOT/'environment/utm_sandbox.sh').read_bytes()).hexdigest()}
    check='import hashlib,json,sys; from pathlib import Path; expected=json.loads(sys.stdin.readline()); assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in expected.items()), "Installed worker/launcher differs; rerun setup"'
    subprocess.run(ssh+['python3 -c '+shlex.quote(check)],input=json.dumps(installed)+'\n',universal_newlines=True,check=True)
    source_files=[p for d in ('environment','verifier','fixtures','tasks') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w:gz') as tar:
        for p in source_files:tar.add(str(p),arcname=str(p.relative_to(ROOT)))
    subprocess.run(ssh+['umask 077; mkdir -p '+shlex.quote(release)+'; tar -xzf - -C '+shlex.quote(release)],input=archive.getvalue(),check=True)
    local_cfg={k:cfg[k] for k in ('remote_root','vip_root','axi_vip_root','designware_home','compile_cache') if k in cfg}
    local_cfg['execution']='local'
    setup='''import json,os,random
from pathlib import Path
from verifier.scenarios import suite
p=Path('.local');p.mkdir(mode=0o700)
config=json.loads(input());(p/'config.json').write_text(json.dumps(config))
private=Path('private');private.mkdir(mode=0o700)
for split in ('reward','evaluation'):
 seed=random.SystemRandom().getrandbits(64)
 (private/(split+'.json')).write_text(json.dumps(suite(False,seed),indent=2))
'''
    code_path=out/'prepare_private.py';code_path.write_text(setup)
    # Keep code and configuration separate from shell interpolation.
    proc=subprocess.run(ssh+['cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(setup)],input=json.dumps(local_cfg)+'\n',universal_newlines=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if proc.returncode:raise RuntimeError('UTM private evaluator preparation failed')
    metadata={'release':release,'source_files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},'model':model,'execution':'UTM','installed_runtime_files':installed}
    (out/'deployment.json').write_text(json.dumps(metadata,indent=2))
    key=os.environ['DEEPSEEK_API_KEY']
    bootstrap={'api_key':key,'model':model,'private_suite':release+'/private/reward.json',
               'evaluation_suite':release+'/private/evaluation.json'}
    command='cd '+shlex.quote(release)+' && python3 -m environment.utm_agent '+shlex.quote(release+'/run')
    with (out/'controller.log').open('w') as log:
        process=subprocess.Popen(ssh+[command],stdin=subprocess.PIPE,stdout=log,stderr=log,universal_newlines=True)
        process.stdin.write(json.dumps(bootstrap)+'\n');process.stdin.close()
        rc=process.wait()
    subprocess.run(['scp','-F',cfg['ssh_config'],'-r',cfg['host']+':'+release+'/run',str(out/'run')],check=True)
    result=json.loads((out/'run/result.json').read_text())
    if rc:result['controller_exit']=rc
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'reward':result.get('reward'),'category':result.get('category'),'turns':result.get('turns')}))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--model',default='deepseek-flash');a=p.parse_args();launch(a.out,a.model)
if __name__=='__main__':main()
