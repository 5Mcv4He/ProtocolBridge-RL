"""One offline entry for trusted, source-matched family rollout evidence.

A capsule is trusted project source, never an untrusted executable plugin. This
adapter validates identity and dependency hashes before selecting its auditor.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from task_families.package import verify


def export(package,experiment,out):
    package=Path(package).resolve();experiment=Path(experiment).resolve();out=Path(out).resolve()
    capsule=verify(package);record=json.loads((experiment/'experiment.json').read_text())
    if record['task_id']!=capsule['task_id']:raise ValueError('Task identity mismatch')
    runtime={k:v for k,v in record['source_files'].items() if k.split('/')[0] in ('environment','verifier','fixtures','tasks','scripts','tests')}
    if not runtime:raise ValueError('Missing source dependency binding')
    for name,value in runtime.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not (package/p).is_file():raise ValueError('Invalid frozen dependency')
        if hashlib.sha256((package/p).read_bytes()).hexdigest()!=value:raise ValueError('Execution and capsule differ: '+name)
    exporter=ROOT/'scripts/rollout_exchange_v5.py'
    code="import importlib.util,sys;sys.path.insert(0,sys.argv[1]);s=importlib.util.spec_from_file_location('pb_exchange',sys.argv[2]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.export([sys.argv[3]],sys.argv[4])"
    subprocess.run([sys.executable,'-c',code,str(package),str(exporter),str(experiment),str(out)],cwd=package,check=True)
    binding={'schema':'pb-capsule-exchange-binding-v1','task_id':capsule['task_id'],
             'capsule_manifest_sha256':hashlib.sha256((package/'family-manifest.json').read_bytes()).hexdigest(),
             'experiment_sha256':hashlib.sha256((experiment/'experiment.json').read_bytes()).hexdigest(),
             'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'auditor_sha256':hashlib.sha256((package/'scripts/audit_policy.py').read_bytes()).hexdigest(),
             'exchange_manifest_sha256':hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest()}
    (out/'source-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    return binding

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',required=True);p.add_argument('--experiment',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(export(a.package,a.experiment,a.out),indent=2))
