"""Serial, resumable industrial controls for selected generated capsules.

All output is private operational evidence. This runner grants no runtime
admission, shares no build across instances, and makes no model calls.
"""
import argparse
import hashlib
import io
import json
import shlex
import subprocess
import tarfile
import time
import uuid
from pathlib import Path
from environment.remote_backend import remote_command
from task_families.production_lock import exclusive
from task_families.router_v2.generate import verify, sha
from task_families.router_v3.audit_controls_v2 import audit
from .batch import save

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = (
    'task_families/router_v6/qualify_batch.py', 'task_families/router_v6/batch.py',
    'environment/remote_backend.py', 'environment/control_bank.py',
    'task_families/production_lock.py', 'task_families/router_v2/generate.py',
    'task_families/router_v3/audit_controls.py', 'task_families/router_v3/audit_controls_v2.py',
    'task_families/router_v3/toolchain.py',
)


def runner(seconds):
    return '''import json,os,signal,shutil,subprocess,sys,time
from pathlib import Path
start=time.time();minimum=shutil.disk_usage('.').free
p=subprocess.Popen([sys.executable,'-m','task_families.router_v3.qualification_v2','controls'],start_new_session=True)
reason=None
while p.poll() is None:
 free=shutil.disk_usage('.').free;minimum=min(minimum,free)
 if free<1024**3 or time.time()-start>SECONDS:
  reason='disk_reserve' if free<1024**3 else 'wall_budget'
  os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=20);break
 time.sleep(2)
Path('resource-result.json').write_text(json.dumps({'exit_code':p.returncode,'stopped_reason':reason,'minimum_free_bytes':minimum,'wall_seconds':time.time()-start}))
sys.exit(p.returncode or (1 if reason else 0))
'''.replace('SECONDS', str(seconds))


