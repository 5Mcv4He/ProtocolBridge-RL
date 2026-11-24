"""Trusted controller on UTM. DSH and API calls execute in the sandbox worker.
The host retains the verifier and concrete holdout vectors outside that filesystem.
Compatible with the CentOS host's Python 3.6; the worker uses Python 3.10+.
"""
import argparse,hashlib,json,os,re,select,subprocess,time,uuid
from pathlib import Path
from verifier.campaign import grade
from .reset import ROOT

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def parse_action(text):
    for m in re.finditer(r'\{',text):
        try:action,_=json.JSONDecoder().raw_decode(text[m.start():])
        except ValueError:continue
        if isinstance(action,dict) and action.get('tool') in ('read','edit','test','submit'):return action
    raise ValueError('Return one JSON action; no action was executed')

def run(out,bootstrap):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    runtime=Path('/opt/protocolbridge-runtime');name='trial-'+uuid.uuid4().hex
    work=runtime/'work'/name
    subprocess.run(['sudo','-n','install','-d','-o','1101','-g','1000','-m','0770',str(work)],check=True)
    task=ROOT/'tasks/axil_to_apb4_001'
    for name_file,source in [('spec.md',task/'spec.md'),('bridge.sv',task/'workspace/bridge.sv')]:
        (work/name_file).write_bytes(source.read_bytes());(work/name_file).chmod(0o664)
    frozen={str(p.relative_to(ROOT)):digest(p) for d in ('tasks','verifier','environment','fixtures') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    holdout=Path(bootstrap['private_suite']);private_cases=json.loads(holdout.read_text())
    evaluation=Path(bootstrap['evaluation_suite'])
    manifest={'files':frozen,'private_reward_suite_sha256':digest(holdout),
              'reserved_evaluation_suite_sha256':digest(evaluation)}
    (out/'freeze.json').write_text(json.dumps(manifest,indent=2))
    prompt='''Implement the RTL task using host-dispatched tools. Return one JSON object each turn:
{"tool":"read","file":"spec.md"}, {"tool":"read","file":"bridge.sv"},
{"tool":"edit","content":"complete RTL"}, {"tool":"test"}, {"tool":"submit"}.
Read both files, implement, test and iterate as necessary, then submit. You have at most 20 turns.
Final tests are independent and unavailable. Do not access other files, hierarchy, simulator system tasks or external includes.'''
    trace=[];result={'reward':None,'category':'agent_incomplete'};last_public=None;read_files=set();tested_hash=None
    stderr=(out/'worker-stderr.log').open('w')
    process=subprocess.Popen(['sudo','-n','/usr/local/sbin/pb-sandbox','/work/'+name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,universal_newlines=True,bufsize=1)
    def send(x):process.stdin.write(json.dumps(x)+'\n');process.stdin.flush()
    send({'api_key':bootstrap['api_key'],'model':bootstrap.get('model','deepseek-flash')})
    try:
        for turn in range(20):
            send({'prompt':prompt})
            ready,_,_=select.select([process.stdout],[],[],240)
            if not ready:raise RuntimeError('Model worker timed out')
            line=process.stdout.readline()
            if not line:raise RuntimeError('Model worker ended')
            message=json.loads(line)
            if 'worker_error' in message:raise RuntimeError(message['worker_error'])
            (out/('harness-%02d.json'%turn)).write_text(json.dumps(message,indent=2))
            text=message['response']['final_response'];action={}
            try:
                action=parse_action(text);tool=action['tool']
                if tool=='read' and action.get('file') in ('spec.md','bridge.sv'):
                    read_files.add(action['file']);feedback=(work/action['file']).read_text()
                elif tool=='edit':
                    if read_files!={'spec.md','bridge.sv'}:raise ValueError('Read Spec and initial RTL first')
                    if not isinstance(action.get('content'),str) or len(action['content'])>40000:raise ValueError('Invalid RTL content')
                    (work/'bridge.sv').write_text(action['content']);(out/('candidate-%02d.sv'%turn)).write_text(action['content']);feedback='RTL written'
                elif tool=='test':
                    public=out/('public-%02d'%turn)
                    feedback=grade(work/'bridge.sv',public,public=True)
                    last_public=public if (public/'backend.json').exists() else None
                    tested_hash=digest(work/'bridge.sv')
                elif tool=='submit':
                    if tested_hash!=digest(work/'bridge.sv'):raise ValueError('Run public test on this exact RTL before submitting')
                    if any(digest(ROOT/p)!=h for p,h in frozen.items()) or digest(holdout)!=manifest['private_reward_suite_sha256']:raise RuntimeError('Frozen inputs changed')
                    submission=out/'submission';submission.mkdir();candidate=submission/'bridge.sv';candidate.write_bytes((work/'bridge.sv').read_bytes());candidate.chmod(0o444)
                    (submission/'submission.json').write_text(json.dumps({'sha256':digest(candidate)}))
                    result=grade(candidate,submission/'grade',cases=private_cases,reuse_build=last_public)
                    feedback='Submission accepted. Final evaluation is not returned to the solver.'
                else:raise ValueError('Unsupported tool/file')
            except (ValueError,KeyError) as e:feedback=str(e);action={'tool':'invalid','response':text}
            trace.append({'turn':turn,'action':action,'feedback':feedback});(out/'trace.json').write_text(json.dumps(trace,indent=2))
            print(json.dumps({'turn':turn,'tool':action.get('tool')}),flush=True)
            if action.get('tool')=='submit':break
            prompt=json.dumps({'tool_result':feedback,'protocol_note':'Only the first valid JSON action was executed.'})
        send({'stop':True})
    except Exception as e:result={'reward':None,'category':'infrastructure_error','reason':type(e).__name__+': '+str(e)}
    finally:
        try:process.stdin.close();process.wait(timeout=20)
        except Exception:process.terminate()
        stderr.close()
    # One reserved evaluation, after the solver is stopped. Its verdict is not
    # the episode reward and is never used to edit the submitted candidate.
    candidate=out/'submission/bridge.sv'
    if candidate.exists():
        if digest(evaluation)!=manifest['reserved_evaluation_suite_sha256']:
            audit={'reward':None,'category':'infrastructure_error','reason':'Reserved inputs changed'}
        else:
            audit=grade(candidate,out/'reserved-evaluation',cases=json.loads(evaluation.read_text()),reuse_build=last_public)
        result['reserved_evaluation']={k:audit.get(k) for k in ('reward','category','verification_complete','source_sha256','suite_sha256','planned','checked','aborted')}
    result.update(model=bootstrap.get('model','deepseek-flash'),harness='DeepSeek Harness in UTM',turns=len(trace),
                  freeze_unchanged=all(digest(ROOT/p)==h for p,h in frozen.items()) and digest(holdout)==manifest['private_reward_suite_sha256'] and digest(evaluation)==manifest['reserved_evaluation_suite_sha256'],private_reward_suite_sha256=manifest['private_reward_suite_sha256'])
    (out/'result.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    import sys
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args()
    bootstrap=json.loads(sys.stdin.readline())
    result=run(a.out,bootstrap)
    print(json.dumps({'reward':result['reward'],'category':result['category']}))
