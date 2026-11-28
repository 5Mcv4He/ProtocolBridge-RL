"""Per-instance controls v2: explicit public role, unchanged task and grader semantics.

A successful result is one evidence layer, not permission to start a rollout.
Existing completed outputs are never re-scored. Interrupted runs require review.
"""
import argparse, hashlib, json, os, time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path=Path(path);tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def run(out, smoke=False):
    from environment.control_bank import bundle
    from verifier.task002.campaign import grade
    from verifier.task002.scenarios import suite
    root=Path.cwd();out=Path(out).resolve()
    if out.exists():raise ValueError('Do not overwrite or re-score an existing run')
    manifest=json.loads((root/'family-manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(root/name)!=digest:raise ValueError('Package source mismatch')
    meta=json.loads((root/'tasks'/manifest['task_id']/'task.json').read_text());q=meta['quality']
    from environment.task_quality import validate_manifest
    validate_manifest(meta,suite())
    out.mkdir(parents=True)
    cfgpath=Path(os.environ.get('PB_CONFIG',root/'.local/config.json'))
    cfg=json.loads(cfgpath.read_text());original_config=cfgpath.read_bytes()
    sources=q['references']+[n['source'] for n in q['negative_controls']]
    bank=out/'control_bank.sv';bank.write_text(bundle([root/p for p in sources]))
    freeze={'manifest_sha256':sha(root/'family-manifest.json'),'driver_sha256':sha(Path(__file__)),
            'control_bank_sha256':sha(bank),'control_sources':{p:sha(root/p) for p in sources},
            'config_sha256':sha(cfgpath),'mode':'smoke' if smoke else 'complete_instance_controls'}
    write(out/'freeze.json',freeze)
    rows=[];build=None;started=time.monotonic()
    def evaluate(index,label,cases,is_public=False):
        nonlocal build
        localcfg=dict(cfg,variant=index);p=out/(label+'-config.json');write(p,localcfg)
        os.environ['PB_CONFIG']=str(p)
        t=time.monotonic();r=grade(bank,out/label,public=is_public,cases=cases,reuse_build=build,trusted_controls=True)
        elapsed=time.monotonic()-t
        if build is None and (out/label/'backend.json').exists():build=out/label
        row={'source':sources[index],'label':label,'reward':r['reward'],'category':r['category'],
             'verification_complete':r['verification_complete'],'cases_executed':len(r['cases']),
             'wall_seconds':elapsed,'compile_reused':r.get('compile_reused',False),
             'result_sha256':sha(out/label/'result.json')}
        rows.append(row);write(out/'progress.json',rows)
        print(json.dumps(row),flush=True);return r
    try:
        for i,ref in enumerate(q['references']):
            cases=[c for c in suite() if c['name']=='generated_boundaries'] if smoke else suite()
            r=evaluate(i,'reference-%d-full'%i,cases)
            if r['reward']!=1:break
            if not smoke:
                r=evaluate(i,'reference-%d-public'%i,suite(True),is_public=True)
                if r['reward']!=1:break
        if all(r['reward']==1 for r in rows):
            for j,negative in enumerate(q['negative_controls']):
                cases=sorted(suite(),key=lambda c:c['name']!=negative['first_case'])
                r=evaluate(j+len(q['references']),'negative-%02d'%j,cases)
                # Timeout, compile failure and infra failures do not qualify a
                # functional mutation even if legacy grading assigns zero.
                if r['reward']!=0 or r['category'] not in ('protocol_timing_error','transaction_functional_error'):break
    finally:
        os.environ['PB_CONFIG']=str(cfgpath)
        if cfgpath.read_bytes()!=original_config:raise ValueError('Original configuration changed')
    expected=(2 if smoke else 4)+len(q['negative_controls'])
    passed=len(rows)==expected and all((r['reward']==1 if r['label'].startswith('reference') else r['reward']==0 and r['category'] in ('protocol_timing_error','transaction_functional_error')) for r in rows)
    result={'schema':'router-instance-controls-v2','task_id':meta['task_id'],
            'scope':freeze['mode'],'controls_passed':passed,'admitted':False,
            'admission_note':'Runtime/interaction qualification and source-matched layer composition still required',
            'rows':rows,'wall_seconds':time.monotonic()-started,'freeze_sha256':sha(out/'freeze.json')}
    write(out/'result.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    run(a.out,a.smoke)
