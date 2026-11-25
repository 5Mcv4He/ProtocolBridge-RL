"""Bounded compile and public-checker queries. No shell/tool arguments from solver.

This is not a lint signoff or a simulator for solver-authored testbenches.
All observations are rebuilt from constants/integers; raw logs stay trusted.
"""
import hashlib,json,os,re,shlex,subprocess,time,uuid
from pathlib import Path
from environment.remote_backend import remote_command
from verifier.task003.campaign import source_policy
ROOT=Path(__file__).resolve().parents[1]
VERSION='engineering-tools-v1'
# Exact known public checker messages only. Never copy arbitrary log substrings.
INVARIANTS={
 'Request capacity exceeded':('Q_CAPACITY','Accepted, executing and response-pending requests all occupy the two unretired credits until their AXI response handshake.'),
 'Arbitration or FIFO head mismatch at setup':('Q_HEAD','The APB setup must select the oldest eligible request according to the specified round-robin rule.'),
 'Registered FIFO grant/setup missing':('Q_GRANT','A buffered eligible head at the idle selection edge must produce APB setup immediately after that edge.'),
 'Queued write payload mismatch at setup':('Q_PAYLOAD','APB write data and byte enables must belong to the selected FIFO head.'),
 'Available-credit acceptance exceeded 16 cycles':('Q_ACCEPT','An asserted request with available credit must be accepted within 16 cycles.'),
 'AXI response exceeded 16 cycles':('Q_RESPONSE','An APB completion must produce the corresponding AXI response within 16 cycles.'),
 'AXI response before selected APB completion':('Q_RESPONSE_ORDER','An AXI response requires completion of its corresponding APB access.'),
 'Two responses simultaneously active':('Q_SERIAL','Task003 permits only the selected transaction to present a response.'),
 'APB queued write data/strobe mismatch':('Q_PAYLOAD','Completed APB write data and byte enables must match the selected request.'),
 'RDATA mismatch':('Q_READ_DATA','Read response data must match the value read by its corresponding APB transaction.'),
 'BRESP mismatch':('Q_ERROR','The write response must map the corresponding APB error status.'),
 'RRESP mismatch':('Q_ERROR','The read response must map the corresponding APB error status.'),
 'Unexpected or duplicate AXI completion':('Q_COMPLETION','Each selected transaction must complete exactly once on AXI.'),
 'Request credit ledger mismatch':('Q_LEDGER','Accepted channel requests must equal retired plus reset-canceled requests.'),
}
COMPILER_CODES={'SE':'Syntax error in candidate RTL.','IND':'Undeclared identifier in candidate RTL.',
 'ICPD':'Conflicting procedural drivers in candidate RTL.','URMI':'Unresolved module instantiation.',
 'XMRE':'Unresolved hierarchical reference.','SV-LCM-PND':'Port connection count mismatch.'}

def compiler_projection(log,rc):
    """Unknown exit failures remain ENV_ERROR; warnings never imply correctness."""
    obs={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
    if re.search(r'LICENSING|license checkout.*(?:fail|error)|Failed attempting|Unable to checkout|No such feature|Licensed number of users already reached',log,re.I):return obs
    if rc==0:
        obs['status']='PASS';return obs
    if rc in (124,137,143,-9):return obs
    blocks=re.findall(r'Error-\[([^\]]+)\](.*?)(?=\nError-|\Z)',log,re.S)
    if not blocks:return obs
    # File attribution is essential: host/tool errors cannot become RTL failures.
    if not all(re.search(r'"bridge\.sv",\s*\d+',body[:400]) for _,body in blocks):return obs
    obs['status']='FAIL'
    for code,body in blocks[:4]:
        line=int(re.search(r'"bridge\.sv",\s*(\d+)',body[:400]).group(1))
        obs['diagnostics'].append({'code':code if code in COMPILER_CODES else 'RTL_COMPILE',
                                  'line':min(line,40000),'message':COMPILER_CODES.get(code,'Candidate RTL did not compile.')})
    return obs

def inspect_public(result):
    from environment.task003 import PUBLIC_NAMES
    case=result.get('failed_case')
    if result.get('reward') is None:return {'status':'ENV_ERROR','invariant':None}
    if result.get('reward')==1:return {'status':'PASS','invariant':None}
    obs={'status':'FAIL','case':case if case in PUBLIC_NAMES else None,'invariant':None}
    # Only the first failed public case is eligible, no other cases or private data.
    for c in result.get('cases',[]):
        if c.get('name')!=case:continue
        for message in c.get('failures',[]):
            if isinstance(message,str) and message in INVARIANTS:
                code,explanation=INVARIANTS[message]
                obs['invariant']={'code':code,'message':explanation};return obs
    return obs

def compile_rtl(source,out):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();result={'status':'ENV_ERROR','diagnostics':[],'functional_correctness_checked':False}
    evidence={'version':VERSION,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    try:
        if source.stat().st_size>40000 or source_policy(source):
            result['status']='INVALID';return result
        cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
        local=cfg.get('execution')=='local';ssh=['ssh','-F',cfg['ssh_config'],cfg['host']] if not local else []
        work=cfg['remote_root']+'/compile-'+uuid.uuid4().hex
        def shell(command,timeout,input=None):
            args=ssh+[remote_command(cfg,command)] if ssh else ['bash','-lc',command]
            # Do not forward API secrets to compiler subprocesses.
            env={k:os.environ[k] for k in ('HOME','PATH','LANG','SSH_AUTH_SOCK') if k in os.environ}
            return subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
        made=shell('umask 077; mkdir -p '+shlex.quote(work)+' && cat > '+shlex.quote(work+'/bridge.sv'),30,source.read_bytes())
        if made.returncode:return result
        # No runtime execution; resource limits apply to compiler and descendants.
        command=('source ~/.bashrc; cd '+shlex.quote(work)+' || exit 125; '
                 'ulimit -c 0; ulimit -f 131072; ulimit -v 2097152; '
                 'timeout -k 5 90 vcs -full64 -sverilog +lint=all bridge.sv -top bridge -o simv > compile.log 2>&1; '
                 'rc=$?; head -c 65536 compile.log; exit $rc')
        run=shell(command,115);log=run.stdout.decode(errors='replace')
        (out/'compile.log').write_text(log);evidence.update(exit_code=run.returncode,remote=work)
        result=compiler_projection(log,run.returncode)
    except Exception as e:evidence['exception_type']=type(e).__name__
    finally:
        evidence.update(observation=result,wall_seconds=round(time.monotonic()-started,4))
        (out/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return result
