"""Audit actual control artifacts; this is one layer, never full task admission.

Replaying the frozen parser checks record consistency, not the parser's semantic
independence. Positive/negative controls and occupancy anchors supply separate
bounded challenges. No simulation results are reused as new grading runs.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from environment.control_bank import bundle
from task_families.router_v2.generate import verify
from .toolchain import observed,check

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(package,evidence):
    package=Path(package).resolve();evidence=Path(evidence).resolve();manifest=verify(package)
    control=evidence/'controls';freeze=json.loads((control/'freeze.json').read_text());report=json.loads((control/'result.json').read_text())
    meta=json.loads((package/'tasks'/manifest['task_id']/'task.json').read_text());q=meta['quality']
    if manifest.get('qualification_revision')!=2 or report.get('schema')!='router-instance-controls-v2':raise ValueError('Unsupported qualification revision')
    if report.get('controls_passed') is not True or report.get('scope')!='complete_instance_controls':raise ValueError('Incomplete or failed controls')
    if freeze['manifest_sha256']!=sha(package/'family-manifest.json') or report['freeze_sha256']!=sha(control/'freeze.json'):raise ValueError('Freeze identity differs')
    if freeze['driver_sha256']!=sha(package/'task_families/router_v3/qualification_v2.py'):raise ValueError('Qualifier source differs')
    sources=q['references']+[n['source'] for n in q['negative_controls']]
    if freeze['control_sources']!={s:sha(package/s) for s in sources}:raise ValueError('Control sources differ')
    bank=control/'control_bank.sv'
    if sha(bank)!=freeze['control_bank_sha256'] or bank.read_text()!=bundle([package/s for s in sources]):raise ValueError('Bank is not the declared control set')
    expected=[(i,'reference-%d-%s'%(i,role),role=='public',1) for i in range(len(q['references'])) for role in ('full','public')]
    expected += [(i+len(q['references']),'negative-%02d'%i,False,0) for i in range(len(q['negative_controls']))]
    if len(expected)!=len(report['rows']):raise ValueError('Incomplete control roster')
    role_inputs={};versions=[];simulations=0
    for row,(index,label,public,reward) in zip(report['rows'],expected):
        if row['label']!=label or row['source']!=sources[index]:raise ValueError('Control identity mismatch')
        dest=control/label;r=json.loads((dest/'result.json').read_text());cfg=json.loads((control/(label+'-config.json')).read_text())
        if sha(dest/'result.json')!=row['result_sha256'] or cfg['variant']!=index:raise ValueError('Result/variant binding mismatch')
        if r['source_sha256']!=sha(bank) or (dest/'bridge.sv').read_bytes()!=bank.read_bytes():raise ValueError('Executed source differs')
        if r['public'] is not public or r['reward']!=reward:raise ValueError('Incorrect evaluation role or verdict')
        if reward==0 and r['category'] not in ('transaction_functional_error','protocol_timing_error'):raise ValueError('Negative was not functionally rejected')
        cases=json.loads((dest/'cases.json').read_text());byname={c['name']:c for c in cases}
        if len(byname)!=len(cases) or r['suite_sha256']!=sha(dest/'cases.json'):raise ValueError('Input identity mismatch')
        if not r['cases']:raise ValueError('No simulation activity')
        if reward==1:
            if r['verification_complete'] is not True or [c['name'] for c in r['cases']]!=[c['name'] for c in cases]:raise ValueError('Positive suite incomplete')
            role='public' if public else 'full';prior=role_inputs.setdefault(role,cases)
            if prior!=cases:raise ValueError('Legal controls used different inputs')
            if not public:
                if not set(q['required_requirements'])<={t for c in cases for t in c['requirements']}:raise ValueError('Missing required scenarios')
                cross=r.get('functional_cross',{})
                if cross.get('required')!=q['required_cross_bins'] or cross.get('observed')!=q['required_cross_bins'] or cross.get('missing')!=[]:raise ValueError('Missing required observed cross')
        for case in r['cases']:
            saved=json.loads((dest/case['name']/'result.json').read_text())
            if saved!=case or case['name'] not in byname:raise ValueError('Per-case record mismatch')
            log=(dest/case['name']/'simulation.log').read_text();identity=observed(log);check(identity,cfg['toolchain']);versions.append(identity);simulations+=1
    # The interpreter is loaded in a fresh process from the verified capsule,
    # avoiding Python module-cache collisions between different task packages.
    code='''import json,sys
from pathlib import Path
from verifier.task002.campaign import interpret
root=Path(sys.argv[1]);count=0
for row in json.loads((root/'result.json').read_text())['rows']:
 d=root/row['label'];r=json.loads((d/'result.json').read_text());cases={c['name']:c for c in json.loads((d/'cases.json').read_text())}
 for saved in r['cases']:
  log=(d/saved['name']/'simulation.log').read_text();parsed=interpret(log,saved['simulation_exit'],cases[saved['name']])
  if any(saved.get(k)!=v for k,v in parsed.items()):raise ValueError('Frozen parser replay differs')
  count+=1
print(count)
'''
    env={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
    replay=subprocess.run([sys.executable,'-c',code,str(control)],cwd=str(package),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    if replay.returncode or int(replay.stdout)!=simulations:raise ValueError('Simulation record replay failed')
    return {'schema':'router-control-audit-v1','task_id':meta['task_id'],'control_layer_qualified':True,'admitted':False,
            'package_manifest_sha256':sha(package/'family-manifest.json'),'control_report_sha256':sha(control/'result.json'),
            'positive_runs':2*len(q['references']),'negative_controls':len(q['negative_controls']),'simulation_records_replayed':simulations,
            'runtime_identities':list({json.dumps(v,sort_keys=True):v for v in versions}.values()),'auditor_sha256':sha(Path(__file__)),
            'limits':'Runtime/interaction qualification and standalone candidate grading acceptance remain separate. Parser replay is not an independent functional oracle.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('evidence');p.add_argument('out');a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Never overwrite an audit record')
    out.write_text(json.dumps(audit(a.package,a.evidence),indent=2)+'\n')
