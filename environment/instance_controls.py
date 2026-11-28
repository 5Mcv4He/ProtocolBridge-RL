"""Actual per-instance controls, with explicit grading roles and no admission.

The caller chooses a supported trusted campaign. Candidate code cannot choose
the oracle, control bank, input suite, or reuse identity. Completed outputs are
never overwritten. Infrastructure/compile errors cannot qualify functional bugs.
"""
import argparse
import hashlib
import importlib
import json
import os
import time
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    p=Path(path);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(p)


def run(out, domain):
    if domain not in ('task002','task003'):raise ValueError('Unqualified control campaign domain')
    from environment.control_bank import bundle
    from environment.task_quality import validate_manifest
    campaign=importlib.import_module('verifier.'+domain+'.campaign')
    scenarios=importlib.import_module('verifier.'+domain+'.scenarios')
    root=Path.cwd();out=Path(out).resolve();m=json.loads((root/'family-manifest.json').read_text())
    for name,h in m['files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or (root/p).is_symlink() or sha(root/p)!=h:
            raise ValueError('Changed package input')
    meta=json.loads((root/'tasks'/m['task_id']/'task.json').read_text());q=meta['quality']
    validate_manifest(meta,scenarios.suite())
    if out.exists():raise ValueError('Never overwrite or regrade a control run')
    out.mkdir(parents=True)
    cfgpath=Path(os.environ.get('PB_CONFIG',root/'.local/config.json'));cfg=json.loads(cfgpath.read_text());cfgbytes=cfgpath.read_bytes()
    sources=q['references']+[x['source'] for x in q['negative_controls']]
    bank=out/'control_bank.sv';bank.write_text(bundle([root/f for f in sources]))
    save(out/'freeze.json',dict(domain=domain,manifest_sha256=sha(root/'family-manifest.json'),
         driver_sha256=sha(__file__),campaign_sha256=sha(campaign.__file__),config_sha256=sha(cfgpath),
         control_bank_sha256=sha(bank),control_sources={f:sha(root/f) for f in sources}))
    rows=[];build=None;start=time.monotonic()
    def evaluate(index,label,cases,public=False):
        nonlocal build
        config=out/(label+'-config.json');save(config,dict(cfg,variant=index));os.environ['PB_CONFIG']=str(config)
        t=time.monotonic();r=campaign.grade(bank,out/label,public=public,cases=cases,reuse_build=build,trusted_controls=True)
        if build is None and (out/label/'backend.json').exists():build=out/label
        row=dict(source=sources[index],label=label,public=public,reward=r['reward'],category=r['category'],
                 verification_complete=r['verification_complete'],cases_executed=len(r['cases']),
                 wall_seconds=time.monotonic()-t,compile_reused=r.get('compile_reused',False),result_sha256=sha(out/label/'result.json'))
        rows.append(row);save(out/'progress.json',rows);print(json.dumps(row),flush=True);return r
    try:
        for i in range(len(q['references'])):
            r=evaluate(i,'reference-%d-full'%i,scenarios.suite())
            if r['reward']!=1 or not r['verification_complete']:break
            r=evaluate(i,'reference-%d-public'%i,scenarios.suite(True),True)
            if r['reward']!=1 or not r['verification_complete']:break
        if len(rows)==2*len(q['references']) and all(r['reward']==1 and r['verification_complete'] for r in rows):
            for j,n in enumerate(q['negative_controls']):
                cases=sorted(scenarios.suite(),key=lambda c:c['name']!=n['first_case'])
                r=evaluate(j+len(q['references']),'negative-%02d'%j,cases)
                if r['reward']!=0 or r['category'] not in ('protocol_timing_error','transaction_functional_error'):break
    finally:
        os.environ['PB_CONFIG']=str(cfgpath)
        if cfgpath.read_bytes()!=cfgbytes:raise ValueError('Original configuration changed')
    expected=2*len(q['references'])+len(q['negative_controls'])
    passed=len(rows)==expected and all((r['reward']==1 and r['verification_complete']) if r['label'].startswith('reference') else (r['reward']==0 and r['category'] in ('protocol_timing_error','transaction_functional_error')) for r in rows)
    result=dict(schema='component-instance-controls-v1',task_id=m['task_id'],domain=domain,
                controls_passed=bool(passed),admitted=False,rows=rows,wall_seconds=time.monotonic()-start,
                freeze_sha256=sha(out/'freeze.json'),scope='Actual functional control layer only; runtime qualification is separate')
    save(out/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--domain',required=True,choices=('task002','task003'))
    a=p.parse_args();r=run(a.out,a.domain);raise SystemExit(0 if r['controls_passed'] else 1)
