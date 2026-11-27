"""Bounded independent RTL equivalence, separate from synthesis consistency.

Trusted reference/script are selected by Task ID, never by submitted content.
Raw logs remain in the trusted result directory, not projected to the solver.
"""
import argparse,hashlib,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
ROOT=Path(__file__).resolve().parents[2]
TASKS={k:'accumulator_'+k+'_repair_v1' for k in ('wrap','saturating')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_policy(text):
    s=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
    if len(text.encode())>24000 or not s.strip():return 'empty_or_oversized'
    if any(c in s for c in ('"','`','\\')) or '::' in s:return 'external_construct'
    if re.search(r'\$|\b(initial|final|bind|force|release|import|export|program|class|interface|package|assume|assert|cover)\b',s):return 'unsupported_construct'
    if re.findall(r'\bmodule\s+(\w+)',s)!=['accumulator'] or len(re.findall(r'\bendmodule\b',s))!=1:return 'module_contract'
    if re.search(r'\.\s*[A-Za-z_]',s):return 'hierarchy_or_instance'
    return None

def interpret(log,rc):
    result={'reward':None,'category':'infrastructure_error','equivalent':None,'verification_complete':False,'exit_code':rc}
    def marker(k):return re.findall(r'^'+k+r'=(\S+)\s*$',log,re.M)
    if rc in (124,137):result['category']='proof_timeout';return result
    if rc or re.search(r'license.*(fail|unavailable)|cannot.*check.?out',log,re.I):return result
    if marker('PB_REFERENCE_READ')!=['1'] or marker('PB_REFERENCE_TOP')!=['1']:return result
    if marker('PB_CANDIDATE_READ')==['0'] or marker('PB_CANDIDATE_TOP')==['0']:
        result.update(reward=0.0,category='compile_error');return result
    if re.search(r'^Error:',log,re.M) or marker('PB_REFERENCE_DONE')!=['1']:return result
    if "No 'black boxes' matched current 'reference and implementation designs'" not in log:
        result['category']='incomplete_comparison';return result
    unmatched=re.findall(r'(\d+)\((\d+)\) Unmatched reference\(implementation\) (compare points|primary inputs, black-box outputs)',log)
    if not unmatched or any(int(a) or int(b) for a,b,_ in unmatched):
        result['category']='incomplete_comparison';return result
    passed=[int(x) for x in re.findall(r'(\d+) Passing compare points',log)]
    failed=[int(x) for x in re.findall(r'(\d+) Failing compare points',log)]
    result.update(passing_points=passed[-1] if passed else 0,failing_points=failed[-1] if failed else 0)
    complete=all(x in log for x in ('No unverified compare points.','No aborted compare points.'))
    if marker('PB_REFERENCE_EQ')==['0'] and 'Verification FAILED' in log and result['failing_points']>0:
        result.update(reward=0.0,category='not_equivalent',equivalent=False)
    elif marker('PB_REFERENCE_EQ')==['1'] and 'Verification SUCCEEDED' in log and result['passing_points']>=16 and not result['failing_points'] and complete and 'No failing compare points.' in log:
        result.update(reward=1.0,category='pass',equivalent=True,verification_complete=True)
    else:result['category']='incomplete_comparison'
    return result

def grade(task,source,out):
    if task not in TASKS.values():raise ValueError('Unknown independent-reference task')
    kind=next(k for k,v in TASKS.items() if v==task)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    source=Path(source);ref=ROOT/'fixtures/independent_formal'/('reference_'+kind+'.sv');script=Path(__file__).with_name('proof.tcl')
    result={'task_id':task,'reward':None,'category':'infrastructure_error','verification_complete':False,'source_sha256':sha(source),'reference_sha256':sha(ref),'script_sha256':sha(script),'grader_sha256':sha(__file__),'comparison':'independent_reference_rtl'}
    (out/'candidate.sv').write_bytes(source.read_bytes());start=time.monotonic()
    try:
        invalid=source_policy(source.read_text())
        if invalid:result.update(category='invalid_submission',reason=invalid);return result
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
        remote=cfg['remote_root'].rstrip('/')+'/independent-formal-'+uuid.uuid4().hex
        ssh=['ssh','-F',cfg['ssh_config'],cfg['host']]
        subprocess.run(ssh+[remote_command(cfg,'mkdir -p '+shlex.quote(remote))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
        (out/'reference.sv').write_bytes(ref.read_bytes());(out/'proof.tcl').write_bytes(script.read_bytes())
        subprocess.run(['scp','-F',cfg['ssh_config'],str(out/'candidate.sv'),str(out/'reference.sv'),str(out/'proof.tcl'),cfg['host']+':'+remote+'/'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
        (out/'deployment.json').write_text(json.dumps({'remote':remote}))
        command='cd '+shlex.quote(remote)+' && timeout -k 5 120 fm_shell -64bit -f proof.tcl'
        r=subprocess.run(ssh+[remote_command(cfg,command)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=150)
        log=r.stdout.decode(errors='replace');(out/'formal.log').write_text(log)
        result.update(interpret(log,r.returncode));result['log_sha256']=sha(out/'formal.log')
        versions=re.findall(r'\bO-2018\.06(?:-SP\d+)?\b',log);result['tool_version']=versions[0] if versions else None
    except subprocess.TimeoutExpired:result['category']='infrastructure_timeout'
    except Exception as e:result['exception_type']=type(e).__name__
    finally:
        result['wall_seconds']=round(time.monotonic()-start,4)
        result['verdict_determinate']=result['reward'] is not None
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('source');p.add_argument('out');a=p.parse_args();print(json.dumps(grade(a.task,a.source,a.out),indent=2))
