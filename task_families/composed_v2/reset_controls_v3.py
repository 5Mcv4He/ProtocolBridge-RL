"""Correct response-reset mutation ordering without changing the task or oracle.

The earlier candidate generator placed its injected VALID assignment before an
unconditional reset clear in the same always_ff branch. Those six mutations
were ineffective. Preserve that version; this explicit upgrade creates a new
control-bank version and never inherits industrial evidence.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from task_families.capsule import ROOT,sha,write
from task_families.package import verify
from .generate import once
from .contract import FAMILY


def corrected(reference,target,stage):
    if type(target)!=int or target not in range(3) or stage not in (7,8):
        raise ValueError('Only the six response-reset mutations are revised')
    signal='s_bvalid' if stage==7 else 's_rvalid';direction=1 if stage==7 else 0
    # Put the conditional violation after every normal reset assignment. The
    # pre-edge state/target/direction still identify the interrupted response.
    boundary='   target<=0;paddr<=0;pwdata<=0;pstrb<=0;pwrite<=0;\n  end else begin'
    fault='\n   if(state==RESP && target==%d && pwrite==%d) %s<=1;'%(target,direction,signal)
    return once(reference,boundary,boundary.replace('\n  end else begin',fault+'\n  end else begin'))


def upgrade(parent,out):
    parent,out=Path(parent).resolve(),Path(out).resolve();m=verify(parent)
    if m['family']!=FAMILY or m.get('execution_adapter')!='composed-source-environment-v1' or m.get('control_revision'):
        raise ValueError('Expected original candidate execution capsule')
    if out.exists():raise ValueError('Never overwrite a generated capsule')
    out.mkdir(parents=True)
    for name in m['files']:
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(parent/name),str(p))
    reference=(out/'fixtures/task003/reference.sv').read_text();changes=[]
    for target in range(3):
        for stage in (7,8):
            name='fixtures/task003/bad_reset_t%d_s%d.sv'%(target,stage)
            old=(parent/name).read_text();signal='s_bvalid' if stage==7 else 's_rvalid';direction=1 if stage==7 else 0
            ineffective='state<=IDLE;if(state==RESP && target==%d && pwrite==%d) begin %s<=1; end ac<=0;'%(target,direction,signal)
            if once(old,ineffective,'state<=IDLE;ac<=0;')!=reference:
                raise ValueError('Unexpected original mutation; manual review required')
            p=out/name;p.write_text(corrected(reference,target,stage))
            changes.append(dict(source=name,before_sha256=sha(parent/name),after_sha256=sha(p)))
    meta=out/'tasks'/m['task_id']/'task.json';v=json.loads(meta.read_text());v['control_revision']='reset-last-assignment-v1';write(meta,v)
    write(out/'control-generation-correction.json',dict(schema='composed-control-correction-v1',
        task_contract_changed=False,verifier_semantics_changed=False,
        reason='Later unconditional nonblocking reset assignments masked six intended response-retention faults.',
        changes=changes,industrial_admission='not_run',parent_manifest_sha256=sha(parent/'family-manifest.json')))
    check=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=str(out),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/'.local').mkdir();(out/'.local/control-correction-static.log').write_bytes(check.stdout)
    if check.returncode:raise ValueError('Corrected candidate static checks failed')
    files=dict(m['files'])
    for name in files:files[name]=sha(out/name)
    files['control-generation-correction.json']=sha(out/'control-generation-correction.json')
    result=dict(m,files=files,control_revision='reset-last-assignment-v1',
        control_parent_manifest_sha256=sha(parent/'family-manifest.json'),
        control_upgrade_sources={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'task_families/composed_v2/generate.py',ROOT/'task_families/package.py')},
        status='candidate_not_admitted')
    write(out/'family-manifest.json',result);verify(out);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent');p.add_argument('out');a=p.parse_args()
    print(upgrade(a.parent,a.out)['task_id'])
