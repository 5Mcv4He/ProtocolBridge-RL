"""Verify installed runtime identity and run its existing isolation probe.
No administrator policy changes. This does not prove arbitrary-path, network or
native-code adversarial isolation; legacy fixed-path fields are informational.
"""
import hashlib,json,shlex,subprocess,uuid
from pathlib import Path
from environment.remote_backend import remote_command
ROOT=Path(__file__).resolve().parents[1]

def probe(config):
    name='policy-'+uuid.uuid4().hex
    ssh=[] if config.get('execution')=='local' else ['ssh','-F',config['ssh_config'],config['host']]
    def run(command,stdin=None):
        args=['bash','-lc',command] if not ssh else ssh+[remote_command(config,command)]
        r=subprocess.run(args,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=45)
        if r.returncode:raise RuntimeError('Isolation probe execution failed')
        return r.stdout
    expected={'/opt/protocolbridge-runtime/opt/pb/utm_worker.py':hashlib.sha256((ROOT/'environment/utm_worker.py').read_bytes()).hexdigest(),'/usr/local/sbin/pb-sandbox':hashlib.sha256((ROOT/'environment/utm_sandbox.sh').read_bytes()).hexdigest()}
    code='import json,hashlib; from pathlib import Path; x=json.loads(input()); print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in x}))'
    observed=json.loads(run('python3 -c '+shlex.quote(code),json.dumps(expected)+'\n'))
    if observed!=expected:raise RuntimeError('Installed isolation runtime differs from source')
    run('sudo -n install -d -o 1101 -g 1000 -m 0770 /opt/protocolbridge-runtime/work/'+name)
    result=json.loads(run('sudo -n /usr/local/sbin/pb-sandbox /work/'+name,json.dumps({'probe_only':True})+'\n'))['isolation_probe']
    accepted=(result['uid']==1101 and result['pid']==1 and result['chroot_escape_denied'] and result['worker_write_denied'] and result['no_new_privs']=='1' and result['effective_capabilities']=='0000000000000000')
    return {'accepted':accepted,'installed_runtime_hashes_match':True,'installed_worker_probe':result,'scope':'Exact installed worker/launcher hashes, runtime UID/PID/capabilities and denied chroot/worker-write probes. Legacy fixed host-path fields are informational. No exhaustive arbitrary-path, network or native-code adversarial isolation claim.'}
