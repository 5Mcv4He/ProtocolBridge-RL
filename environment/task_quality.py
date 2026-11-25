"""Fail-closed task admission gate; preserves every control and resumes by hashes.
Task-owned SV/VIP backends supply functionality. This controller cannot certify
semantic completeness of a Spec or make untested tasks eligible by metadata alone.
"""
import argparse,hashlib,importlib,json,os,subprocess
from pathlib import Path
from environment.control_bank import bundle
ROOT=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,data):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');os.replace(str(tmp),str(p))
def snapshot(task):
    dirs=[task,ROOT/'environment',ROOT/'verifier',ROOT/'fixtures',ROOT/'tests']
    return {str(p.relative_to(ROOT)):digest(p) for d in dirs for p in sorted(d.rglob('*')) if p.is_file() and '__pycache__' not in str(p)}
def validate_manifest(m,cases):
    q=m['quality'];names={c['name'] for c in cases}
    if not isinstance(m.get('version'),int) or m['version']<1 or not m.get('task_id'):raise ValueError('Invalid task identity')
    if len(names)!=len(cases) or not cases:raise ValueError('Duplicate or empty case suite')
    if not isinstance(q.get('minimum_negative_controls'),int) or q['minimum_negative_controls']<3:raise ValueError('At least three negative controls required')
    sources=q['references']+[c['source'] for c in q['negative_controls']]
    if len(set(sources))!=len(sources):raise ValueError('Duplicate control sources')
    requirements={r for c in cases for r in c['requirements']}
    if len(q['references'])<2 or len(q['negative_controls'])<q['minimum_negative_controls']:raise ValueError('Insufficient controls')
    if not set(q['required_requirements'])<=requirements:raise ValueError('Missing requirements in suite')
    if any(c['first_case'] not in names or not c['violation'] for c in q['negative_controls']):raise ValueError('Invalid negative control declaration')
    if not q.get('spec_review',{}).get('blind_spots'):raise ValueError('Spec review/limitations required')
    for p in q['references']+[c['source'] for c in q['negative_controls']]:
        try:(ROOT/p).resolve().relative_to(ROOT)
        except ValueError:raise ValueError('Invalid source path')
        if not (ROOT/p).is_file():raise ValueError('Missing control')
    if len({digest(ROOT/p) for p in sources})!=len(sources):raise ValueError('Duplicate control contents')

def require_admission(task,out):
    task=Path(task).resolve();out=Path(out).resolve()
    result=json.loads((out/'result.json').read_text());frozen=json.loads((out/'freeze.json').read_text())
    metadata=json.loads((task/'task.json').read_text())
    if result.get('accepted') is not True or result.get('task_id')!=metadata['task_id'] or frozen.get('task_id')!=metadata['task_id']:raise ValueError('Task is not admitted')
    config=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    if frozen.get('toolchain',{})!=config.get('toolchain',{}):raise ValueError('Admission toolchain mismatch')
    if result.get('freeze_sha256')!=digest(out/'freeze.json') or frozen['files']!=snapshot(task):raise ValueError('Admission does not match current source')
    return {'task_id':metadata['task_id'],'gate_result_sha256':digest(out/'result.json'),'freeze_sha256':digest(out/'freeze.json')}

