"""Actual positive/negative gate; no example-level evidence inheritance."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha,TASK
from verification_resources.dependencies import local_import_closure

def dependencies():
    files=set(local_import_closure(ROOT,['verifier/swd_read/quality.py']))
    files.add('verifier/swd_read/tb.sv')
    files.update(str(p.relative_to(ROOT)) for p in (ROOT/'tasks'/TASK).rglob('*') if p.is_file())
    return {f:sha(ROOT/f) for f in sorted(files)}

def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[];sources=dependencies();task=ROOT/'tasks'/TASK
    (out/'freeze.json').write_text(json.dumps(sources,indent=2)+'\n')
    def record(name,source,expected,phase='public',category=None):
        result=grade(TASK,source,out/(name+'-'+phase),phase)
        ok=result['reward']==expected and result['category']==category
        if expected==1:ok=ok and result['verification_complete'] and result['activity']['reads']==48
        checks.append(dict(task_id=TASK,control=name,phase=phase,accepted=ok,expected_reward=expected,result=result))
        (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(name,phase,result['category'],ok,flush=True)
        if result['category'].startswith('infrastructure'):raise RuntimeError('Stop on infrastructure fault')
    for name in ('reference','alternate'):
        for phase in ('public','terminal','evaluation'):record(name,task/(name+'.sv'),1.,phase,'pass')
    kinds={'data_msb_first':'transaction_mismatch','live_data':'transaction_mismatch','stale_latch':'transaction_mismatch'}
    for f in sorted((task/'controls').glob('*.sv')):record(f.stem,f,0.,category=kinds.get(f.stem,'protocol_timing_error'))
    record('initial',task/'workspace/target.sv',0.,category='protocol_timing_error')
    ref=(task/'reference.sv').read_text()
    for name,src,expected,cat in [('empty','',None,'invalid_submission'),('interface',ref.replace('[31:0] read_value','[30:0] read_value'),None,'invalid_submission'),('spoof',ref.replace('endmodule','initial $display("PB_SWD_COMPLETE");endmodule'),None,'invalid_submission'),('syntax',ref.replace('data<=0;','data<=;'),0.,'compile_error')]:
        p=out/(name+'.sv');p.write_text(src);record(name,p,expected,category=cat)
    if dependencies()!=sources:raise RuntimeError('Source changed during gate')
    result=dict(schema='swd-read-quality-v2',accepted=len(checks)==19 and all(r['accepted'] for r in checks),checks=checks,source_files=sources,
                scope='Finite DP read transport only; no AP, writes, full DPIDR semantics or mid-transaction reset.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
