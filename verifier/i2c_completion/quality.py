"""Recheck changed starting materials while requiring the unchanged backend gate."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha
from task_families.i2c_completion_v1.generate import scaffold
from task_families.i2c_sink_v1.generate_v2 import rtl,controls
from verification_resources.dependencies import local_import_closure

def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
    def record(mode,name,source,expected,phase='public'):
        p=out/(mode+'-'+name+'.sv');p.write_text(source);task='i2c_completion_'+mode+'_v1'
        r=grade(task,p,out/(mode+'-'+name+'-'+phase),phase)
        ok=r['reward']==expected and (r['category']=='pass' if expected==1 else r['category'] in ('transaction_mismatch','protocol_timing_error'))
        checks.append(dict(task_id=task,control=name,phase=phase,expected_reward=expected,accepted=ok,result=r));print(task,name,phase,r['category'],ok,flush=True)
        (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n')
        if r['reward'] is None:raise RuntimeError('Trusted backend incomplete')
    for mode in ('byte','word'):
        for name,s in [('shift',rtl(mode)),('indexed',rtl(mode,True))]:
            for phase in ('public','terminal','evaluation'):record(mode,name,s,1.,phase)
        record(mode,'missing_delivery',scaffold(),0.)
        record(mode,'ack_regression',controls(mode)['ack_too_early'],0.)
    for n in ('partial_word_crosses_stop','byte_order'):record('word',n,controls('word')[n],0.)
    paths=set(local_import_closure(ROOT,['verifier/i2c_completion/quality.py','task_families/i2c_completion_v1/generate.py']))
    # The immutable backend admission resolves its own complete dependency set.
    backend_gate='experiments/i2c-sink-v1/quality.json';g=json.loads((ROOT/backend_gate).read_text());paths|=set(g['source_files'])|{backend_gate}
    paths|={str(p.relative_to(ROOT)) for m in ('byte','word') for p in (ROOT/'tasks'/('i2c_completion_'+m+'_v1')).rglob('*') if p.is_file()}
    result=dict(schema='i2c-completion-quality-v1',accepted=len(checks)==18 and all(c['accepted'] for c in checks),checks=checks,source_files={p:sha(ROOT/p) for p in sorted(paths)},backend_gate_sha256=sha(ROOT/backend_gate),scope='Same I2C contracts, new scaffold-completion initial materials; no reduction of functional obligations')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
