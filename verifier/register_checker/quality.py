"""Fresh industrial gate; functional controls must fail functionally, not compile."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha
from .model import anchors
from task_families.register_checker_v1.generate import reference,controls

def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
    def record(mode,name,source,expected,phase='public',category=None):
        task='register_checker_'+mode+'_v1';p=out/(mode+'-'+name+'.sv');p.write_text(source)
        result=grade(task,p,out/(mode+'-'+name+'-'+phase),phase)
        ok=result['reward']==expected and (category is None or category==result['category'])
        checks.append(dict(task_id=task,control=name,phase=phase,accepted=ok,expected_reward=expected,result=result))
        (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n');print(mode,name,phase,result['category'],ok,flush=True)
        if result['category'].startswith('infrastructure'):raise RuntimeError('Stop on infrastructure fault; preserve incomplete gate')
    for mode in ('rw','w1c'):
        for name,src in [('array',reference(mode)),('per_address',reference(mode,True))]:
            for phase in ('public','terminal','evaluation'):record(mode,name,src,1.,phase,'pass')
        for name,src in controls(mode).items():record(mode,name,src,0.,category='transition_mismatch')
    ref=reference('rw')
    record('rw','empty','',None,category='invalid_submission')
    record('rw','wrong_interface',ref.replace('[3:0]','[4:0]'),None,category='invalid_submission')
    record('rw','spoof_report',ref.replace('endmodule','initial $display("PB_CHECKER_COMPLETE");endmodule'),None,category='invalid_submission')
    record('rw','syntax_error',ref.replace('error<=0;','error<=;'),0.,category='compile_error')
    files=['verifier/register_checker/model.py','verifier/register_checker/campaign.py','verifier/register_checker/quality.py','verifier/event_runtime.py','verifier/fifo_checker/campaign_v3.py','verifier/fifo_checker/model_v2.py','verifier/independent_formal/campaign.py','verifier/uart_tx/campaign_v4.py','environment/remote_backend.py','task_families/register_checker_v1/generate.py']
    files += [str(p.relative_to(ROOT)) for mode in ('rw','w1c') for p in sorted((ROOT/'tasks'/('register_checker_'+mode+'_v1')).rglob('*')) if p.is_file()]
    result=dict(schema='register-checker-quality-v1',accepted=len(checks)==38 and all(r['accepted'] for r in checks),checks=checks,semantic_anchors=anchors(),source_files={f:sha(ROOT/f) for f in files},scope='Event-level register state checker. No serial VIP compliance or formal completeness claim.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
