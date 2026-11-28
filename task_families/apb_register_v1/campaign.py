"""Trusted local VCS runner for source-bound register candidates.

Execute inside a separately provisioned EDA workspace. Every grade compiles independently; this first qualification version does not
reuse binaries. No Agent-controlled commands, alternate checker paths,
library selection or reward
rules are accepted. This runner alone does not qualify the resource or task.
"""
import hashlib,json,re,shlex,subprocess,time
from pathlib import Path
from .contract import validate
from .generate import PORTS
from .verification import scenarios,config_sv,anchors_sv
from .results import compile_result,simulation_result


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,r):Path(p).write_text(json.dumps(r,indent=2)+'\n')

def source_policy(text):
    s=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if not s.strip() or len(text.encode())>24000:return 'empty_or_oversized'
    if any(c in s for c in ('"','`','\\','#','$')) or '::' in s:return 'external_or_simulation_construct'
    if re.search(r'\b(initial|final|bind|force|release|import|export|program|class|interface|package|assume|assert|cover)\b',s):return 'unsupported_construct'
    if re.findall(r'\bmodule\s+(\w+)',s)!=['bridge'] or len(re.findall(r'\bendmodule\b',s))!=1:return 'module_contract'
    if re.search(r'\.\s*[A-Za-z_]',s):return 'hierarchy_or_instance'
    normalize=lambda x:re.sub(r'\b(logic|wire|reg)\b|\s+','',x)
    header=re.match(r'\s*(module\s+bridge\s*\(.*?\)\s*;)',s,re.S)
    return None if header and normalize(header[1])==normalize(PORTS) else 'fixed_interface'


def grade(contract,source,out,config,seed=0,random_count=24,trusted_controls=False,variant=0):
    validate(contract);out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source);config=Path(config)
    if type(variant)!=int or variant<0 or variant>=32 or (not trusted_controls and variant):
        raise ValueError('Only trusted control banks can select variants')
    start=time.monotonic();r=dict(task_id=contract['task_id'],reward=None,category='infrastructure_error',verification_complete=False,
                                 source_sha256=sha(source),grader_sha256=sha(__file__))
    try:
        bad=None if trusted_controls else source_policy(source.read_text())
        if bad:r.update(category='invalid_submission',reason=bad);return r
        cfg=json.loads(config.read_text());entry=Path(cfg['eda_env_script']);vip=Path(cfg['apb_vip_root'])
        if not entry.is_file() or not vip.is_dir():return r
        rows=scenarios(contract,seed,random_count)
        (out/'candidate.sv').write_bytes(source.read_bytes());(out/'tb.sv').write_bytes(Path(__file__).with_name('tb.sv.in').read_bytes())
        (out/'register_config.svh').write_text(config_sv(contract));(out/'oracle_anchors.svh').write_text(anchors_sv(contract))
        (out/'vectors.txt').write_text(''.join('%d %08x %08x %x\n'%tuple(x) for x in rows))
        r.update(input_sha256=sha(out/'vectors.txt'),contract_sha256=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest(),variant=variant)
        identity={n:sha(out/n) for n in ('candidate.sv','tb.sv','register_config.svh','oracle_anchors.svh')}
        identity.update(environment_entry=sha(entry),configuration=sha(config),grader=sha(__file__))
        def execute(argv,cwd,name,limit):
            cmd='source '+shlex.quote(str(entry))+' || exit 125; ulimit -v 4194304; ulimit -f 131072; exec '+ ' '.join(shlex.quote(str(x)) for x in ['timeout','-k','5',str(limit)]+argv)
            t=time.monotonic();p=subprocess.run(['/bin/bash','-lc',cmd],cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit+15)
            log=p.stdout.decode(errors='replace');(out/(name+'.log')).write_text(log)
            r[name+'_wall_seconds']=time.monotonic()-t;r[name+'_exit']=p.returncode;return log,p.returncode
        build=out/'build';build.mkdir()
        argv=['vcs','-full64','-sverilog','-ntb_opts','uvm','-timescale=1ns/1ps',
              '+define+SVT_APB_MAX_DATA_WIDTH=32','+define+SVT_APB_MAX_ADDR_WIDTH=32','+define+SVT_APB_MAX_NUM_SLAVES_1','+define+UVM_DISABLE_AUTO_ITEM_RECORDING',
              '+incdir+'+str(vip/'include/sverilog'),'+incdir+'+str(vip/'src/sverilog/vcs'),'+incdir+'+str(out),
              str(out/'candidate.sv'),str(out/'tb.sv'),'-top','tb','-o','simv']
        log,rc=execute(argv,build,'compile',600)
        if rc:r.update(compile_result(log,rc));return r
        backend=dict(inputs=identity,build=str(build),compiled=True,binary_sha256=sha(build/'simv'));save(out/'backend.json',backend)
        log,rc=execute([str(build/'simv'),'+UVM_VERBOSITY=UVM_NONE','+UVM_MAX_QUIT_COUNT=1','+variant='+str(variant),'+vectors='+str(out/'vectors.txt')],build,'simulation',120)
        transfers=sum(x[0]!=2 for x in rows);resets=1+sum(x[0]==2 for x in rows)
        r.update(simulation_result(log,rc,transfers,resets,transfers*contract['wait_cycles'],len(contract['registers'])))
        r['expected_transfers']=transfers;r['expected_resets']=resets
    except subprocess.TimeoutExpired:r['category']='infrastructure_timeout'
    except Exception as e:r['exception_type']=type(e).__name__
    finally:
        r['wall_seconds']=time.monotonic()-start;save(out/'result.json',r)
    return r

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('source');p.add_argument('out');p.add_argument('config');p.add_argument('--seed',type=int,default=0);p.add_argument('--random-count',type=int,default=24)
    a=p.parse_args();print(json.dumps(grade(json.loads(Path(a.contract).read_text()),a.source,a.out,a.config,a.seed,a.random_count),indent=2))