def run(planfile, configfile, out):
    planfile, configfile, out = Path(planfile).resolve(), Path(configfile).resolve(), Path(out).resolve()
    plan = json.loads(planfile.read_text()); cfg = json.loads(configfile.read_text())
    if set(plan) != {'schema', 'packages', 'budget_seconds', 'selection_sha256'} or plan['schema'] != 'selected-router-controls-v1':
        raise ValueError('Exact bounded plan required')
    if (type(plan['budget_seconds']) is not int or not 0 < plan['budget_seconds'] <= 7200
            or not 1 <= len(plan['packages']) <= 6):
        raise ValueError('Invalid industrial budget')
    identities = set()
    for row in plan['packages']:
        if set(row) != {'path', 'manifest_sha256'} or not Path(row['path']).is_absolute():
            raise ValueError('Explicit package identity required')
        m = verify(row['path'])
        if sha(Path(row['path'])/'family-manifest.json') != row['manifest_sha256']:
            raise ValueError('Package changed')
        if m.get('family') != 'x2p_three_target_router_v5' or m.get('verifier_revision') != 'response-ownership-v1':
            raise ValueError('Current response ownership checker required')
        if m['task_id'] in identities: raise ValueError('Duplicate task')
        identities.add(m['task_id'])
    ssh = ['ssh', '-F', cfg['ssh_config'], cfg['host']]

    def remote(command, data=None, timeout=60):
        p = subprocess.run(ssh+[remote_command(cfg, command)], input=data, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout)
        if p.returncode: raise RuntimeError('Remote operation failed: '+str(p.returncode))
        return p.stdout

    with exclusive(out):
        freeze = dict(plan_sha256=sha(planfile), config_sha256=sha(configfile),
                      controller_sha256=sha(__file__), concurrency=1, model_calls=0,
                      source_files={f:sha(ROOT/f) for f in DEPENDENCIES})
        def unchanged():
            if sha(configfile)!=freeze['config_sha256'] or any(sha(ROOT/f)!=h for f,h in freeze['source_files'].items()):
                raise ValueError('Frozen qualification dependencies changed')
        if (out/'freeze.json').exists():
            if json.loads((out/'freeze.json').read_text()) != freeze: raise ValueError('Changed batch cannot resume')
        else:
            save(out/'freeze.json', freeze); (out/'plan.json').write_bytes(planfile.read_bytes())
            for name in DEPENDENCIES:
                p=out/'sources'/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes((ROOT/name).read_bytes())
        records = []
        for row in plan['packages']:
            unchanged()
            package = Path(row['path']); m = verify(package); tid = m['task_id']; dest = out/tid
            if (dest/'result.json').exists():
                r = json.loads((dest/'result.json').read_text())
                if sha(dest/'evidence.tgz') != r['evidence_sha256']: raise ValueError('Completed archive changed')
                if r['controls_passed'] and audit(package, dest/'evidence') != json.loads((dest/'audit.json').read_text()):
                    raise ValueError('Completed control audit changed')
                records.append(r)
                if not r['controls_passed']: break
                continue
            remaining = plan['budget_seconds'] - sum(r['resource']['wall_seconds'] for r in records)
            if remaining < 120:
                save(out/'budget-stop.json', dict(before_task=tid, remaining_seconds=remaining)); break
            dest.mkdir(exist_ok=True)
            deployment = dest/'deployment.json'
            if not deployment.exists():
                probe = "import json,shutil;from pathlib import Path;busy=[]\nfor p in Path('/proc').glob('[0-9]*/comm'):\n try:\n  if p.read_text().strip() in ('simv','vcs','vcs1','dc_shell','fm_shell'):busy.append(p.parent.name)\n except FileNotFoundError:pass\nassert not busy;assert shutil.disk_usage("+repr(cfg['remote_root'])+").free>4*1024**3"
                remote('python3 -c '+shlex.quote(probe))
                release = cfg['remote_root']+'/router-selected-'+uuid.uuid4().hex
                local = {k: cfg[k] for k in ('vip_root','axi_vip_root','designware_home','eda_env_script','toolchain') if k in cfg}
                local.update(execution='local', remote_root=release+'/builds')
                code = runner(min(1800, int(remaining))); data = io.BytesIO()
                # Local capsules may share immutable source inodes. Transfers
                # materialize their bytes; no cross-package links escape.
                with tarfile.open(fileobj=data, mode='w:gz', dereference=True) as tar:
                    for name in list(m['files'])+['family-manifest.json']: tar.add(str(package/name), arcname=name)
                    for name, raw in [('.local/config.json',json.dumps(local).encode()),('bounded_controls.py',code.encode())]:
                        item=tarfile.TarInfo(name); item.size=len(raw); tar.addfile(item,io.BytesIO(raw))
                save(deployment, dict(release=release, phase='recorded_before_transfer',
                                      runner_sha256=hashlib.sha256(code.encode()).hexdigest()))
                remote('umask 077; mkdir -p '+shlex.quote(release)+' && tar -xzf - -C '+shlex.quote(release),data.getvalue(),90)
                d=json.loads(deployment.read_text()); d['phase']='deployed'; save(deployment,d)
            d=json.loads(deployment.read_text()); release=d['release']
            if d['phase']!='deployed': raise ValueError('Interrupted transfer needs explicit review')
            remote('cd '+shlex.quote(release)+' && python3 -m environment.durable_job',
                   json.dumps(dict(name='controls',module='bounded_controls',args=[])).encode())
            while True:
                state=json.loads(remote('cat '+shlex.quote(release+'/.jobs/controls/state.json')))
                if state['status']=='finished': break
                # A stale running record never authorizes a restart or a verdict.
                probe="from pathlib import Path;p=Path('/proc')/str("+str(state['pid'])+")/'stat';assert p.read_text().split()[21]=="+repr(state['proc_start'])
                remote('python3 -c '+shlex.quote(probe))
                print(json.dumps(dict(task_id=tid,status='running')),flush=True); time.sleep(30)
            code="import os,subprocess;names=[n for n in os.listdir('.') if n not in ('builds','evidence.tgz','__pycache__')];subprocess.run(['tar','--exclude=__pycache__','-czf','evidence.tgz','--']+names,check=True)"
            digest=remote('cd '+shlex.quote(release)+' && python3 -c '+shlex.quote(code)+' && sha256sum evidence.tgz',timeout=90).decode().split()[0]
            archive=dest/'evidence.tgz'; partial=dest/'evidence.part'
            with partial.open('wb') as stream:
                p=subprocess.run(ssh+[remote_command(cfg,'cat '+shlex.quote(release+'/evidence.tgz'))],stdout=stream,stderr=subprocess.PIPE,timeout=180)
            if p.returncode or sha(partial)!=digest: raise ValueError('Evidence transfer mismatch')
            partial.replace(archive)
            with tarfile.open(str(archive)) as tar:
                if any(x.issym() or x.islnk() or Path(x.name).is_absolute() or '..' in Path(x.name).parts for x in tar.getmembers()):
                    raise ValueError('Unsafe archive entry')
                tar.extractall(str(dest/'evidence'))
            resource=json.loads((dest/'evidence/resource-result.json').read_text())
            unchanged()
            resultpath=dest/'evidence/controls/result.json'
            passed=state['exit_code']==0 and resultpath.exists() and json.loads(resultpath.read_text())['controls_passed']
            if passed: save(dest/'audit.json',audit(package,dest/'evidence'))
            record=dict(task_id=tid,controls_passed=bool(passed),admitted=False,
                        evidence_sha256=digest,resource=resource,manifest_sha256=row['manifest_sha256'])
            save(dest/'result.json',record); records.append(record); save(out/'progress.json',records)
            # Only this completed new job's derived builds are removed. Sources,
            # logs, inputs, result archives and audit records remain preserved.
            assert release.startswith(cfg['remote_root']+'/router-selected-')
            remote('python3 -c '+shlex.quote('import shutil;shutil.rmtree('+repr(release+'/builds')+',ignore_errors=False)'))
            save(dest/'cleanup.json',dict(derived_builds_removed=True,evidence_sha256=digest))
            if not passed: break
        result=dict(schema='selected-router-controls-result-v1',planned=len(plan['packages']),
                    completed=len(records),controls_passed=sum(r['controls_passed'] for r in records),
                    admitted=0,rows=records)
        save(out/'result.json',result); return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('config');p.add_argument('out')
    a=p.parse_args();r=run(a.plan,a.config,a.out)
    print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