def run(task,out,resume=False,seed=20261125):
    task=Path(task).resolve();out=Path(out).resolve();m=json.loads((task/'task.json').read_text());q=m['quality']
    backend=importlib.import_module(m['verifier']);scenarios=importlib.import_module(m['verifier'].rsplit('.',1)[0]+'.scenarios')
    cases=scenarios.suite(False,seed);public=scenarios.suite(True,17);validate_manifest(m,cases)
    cfg_path=Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json'));config=json.loads(cfg_path.read_text())
    freeze={'task_id':m['task_id'],'version':m['version'],'files':snapshot(task),'private_input_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest(),'public_input_sha256':hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest(),'toolchain':config.get('toolchain',{}),'seed':seed}
    if resume:
        if json.loads((out/'freeze.json').read_text())!=freeze:raise ValueError('Gate inputs changed; start a new version/run')
        if (out/'result.json').exists():return json.loads((out/'result.json').read_text())
    else:
        out.mkdir(parents=True,exist_ok=False);write(out/'freeze.json',freeze);write(out/'private-cases.json',cases)
    # Lock is per gate; operator must keep one licensed campaign active globally.
    import fcntl
    lock=(out/'gate.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    entries=[{'source':x,'kind':'positive'} for x in q['references']]+[dict(c,kind='negative') for c in q['negative_controls']]
    source=out/'control_bank.sv'
    if not source.exists():source.write_text(bundle([ROOT/e['source'] for e in entries]))
    results={};compiled=None;original=os.environ.get('PB_CONFIG')
    def control(name,index,selected,is_public=False):
        nonlocal compiled
        dest=out/name
        if (dest/'result.json').exists():r=json.loads((dest/'result.json').read_text())
        elif dest.exists():raise RuntimeError('Incomplete control preserved; do not retry automatically: '+name)
        else:
            cp=out/'deployment.json';write(cp,dict(config,variant=index));os.environ['PB_CONFIG']=str(cp)
            r=backend.grade(source,dest,public=is_public,cases=selected,reuse_build=compiled,trusted_controls=True)
        if (dest/'backend.json').exists():compiled=dest
        results[name]=r;write(out/'progress.json',results)
        return r
    try:
        for i,e in enumerate(entries):
            name=Path(e['source']).stem;selected=list(cases)
            if e.get('first_case'):selected.sort(key=lambda c:c['name']!=e['first_case'])
            r=control(name,i,selected)
            if e['kind']=='positive':
                if r.get('reward')!=1 or not r.get('verification_complete'):raise RuntimeError('Positive control failed: '+name)
                if r.get('functional_cross',{}).get('observed')!=q['required_cross_bins']:raise RuntimeError('Required cross not observed')
                if control(name+'-public',i,public,True).get('reward')!=1:raise RuntimeError('Public positive failed')
            elif r.get('reward')!=0 or r.get('category') not in ('protocol_timing_error','transaction_functional_error','test_timeout'):raise RuntimeError('Negative control not functionally rejected: '+name)
        os.environ['PB_CONFIG']=str(cfg_path)
        from .isolation_probe import probe
        probe_file=out/'isolation.json'
        if probe_file.exists():boundary=json.loads(probe_file.read_text())
        else:boundary=probe(config);write(probe_file,boundary)
        if not boundary.get('accepted'):raise RuntimeError('Isolation boundary probe failed')
        # Initial workspace must be rejected by actual simulation.
        dest=out/'initial'
        if (dest/'result.json').exists():r=json.loads((dest/'result.json').read_text())
        elif dest.exists():raise RuntimeError('Incomplete initial check')
        else:r=backend.grade(task/m['initial_rtl'],dest,public=True)
        results['initial']=r
        if r.get('reward')!=0:raise RuntimeError('Initial template did not produce a confirmed failure')
        mech=out/'mechanism'
        if (mech/'result.json').exists():mr=json.loads((mech/'result.json').read_text())
        elif mech.exists():raise RuntimeError('Incomplete mechanism check')
        else:mr=importlib.import_module(q['mechanism_module']).run(mech,out/'private-cases.json','text-json-atomic-v2')
        if not mr.get('accepted'):raise RuntimeError('Policy mechanism failed')
        # Explicit infrastructure and invalid-language probes cannot earn reward=0.
        invalid=out/'invalid.sv';invalid.write_text('module bridge; initial $finish; endmodule\n')
        broken=out/'broken.sv';broken.write_text((task/m['initial_rtl']).read_text().replace('endmodule','syntax error here; endmodule'))
        for name,src,kind in [('invalid_submission',invalid,'invalid_submission'),('compile_error',broken,'compile_error'),('infrastructure_error',ROOT/q['references'][0],'infrastructure_error')]:
            if name=='infrastructure_error':os.environ['PB_CONFIG']=str(out/'intentionally-missing-config.json')
            d=out/name
            if (d/'result.json').exists():r=json.loads((d/'result.json').read_text())
            elif d.exists():raise RuntimeError('Incomplete classification probe')
            else:r=backend.grade(src,d,public=True)
            results[name]=r
            if r.get('category')!=kind or r.get('reward')!=(0 if name=='compile_error' else None):raise RuntimeError('Classification probe failed: '+name)
        if snapshot(task)!=freeze['files']:raise RuntimeError('Source changed during gate')
        report={'accepted':True,'task_id':m['task_id'],'freeze_sha256':digest(out/'freeze.json'),'positive_count':len(q['references']),'negative_count':len(q['negative_controls']),'mechanism_checks':mr['check_count'],'isolation_probe_accepted':boundary['accepted'],'results':{n:{k:r.get(k) for k in ('reward','category','verification_complete','failed_case','planned','checked','aborted','source_sha256','suite_sha256','functional_cross')} for n,r in results.items()},'limitations':q['spec_review']['blind_spots']}
    except Exception as e:
        report={'accepted':False,'task_id':m['task_id'],'failure':str(e),'completed_controls':list(results),'resume_requires_same_inputs':True}
        write(out/'failure.json',report);return report
    finally:
        if original is None:os.environ.pop('PB_CONFIG',None)
        else:os.environ['PB_CONFIG']=original
    write(out/'result.json',report);return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task');p.add_argument('out');p.add_argument('--resume',action='store_true');p.add_argument('--seed',type=int,default=20261125);a=p.parse_args()
    r=run(a.task,a.out,a.resume,a.seed);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
