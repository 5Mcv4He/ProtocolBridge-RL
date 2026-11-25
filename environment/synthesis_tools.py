"""Bounded synthesis plus opt-in trusted equivalence/teaching measurement.
Solver calls synth_check only; neither formal results nor PPA metrics enter its observation.
"""
import argparse,hashlib,io,json,os,re,shlex,subprocess,tarfile,time,uuid
from pathlib import Path
from environment.synthesis_projection import VERSION,dc_observation,formal_result,measurement_result
from verifier.task003.campaign import source_policy
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'environment/synthesis'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(source,out,equivalence=False,measure=False,equivalence_netlist=None):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    r={'version':VERSION,'source_sha256':sha(source),'observation':{'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False},'formal':None,'measurement':None,'reward':None}
    (out/'bridge.sv').write_bytes(source.read_bytes())
    source=out/'bridge.sv'
    r['source_sha256']=sha(source)
    start=time.monotonic()
    try:
        if source.stat().st_size>40000 or source_policy(source):
            r['observation']['status']='INVALID';return r
        if equivalence_netlist is not None and not equivalence:raise ValueError('Trusted implementation override requires equivalence')
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
        env=cfg.get('eda_env_script')
        if not isinstance(env,str) or not env.startswith('/') or any(c in env for c in '\x00\n\r'):raise ValueError('Explicit administrator environment entry required')
        local=cfg.get('execution')=='local';remote=cfg['remote_root']+'/synthesis-'+uuid.uuid4().hex
        files={name:ASSETS/name for name in ('runner.py','dc.tcl','fm.tcl','pt.tcl','constraints.tcl')}
        files.update({'bridge.sv':source,'projection.py':ROOT/'environment/synthesis_projection.py'})
        if equivalence_netlist is not None:files['override.v']=Path(equivalence_netlist)
        request={'equivalence':bool(equivalence),'measure':bool(measure)}
        r['frozen_inputs']={n:sha(p) for n,p in files.items()};r['requested']=request
        r['controller_sha256']=sha(__file__)
        def shell(cmd,timeout,input=None):
            cmd='source '+shlex.quote(env)+' || exit 125; '+cmd
            args=['bash','-lc',cmd] if local else ['ssh','-F',cfg['ssh_config'],cfg['host'],'bash -lc '+shlex.quote(cmd)]
            child={k:os.environ[k] for k in ('HOME','PATH','LANG','SSH_AUTH_SOCK') if k in os.environ}
            return subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,env=child)
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w') as tar:
            for name,p in files.items():tar.add(str(p),arcname=name)
            raw=json.dumps(request).encode();info=tarfile.TarInfo('request.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        setup=shell('umask 077; mkdir -p '+shlex.quote(remote)+' && tar -xf - -C '+shlex.quote(remote),30,data.getvalue())
        if setup.returncode:raise RuntimeError('Setup failed')
        execution=shell('cd '+shlex.quote(remote)+' || exit 125; export PB_EDA_ENV_SCRIPT='+shlex.quote(env)+'; ulimit -c 0; ulimit -f 32768; ulimit -v 2097152; python3 runner.py',430)
        r['runner_exit']=execution.returncode
        # Only fixed own outputs are collected, never a tool/library installation tree.
        collect="python3 -c "+shlex.quote("import io,sys,tarfile; from pathlib import Path; t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|'); [t.add(n,arcname=n) for n in ['execution.json','dc.log','fm.log','pt.log','mapped.v','mapped.sdc','mapping.svf'] if Path(n).is_file()]; t.close()")
        fetched=shell('cd '+shlex.quote(remote)+' && '+collect,40)
        if fetched.returncode:raise RuntimeError('Evidence collection failed')
        with tarfile.open(fileobj=io.BytesIO(fetched.stdout),mode='r:') as tar:
            allowed={'execution.json','dc.log','fm.log','pt.log','mapped.v','mapped.sdc','mapping.svf'}
            for member in tar.getmembers():
                if member.name not in allowed or not member.isfile() or member.size>16*1024**2:raise ValueError('Unexpected evidence member')
                (out/member.name).write_bytes(tar.extractfile(member).read())
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        if execution.returncode or not (out/'execution.json').exists():return r
        record=json.loads((out/'execution.json').read_text());r['execution']=record
        if record['binding_before']!=record['binding_after']:raise RuntimeError('Environment or library changed during run')
        expected=cfg.get('expected_synthesis_binding')
        if expected is not None and any(record['binding_before'].get(k)!=v for k,v in expected.items()):raise RuntimeError('Synthesis environment differs from frozen batch')
        for stage in record['stages']:
            name=stage['stage'];log=(out/(name+'.log')).read_text()
            if name=='dc':r['observation']=dc_observation(log,stage['exit_code'],(out/'mapped.v').exists())
            elif name=='fm':r['formal']=formal_result(log,stage['exit_code'])
            elif name=='pt':r['measurement']=measurement_result(log,stage['exit_code'])
        if r['measurement'] is not None and (out/'dc.log').exists():
            values=re.findall(r'^Total cell area:\s+([0-9.eE+-]+)',(out/'dc.log').read_text(),re.M)
            if len(values)==1:r['measurement']['reported_cell_area']=float(values[0])
            r['measurement']['area_units']='library-defined teaching area units'
        r['evidence_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='deployment.json'}
    except Exception as e:
        r['exception_type']=type(e).__name__
        r['observation']={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
    finally:
        r['wall_seconds']=round(time.monotonic()-start,4)
        (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    return r

def synth_check(source,out):return run(source,out)['observation']
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--equivalence',action='store_true');p.add_argument('--measure',action='store_true');p.add_argument('--equivalence-netlist');a=p.parse_args()
    r=run(a.source,a.out,a.equivalence,a.measure,a.equivalence_netlist)
    print(json.dumps({k:r[k] for k in ('observation','formal','measurement','reward','wall_seconds')},indent=2))

def environment_binding(config):
    """Operator-only batch freeze. No environment values or library bytes returned."""
    from environment.remote_backend import remote_command
    env=config.get('eda_env_script')
    if not isinstance(env,str) or not env.startswith('/'):raise ValueError('Administrator environment entry required')
    code="import hashlib,json,os; from pathlib import Path; print(json.dumps({'library_sha256':hashlib.sha256(Path(os.environ['CLASS_DB']).read_bytes()).hexdigest(),'environment_script_sha256':hashlib.sha256(Path("+repr(env)+").read_bytes()).hexdigest()}))"
    args=['bash','-lc','source '+shlex.quote(env)+' && python3 -c '+shlex.quote(code)] if config.get('execution')=='local' else ['ssh','-F',config['ssh_config'],config['host'],remote_command(config,'python3 -c '+shlex.quote(code))]
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    if p.returncode:raise RuntimeError('EDA environment binding failed')
    result=json.loads(p.stdout)
    if set(result)!={'library_sha256','environment_script_sha256'} or any(not isinstance(v,str) or len(v)!=64 for v in result.values()):raise ValueError('Invalid EDA binding')
    return result
