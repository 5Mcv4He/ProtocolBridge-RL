"""Separate bounded VIP laboratory. Never used by terminal grade()."""
import argparse,hashlib,importlib.util,json,os,re,signal,subprocess,sys,time
from pathlib import Path
from verifier.task003.scenarios import suite
from verifier.task003.campaign import source_policy
from environment.engineering_tools import inspect_public,INVARIANTS
ROOT=Path(__file__).resolve().parents[1]
SIGNALS=('rst_n awvalid awready awaddr wvalid wready wdata wstrb arvalid arready araddr bvalid bready bresp rvalid rready rdata rresp psel penable pwrite paddr pwdata pstrb pready prdata pslverr').split()
WIDTHS=[1,1,1,32,1,1,32,4,1,1,32,1,1,2,1,1,32,2,1,1,1,32,32,4,1,32,1]
PUBLIC={c['name']:c for c in suite(True,17)}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cases(request):
    if not isinstance(request,dict):raise ValueError('Invalid request')
    if set(request)=={'scenario'} and isinstance(request['scenario'],str) and request['scenario'] in PUBLIC:return [PUBLIC[request['scenario']]]
    if set(request)!={'transactions'}:raise ValueError('Unknown laboratory fields')
    rows=request['transactions']
    if not isinstance(rows,list) or not 1<=len(rows)<=16:raise ValueError('Expected 1..16 transactions')
    for row in rows:
        if not isinstance(row,list) or len(row)!=10 or any(type(v)!=int for v in row):raise ValueError('Invalid row')
        for v,limit in zip(row,[1,2**32-1,2**32-1,15,64,64,64,64,1,64]):
            if not 0<=v<=limit:raise ValueError('Out of range')
        if row[1]%4:raise ValueError('Address alignment')
    return [{'name':'custom','sequence':'queue_memory_sequence','rows':rows,'recovery':[],
             'reset_stage':0,'requirements':[],'ready_mode':'reactive'}]

def timeline(log):
    samples=[];first_error=None;credits=[0,0,0];limited=False
    for line in log.splitlines():
        if line.startswith('PBR1 '):
            fields=line.split()[1:]
            if len(fields)!=29:raise ValueError('Malformed observation')
            cycle,phase=map(int,fields[:2])
            if not 0<=cycle<4096 or phase not in (0,1):raise ValueError('Invalid observation coordinates')
            pins=[]
            for value,width in zip(fields[2:],WIDTHS):
                if not re.fullmatch('[0-9a-fA-FxXzZ]+',value):raise ValueError('Invalid pin value')
                n=None if re.search('[xz]',value,re.I) else int(value,16)
                if n is not None and not 0<=n<2**width:raise ValueError('Pin overflow')
                pins.append(n)
            p=dict(zip(SIGNALS,pins));events=[]
            if phase==0:
                if p['rst_n']==0:credits=[0,0,0];events=['reset']
                elif p['rst_n']==1:
                    for i,(name,valid,ready) in enumerate([('AW','awvalid','awready'),('W','wvalid','wready'),('AR','arvalid','arready')]):
                        if p[valid]==1 and p[ready]==1:credits[i]+=1;events.append(name)
                    for name,valid,ready in [('B','bvalid','bready'),('R','rvalid','rready')]:
                        if p[valid]==1 and p[ready]==1:
                            events.append(name)
                            if name=='B':credits[0]-=1;credits[1]-=1
                            else:credits[2]-=1
                    if p['psel']==1:
                        if p['penable']==0:events.append('APB_SETUP')
                        elif p['penable']==1:events.append('APB_COMPLETE' if p['pready']==1 else 'APB_WAIT')
            samples.append({'cycle':cycle,'phase':'post' if phase else 'pre','pins':pins,'events':events,'unretired':list(credits)})
        elif line=='PBR_LIMIT':limited=True
        elif first_error is None and ('PBQ_ERROR ' in line or re.search(r'UVM_(?:ERROR|FATAL).*\[',line)):
            if samples and not limited:first_error={'cycle':samples[-1]['cycle'],'phase':samples[-1]['phase']}
    if not samples:raise ValueError('Missing runtime observations')
    return {'signals':SIGNALS,'samples':samples,'first_error':first_error,'capture_limit_cycles':4096,
            'truncated':limited}

