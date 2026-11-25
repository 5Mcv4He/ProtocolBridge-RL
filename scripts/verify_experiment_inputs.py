"""Validate frozen rollout reward/evaluation inputs with a known positive control.
Research-side check only; never changes Agent rewards or observations.
"""
import argparse,hashlib,importlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def frozen_inputs(root):
    root=Path(root);m=json.loads((root/'experiment.json').read_text());items=[]
    for rep,hashes in sorted(m['paired_suite_hashes'].items(),key=lambda x:int(x[0])):
        for split,h in sorted(hashes.items()):
            suffix='submission/grade/cases.json' if split=='reward' else 'reserved-evaluation/cases.json'
            matches=[p for p in root.glob('r%02d-*/%s'%(int(rep),suffix)) if sha(p)==h]
            if not matches:raise ValueError('Missing exact frozen input: round '+rep+' '+split)
            items.append({'name':'r%02d-%s'%(int(rep),split),'sha256':h,'path':matches[0]})
    if not items:raise ValueError('No frozen inputs')
    return m,items

def run(root,out,resume=False):
    m,items=frozen_inputs(root);task=m.get('task_id','axil_to_apb4_001')
    if task not in ('axil_to_apb4_001','axil_to_apb4_router_002','axil_to_apb4_queue_003','axil_to_apb4_decoupled_004'):raise ValueError('Unknown experiment task')
    if task=='axil_to_apb4_001':module='verifier.campaign';reference=ROOT/'fixtures/reference.sv'
    else:
        meta=json.loads((ROOT/'tasks'/task/'task.json').read_text());module=meta['verifier'];reference=ROOT/meta['quality']['references'][0]
    frozen_files={k:v for k,v in m['source_files'].items() if k.startswith('verifier/') or k.startswith('tasks/'+task+'/') or k==str(reference.relative_to(ROOT))}
    if any(not (ROOT/p).is_file() or sha(ROOT/p)!=h for p,h in frozen_files.items()):raise ValueError('Verifier or reference changed since experiment')
    from environment.remote_backend import toolchain_metadata
    cfg=json.loads(Path(os.environ.get('PB_CONFIG',ROOT/'.local/config.json')).read_text())
    if toolchain_metadata(cfg)!=m.get('toolchain',{}):raise ValueError('Experiment toolchain changed')
    backend=importlib.import_module(module)
    frozen={'qualification_code_sha256':sha(__file__),'toolchain':toolchain_metadata(cfg),'experiment_sha256':sha(Path(root)/'experiment.json'),'reference_sha256':sha(reference),'files':frozen_files,'input_sha256':{x['name']:x['sha256'] for x in items}}
    out=Path(out)
    if resume:
        if json.loads((out/'freeze.json').read_text())!=frozen:raise ValueError('Input qualification freeze mismatch')
    else:out.mkdir(parents=True,exist_ok=False);(out/'freeze.json').write_text(json.dumps(frozen,indent=2)+'\n')
    results={};reuse=None
    for x in items:
        dest=out/x['name']
        if (dest/'result.json').exists():r=json.loads((dest/'result.json').read_text())
        elif dest.exists():raise RuntimeError('Incomplete qualification preserved; do not rerun automatically')
        else:r=backend.grade(reference,dest,cases=json.loads(x['path'].read_text()),reuse_build=reuse)
        results[x['name']]={k:r.get(k) for k in ('reward','category','verification_complete','source_sha256','suite_sha256','planned','checked','aborted','functional_cross')}
        (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
        if (dest/'backend.json').exists():reuse=dest
        if r.get('reward')!=1 or not r.get('verification_complete') or r.get('suite_sha256')!=x['sha256']:break
    result={'accepted':len(results)==len(items) and all(r['reward']==1 and r['verification_complete'] and r['suite_sha256']==frozen['input_sha256'][n] for n,r in results.items()),'task_id':task,'freeze_sha256':sha(out/'freeze.json'),'results':results,'scope':'Actual positive-control simulation of the exact frozen inputs; post-hoc research-side qualification, no candidate rescoring or solver feedback.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');p.add_argument('--resume',action='store_true');a=p.parse_args();r=run(a.root,a.out,a.resume);print(json.dumps(r,indent=2));raise SystemExit(0 if r['accepted'] else 1)
