"""Industrial controls for the intersection of behavior and synthesizability."""
import argparse,json
from pathlib import Path
from .campaign import ROOT,sha,grade
from task_families.bitfold_synth_v1.generate import rtl,initial,controls
from verification_resources.dependencies import local_import_closure

def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
    def record(mode,name,source,expected,phase='public',category=None,anchor=False,reference=False):
        task='bitfold_'+mode+'_repair_v1';p=out/(mode+'-'+name+'.sv');p.write_text(source)
        r=grade(task,p,out/(mode+'-'+name+'-'+phase),phase,anchor_only=anchor,reference_only=reference)
        ok=r['reward']==expected and (category is None or r['category']==category)
        checks.append(dict(task_id=task,control=name,phase=phase,expected_reward=expected,expected_category=category,accepted=ok,result=r))
        (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(task,name,phase,r['category'],ok,flush=True)
        if r['reward'] is None and category!='invalid_submission':raise RuntimeError('Trusted validation incomplete')
    for mode in ('population','trailing_zero'):
        for name,s in [('bounded',rtl(mode)),('alternate',rtl(mode,True))]:
            for phase in ('public','terminal','evaluation'):record(mode,name,s,1.,phase,category='pass')
        record(mode,'initial_function',initial(mode),1.,category='pass',anchor=True)
        for name,s in controls(mode).items():
            record(mode,name,s,0.,category='synthesis_error' if name=='data_dependent_loop' else 'transaction_mismatch')
        for name in ('wrong_bit','wrong_boundary'):
            record(mode,name+'-reference',controls(mode)[name],0.,category='not_equivalent',reference=True)
    ref=rtl('population')
    record('population','empty','',None,category='invalid_submission')
    record('population','width',ref.replace('[3:0]','[7:0]'),None,category='invalid_submission')
    record('population','syntax',ref.replace('result=0;','result=;'),0.,category='compile_error')
    paths=set(local_import_closure(ROOT,['verifier/bitfold_synth/quality.py','task_families/bitfold_synth_v1/generate.py']))
    paths|={str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob('*.tcl')}
    paths|={str(p.relative_to(ROOT)) for mode in ('population','trailing_zero') for p in (ROOT/'tasks'/('bitfold_'+mode+'_repair_v1')).rglob('*') if p.is_file()}
    result=dict(schema='bitfold-synthesis-quality-v1',accepted=len(checks)==31 and all(c['accepted'] for c in checks),checks=checks,source_files={p:sha(ROOT/p) for p in sorted(paths)},scope='Two eight-bit combinational operations; exhaustive two-state semantics, independent-reference and own-netlist equivalence; no PPA reward')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
