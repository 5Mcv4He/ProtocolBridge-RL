"""Functional controls must reach functional checking, not merely return zero."""
import argparse,json
from pathlib import Path
from .campaign import ROOT,sha,grade
from task_families.rffe_register_v1.generate import rtl,controls
from verification_resources.dependencies import local_import_closure


def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
    def record(mode,name,source,expected,phase='public',category=None):
        task='rffe_register_'+mode+'_v1';p=out/(mode+'-'+name+'.sv');p.write_text(source)
        r=grade(task,p,out/(mode+'-'+name+'-'+phase),phase)
        accepted=r['reward']==expected and (category is None or r['category']==category)
        if expected==0 and category is None:accepted=accepted and r['category'] in ('transaction_mismatch','protocol_timing_error')
        checks.append(dict(task_id=task,control=name,phase=phase,expected_reward=expected,expected_category=category,accepted=accepted,result=r))
        (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n')
        print(task,name,phase,r['category'],accepted,flush=True)
        if r['reward'] is None and r['category']!='invalid_submission':raise RuntimeError('Incomplete trusted verification; stop gate and preserve results')
    for mode in ('rw','w1c'):
        for name,source in [('shift',rtl(mode)),('indexed',rtl(mode,True))]:
            for phase in ('public','terminal','evaluation'):record(mode,name,source,1.,phase)
        for name,source in controls(mode).items():record(mode,name,source,0.)
    ref=rtl('rw')
    record('rw','empty','',None,category='invalid_submission')
    record('rw','wrong_width',ref.replace('input logic clk','input logic [1:0] clk'),None,category='invalid_submission')
    record('rw','wrong_direction',ref.replace('output logic sdata_out','input logic sdata_out'),None,category='invalid_submission')
    record('rw','report_spoof',ref.replace('endmodule','initial $display("PB_RFFE_COMPLETE");endmodule'),None,category='invalid_submission')
    record('rw','syntax',ref.replace('state<=0;','state<=;'),0.,category='compile_error')
    paths=set(local_import_closure(ROOT,['verifier/rffe_register/quality.py','task_families/rffe_register_v1/generate.py']))
    paths |= {'verifier/rffe_register/tb.sv','task_families/rffe_register_v1/reference_template.sv'}
    paths |= {str(p.relative_to(ROOT)) for mode in ('rw','w1c') for p in (ROOT/'tasks'/('rffe_register_'+mode+'_v1')).rglob('*') if p.is_file()}
    result=dict(schema='rffe-register-quality-v2',accepted=len(checks)==33 and all(c['accepted'] for c in checks),checks=checks,
                source_files={p:sha(ROOT/p) for p in sorted(paths)},scope='Finite Register Read/Write USID1 addresses0..15; VIP protocol plus independent pin/register oracle; not full RFFE certification')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