def observation(record,detail,start=None,count=12):
    if record.get('status') not in ('PASS','FAIL','ENV_ERROR','INVALID'):return {'status':'ENV_ERROR'}
    out={'status':record['status']}
    if not detail:return out
    digest=record.get('source_sha256')
    invariant=record.get('invariant');known={code:message for code,message in INVARIANTS.values()}
    out.update(source_sha256=digest if isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest) else None,
               invariant={'code':invariant['code'],'message':known[invariant['code']]} if isinstance(invariant,dict) and invariant.get('code') in known else None)
    trace=record.get('timeline')
    if trace is None:return out
    samples=trace['samples'];end=trace['first_error']
    if start is None:
        anchor=end['cycle'] if end else samples[-1]['cycle'];start=max(0,anchor-count//2)
    rows=[]
    for s in samples:
        if not start<=s['cycle']<start+count:continue
        if type(s['cycle'])!=int or s['phase'] not in ('pre','post') or len(s['pins'])!=len(SIGNALS) or len(s['unretired'])!=3:raise ValueError('Invalid sample')
        if any(v is not None and (type(v)!=int or not 0<=v<2**w) for v,w in zip(s['pins'],WIDTHS)):raise ValueError('Invalid pin')
        if any(type(v)!=int or not -8192<=v<=8192 for v in s['unretired']):raise ValueError('Invalid ledger')
        rows.append({'cycle':s['cycle'],'phase':s['phase'],'pins':list(s['pins']),
                     'events':[v for v in s['events'] if v in ('reset','AW','W','AR','B','R','APB_SETUP','APB_COMPLETE','APB_WAIT')],
                     'unretired':list(s['unretired'])})
        if len(rows)==24:break
    if end is not None:
        if type(end.get('cycle'))!=int or not 0<=end['cycle']<4096 or end.get('phase') not in ('pre','post'):raise ValueError('Invalid error coordinate')
        end={k:end[k] for k in ('cycle','phase')}
    out.update(signals=SIGNALS,rows=rows,first_error=end,capture_limit_cycles=4096,truncated=bool(trace['truncated']))
    return out

def worker(source,out,request,reuse):
    # A fresh subprocess owns this copy. The original grader and files are untouched.
    out=Path(out);overlay=out/'overlay/verifier/task003';overlay.mkdir(parents=True)
    for name in ('tb.sv','vip.sv','scoreboard.sv'):
        text=(ROOT/'verifier/task003'/name).read_text()
        if name=='tb.sv':
            needle='if(sb!=null) begin sb.before_edge();#1;sb.after_edge();end'
            assert text.count(needle)==1
            text=text.replace(needle,'pb_observe(0); if(sb!=null) begin sb.before_edge();#1;pb_observe(1);sb.after_edge();end')
            text=text.replace(' bridge dut(.*);',(ROOT/'environment/runtime/observer.sv').read_text()+'\n bridge dut(.*);')
        (overlay/name).write_text(text)
    spec=importlib.util.spec_from_file_location('verifier.task003._laboratory',ROOT/'verifier/task003/campaign.py')
    backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend);backend.ROOT=out/'overlay'
    from environment.verification_timing import measured_grade
    r=measured_grade(backend.grade,source,out/'grade',measurement_backend=backend,public=True,cases=cases(request),reuse_build=reuse)
    result={'source_sha256':sha(source),'status':'ENV_ERROR','invariant':None,'timeline':None,'reward':None}
    if r.get('reward') is not None:
        result['status']='PASS' if r['reward']==1 else 'FAIL'
        result['invariant']=inspect_public(r).get('invariant')
        logs=list((out/'grade').glob('*/simulation.log'))
        if logs:result['timeline']=timeline(logs[0].read_text())
        elif r.get('category')!='compile_error':result['status']='ENV_ERROR'
    result['verifier_result_sha256']=sha(out/'grade/result.json')
    result['observer_sha256']=sha(ROOT/'environment/runtime/observer.sv')
    (out/'internal.json').write_text(json.dumps(result,indent=2)+'\n')

def run(source,out,request,reuse=None):
    selected=cases(request) # Strict validation before creating output or running anything.
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);source=Path(source)
    (out/'bridge.sv').write_bytes(source.read_bytes());source=out/'bridge.sv'
    (out/'request.json').write_text(json.dumps(request))
    record={'status':'ENV_ERROR','source_sha256':sha(source),'reward':None};start=time.monotonic()
    try:
        if source.stat().st_size>40000 or source_policy(source):record['status']='INVALID';return record
        # This module executes inside the trusted Linux backend, never the solver.
        config_path=Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).resolve()
        cfg=json.loads(config_path.read_text())
        if cfg.get('execution')!='local':raise ValueError('Laboratory requires trusted backend execution')
        env={k:os.environ[k] for k in ('HOME','PATH','LANG','PB_CONFIG') if k in os.environ}
        env['PB_CONFIG']=str(config_path)
        def limits():
            import resource
            resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024**2,128*1024**2))
            resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
        with (out/'controller.log').open('w') as log:
            args=[sys.executable,'-m','environment.runtime_tools','--worker',str(source),str(out),str(out/'request.json')]
            if reuse:args+=['--reuse',reuse]
            p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,preexec_fn=limits)
            try:rc=p.wait(timeout=240)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rc=124
        if rc==0:record=json.loads((out/'internal.json').read_text())
        record['exit_code']=rc
    except Exception as e:record['exception_type']=type(e).__name__
    finally:
        record['wall_seconds']=round(time.monotonic()-start,4)
        (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('source');p.add_argument('out');p.add_argument('request');p.add_argument('--reuse');a=p.parse_args()
    if a.worker:worker(a.source,a.out,json.loads(Path(a.request).read_text()),a.reuse)
    else:print(json.dumps(observation(run(a.source,a.out,json.loads(Path(a.request).read_text()),a.reuse),True),indent=2))
