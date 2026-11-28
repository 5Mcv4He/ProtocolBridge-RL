"""Audit concrete control executions across the supported campaign domains.

This replays recorded classifications and source/input bindings; it never creates
new simulation outcomes and never grants runtime or model-sampling admission.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from environment.control_bank import bundle
from task_families.package import verify
from task_families.router_v3.toolchain import observed, check


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())


def audit(package,evidence):
    package=Path(package).resolve();evidence=Path(evidence).resolve();m=verify(package)
    d=evidence/'controls';f=read(d/'freeze.json');r=read(d/'result.json');domain=f['domain']
    if domain not in ('task002','task003') or r.get('schema')!='component-instance-controls-v1' or r.get('controls_passed') is not True:
        raise ValueError('Complete supported control execution required')
    if f['manifest_sha256']!=sha(package/'family-manifest.json') or r['freeze_sha256']!=sha(d/'freeze.json'):
        raise ValueError('Frozen identity mismatch')
    if f['driver_sha256']!=sha(package/'environment/instance_controls.py') or f['campaign_sha256']!=sha(package/'verifier'/domain/'campaign.py'):
        raise ValueError('Qualification source mismatch')
    q=read(package/'tasks'/m['task_id']/'task.json')['quality'];sources=q['references']+[x['source'] for x in q['negative_controls']]
    if f['control_sources']!={s:sha(package/s) for s in sources}:raise ValueError('Control sources differ')
    bank=d/'control_bank.sv'
    if sha(bank)!=f['control_bank_sha256'] or bank.read_text()!=bundle([package/s for s in sources]):raise ValueError('Control bank differs')
    roster=[(i,'reference-%d-%s'%(i,role),role=='public',1) for i in range(len(q['references'])) for role in ('full','public')]
    roster += [(i+len(q['references']),'negative-%02d'%i,False,0) for i in range(len(q['negative_controls']))]
    if len(roster)!=len(r['rows']):raise ValueError('Incomplete control roster')
    versions=[];entries=set();count=0
    for row,(index,label,public,reward) in zip(r['rows'],roster):
        if (row['source'],row['label'],row['public'])!=(sources[index],label,public):raise ValueError('Variant identity mismatch')
        run=d/label;result=read(run/'result.json');cfg=read(d/(label+'-config.json'))
        if sha(run/'result.json')!=row['result_sha256'] or cfg['variant']!=index:raise ValueError('Result binding differs')
        if result['source_sha256']!=sha(bank) or (run/'bridge.sv').read_bytes()!=bank.read_bytes():raise ValueError('Executed source differs')
        if result['reward']!=reward or result['public'] is not public:raise ValueError('Role or reward differs')
        if reward==0 and result['category'] not in ('transaction_functional_error','protocol_timing_error'):raise ValueError('Mutation was not functionally rejected')
        cases=read(run/'cases.json');byname={c['name']:c for c in cases}
        if len(byname)!=len(cases) or sha(run/'cases.json')!=result['suite_sha256'] or not result['cases']:raise ValueError('Missing input/activity')
        if reward==1:
            if not result['verification_complete'] or [c['name'] for c in result['cases']]!=list(byname):raise ValueError('Incomplete positive evaluation')
            if not public:
                cross=result.get('functional_cross',{})
                if cross.get('required')!=q['required_cross_bins'] or cross.get('observed')!=q['required_cross_bins'] or cross.get('missing')!=[]:raise ValueError('Missing actual interaction coverage')
        runtime=read(run/'runtime.json');backend=read(run/'backend.json')
        expected={p.name:sha(p) for p in (package/'verifier'/domain).glob('*.sv')}
        expected.update(candidate=sha(bank),campaign=sha(package/'verifier'/domain/'campaign.py'),build_configuration=hashlib.sha256(json.dumps({k:v for k,v in cfg.items() if k not in ('variant','remote_root')},sort_keys=True).encode()).hexdigest())
        inputs=runtime['inputs']
        if set(inputs)!=set(expected)|{'environment_entry'} or any(inputs[k]!=v for k,v in expected.items()) or backend['inputs']!=inputs or backend['remote']!=runtime['remote']:raise ValueError('Actual build dependencies differ')
        if len(inputs['environment_entry'])!=64:raise ValueError('Missing environment entry identity')
        entries.add(inputs['environment_entry'])
        for actual in result['cases']:
            folder=run/actual['name'];c=byname[actual['name']]
            if read(folder/'result.json')!=actual:raise ValueError('Per-case record differs')
            if domain=='task003':
                vectors='%d %d %d\n'%(c.get('reset_stage',0),len(c['rows']),len(c.get('recovery',[])))
                vectors+=''.join('%d %08x %08x %x %d %d %d %d %d %d\n'%tuple(x) for x in c['rows']+c.get('recovery',[]))
            else:vectors=''.join('%d %08x %08x %x %d %d %d %d %d %d %d\n'%tuple(x) for x in c['rows'])
            if (folder/'vectors.txt').read_text()!=vectors:raise ValueError('Serialized stimulus differs')
            identity=observed((folder/'simulation.log').read_text());check(identity,cfg['toolchain']);versions.append(identity);count+=1
    if len(entries)!=1:raise ValueError('Environment varied within control execution')
    # Load only the verified capsule in a fresh interpreter; reject selected
    # suites that differ from its public/full definitions, not just each other.
    code='''import importlib,json,sys
from pathlib import Path
domain=sys.argv[2];root=Path(sys.argv[1]);campaign=importlib.import_module('verifier.'+domain+'.campaign');suite=importlib.import_module('verifier.'+domain+'.scenarios').suite
m=json.loads(Path('family-manifest.json').read_text());q=json.loads((Path('tasks')/m['task_id']/'task.json').read_text())['quality'];count=0
for row in json.loads((root/'result.json').read_text())['rows']:
 d=root/row['label'];r=json.loads((d/'result.json').read_text());cases=json.loads((d/'cases.json').read_text());expected=suite(row['public'])
 if row['label'].startswith('negative-'):
  n=q['negative_controls'][int(row['label'].split('-')[1])];expected=sorted(expected,key=lambda c:c['name']!=n['first_case'])
 if cases!=expected:raise ValueError('Actual selected inputs differ from frozen scenario generator')
 byname={c['name']:c for c in cases}
 for saved in r['cases']:
  parsed=campaign.interpret((d/saved['name']/'simulation.log').read_text(),saved['simulation_exit'],byname[saved['name']])
  if any(saved.get(k)!=v for k,v in parsed.items()):raise ValueError('Frozen parser replay mismatch')
  count+=1
print(count)
'''
    env={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
    replay=subprocess.run([sys.executable,'-c',code,str(d),domain],cwd=str(package),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    if replay.returncode or int(replay.stdout)!=count:raise ValueError('Frozen input/parser replay failed')
    return dict(schema='component-control-audit-v1',task_id=m['task_id'],domain=domain,control_layer_qualified=True,admitted=False,
                positive_runs=2*len(q['references']),negative_controls=len(q['negative_controls']),simulation_records_replayed=count,
                environment_entry_sha256=entries.pop(),runtime_identities=list({json.dumps(x,sort_keys=True):x for x in versions}.values()),
                package_manifest_sha256=sha(package/'family-manifest.json'),control_report_sha256=sha(d/'result.json'),auditor_sha256=sha(__file__),
                scope='Recorded execution/input/source consistency; not an independent proof of oracle semantics or runtime admission')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('evidence');p.add_argument('out');a=p.parse_args()
    result=audit(a.package,a.evidence)
    with Path(a.out).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
