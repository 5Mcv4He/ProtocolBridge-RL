"""Reuse the source-explicit EDA adapter for the composed Task003 campaign."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from task_families.capsule import ROOT,sha,write
from task_families.package import verify
from task_families.router_v3.materialize import adapt
from .contract import FAMILY


def adapt_campaign(text):
    inherited="        def shell(command,timeout):return run((['/bin/bash','-lc',remote_command(cfg,command)] if local else ssh+[remote_command(cfg,command)]),timeout)"
    canonical="        def shell(command,timeout):return run((['/bin/bash','-lc',command] if local else ssh+[command]),timeout)"
    if text.count(inherited)!=1:raise ValueError('Unexpected inherited queue deployment wrapper')
    # The common adapter replaces this complete wrapper with an explicit,
    # hashed environment entry. It never runs the intermediate source.
    return adapt(text.replace(inherited,canonical,1))


def materialize(parent,out):
    parent=Path(parent).resolve();out=Path(out).resolve();m=verify(parent)
    if m['family']!=FAMILY:raise ValueError('Expected finite window/queue composition')
    if out.exists():raise ValueError('Never overwrite an execution capsule')
    out.mkdir(parents=True)
    for name in m['files']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(parent/name),str(p))
    p=out/'verifier/task003/campaign.py';p.write_text(adapt_campaign(p.read_text()))
    shutil.copyfile(str(ROOT/'environment/instance_controls.py'),str(out/'environment/instance_controls.py'))
    check=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/'.local').mkdir();(out/'.local/execution-static.log').write_bytes(check.stdout)
    if check.returncode:raise ValueError('Execution checks failed; source preserved')
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and not set(p.relative_to(out).parts)&{'.local','__pycache__'} and p.name!='family-manifest.json'}
    m=dict(m,files=files,parent_manifest_sha256=sha(parent/'family-manifest.json'),
           execution_adapter='composed-source-environment-v1',
           adapter_sources={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'task_families/router_v3/materialize.py',ROOT/'environment/instance_controls.py')})
    write(out/'family-manifest.json',m);verify(out);return m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent');p.add_argument('out');a=p.parse_args()
    print(materialize(a.parent,a.out)['task_id'])
