"""Independent compilation of finite APB register controls, without admission.

Only locally generated, trusted material packages belong in this runner.
The manifest binds inputs; it is not a signature authorizing arbitrary code.
Functional mutations must fail through a functional or timing checker.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from task_families.apb_register_v1.contract import validate, FAMILY
from task_families.apb_register_v1.campaign import grade


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,r):
    p=Path(p);tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(r,indent=2)+'\n');tmp.replace(p)


def inputs(package):
    package=Path(package).resolve();m=read(package/'manifest.json')
    if m.get('schema')!='apb-register-materials-v1' or m.get('family')!=FAMILY:
        raise ValueError('Unsupported material package')
    family=Path(__file__).resolve().parents[1]/'task_families/apb_register_v1'
    producers={n:sha(family/n) for n in ('generate.py','contract.py','verification.py','tb.sv.in')}
    if m.get('producer_files')!=producers:
        raise ValueError('Material producer/checker version differs')
    for name,h in m['files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or (package/p).is_symlink() or sha(package/p)!=h:
            raise ValueError('Material source changed')
    c=validate(read(package/'contract.json'));meta=read(package/'task.json')
    if meta['task_id']!=c['task_id'] or m['task_id']!=c['task_id']:
        raise ValueError('Material identity mismatch')
    expected={'contract.json','task.json','spec.md','workspace/bridge.sv','obligations.json',
              'fixtures/reference.sv','fixtures/reference_packed.sv',
              'verification/register_config.svh','verification/oracle_anchors.svh',
              'verification/tb.sv','verification/public.vec'}
    faults=['alias','ignore_strobe','no_error','bad_reset']
    if c['wait_cycles']:faults.append('no_wait')
    if any(r['access']=='w1c' for r in c['registers']):faults.append('w1c_rw')
    if any(r['access']=='ro' for r in c['registers']):faults.append('ro_write')
    if any(r['access']=='rw' and r['write_mask']!=0xffffffff for r in c['registers']):faults.append('reserved_write')
    negatives=['fixtures/bad_'+f+'.sv' for f in faults]
    expected.update(negatives)
    if set(m['files'])!=expected or meta['references']!=['fixtures/reference.sv','fixtures/reference_packed.sv'] or meta['negative_controls']!=negatives:
        raise ValueError('Missing, extra or inapplicable material dependency')
    if sha(package/'verification/tb.sv')!=sha(family/'tb.sv.in'):
        raise ValueError('Packaged and executed checker differ')
    return c,meta


def accepted(result,positive):
    if positive:return result.get('reward')==1 and result.get('verification_complete') is True
    return result.get('reward')==0 and result.get('category') in ('transaction_functional_error','protocol_timing_error')


def run(package,out,config,seed=37,random_count=24,max_seconds=2400):
    package=Path(package).resolve();out=Path(out).resolve();config=Path(config).resolve()
    if type(max_seconds)!=int or not 120<=max_seconds<=3600:raise ValueError('Bounded job duration required')
    c,meta=inputs(package);out.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__)]+[p for p in Path(__file__).resolve().parents[1].joinpath('task_families/apb_register_v1').iterdir() if p.suffix in ('.py','.in')]
    freeze=dict(schema='apb-register-control-freeze-v1',manifest_sha256=sha(package/'manifest.json'),
                config_sha256=sha(config),sources={str(p.resolve()):sha(p) for p in sources},
                controls={n:sha(package/n) for n in meta['references']+meta['negative_controls']},
                seed=seed,random_count=random_count,max_seconds=max_seconds,compile_reuse=False)
    save(out/'freeze.json',freeze);start=time.monotonic();rows=[];reason=None
    for i,name in enumerate(meta['references']+meta['negative_controls']):
        # A grade is bounded by 600s compilation +120s simulation and margin.
        if time.monotonic()-start+750>max_seconds:reason='remaining_grade_budget';break
        if sha(package/'manifest.json')!=freeze['manifest_sha256'] or sha(config)!=freeze['config_sha256'] or any(sha(p)!=h for p,h in freeze['sources'].items()):
            raise ValueError('Frozen execution dependency changed')
        inputs(package)
        positive=i<len(meta['references']);label='control-%02d'%i
        r=grade(c,package/name,out/label,config,seed,random_count)
        if r['source_sha256']!=freeze['controls'][name]:raise ValueError('Grade source differs from frozen control')
        ok=accepted(r,positive)
        rows.append(dict(label=label,source=name,positive=positive,accepted=ok,
                         reward=r['reward'],category=r['category'],verification_complete=r['verification_complete'],
                         result_sha256=sha(out/label/'result.json'),source_sha256=r['source_sha256'],
                         wall_seconds=r['wall_seconds']))
        save(out/'progress.json',rows);print(json.dumps(rows[-1]),flush=True)
        if not ok:reason='control_outcome_requires_review';break
    passed=len(rows)==len(freeze['controls']) and all(r['accepted'] for r in rows)
    result=dict(schema='apb-register-control-results-v1',task_id=c['task_id'],controls_passed=passed,
                admitted=False,rows=rows,stopped_reason=reason,freeze_sha256=sha(out/'freeze.json'),
                wall_seconds=time.monotonic()-start,scope='Functional controls only; runtime, information boundary and task admission remain separate.')
    save(out/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('out');p.add_argument('config')
    p.add_argument('--max-seconds',type=int,default=2400);a=p.parse_args()
    r=run(a.package,a.out,a.config,max_seconds=a.max_seconds);raise SystemExit(0 if r['controls_passed'] else 1)
