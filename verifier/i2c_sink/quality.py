"""No admission from a vendor example: source-bound controls for the finite contract."""
import argparse,json
from pathlib import Path
from .campaign import grade,ROOT,sha
from task_families.i2c_sink_v1.generate import MODES,rtl,controls

def run(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);checks=[]
    def record(task,name,src,expected,phase='public',category=None):
        p=out/(task+'-'+name+'.sv');p.write_text(src)
        r=grade(task,p,out/(task+'-'+name+'-'+phase),phase)
        accepted=r['reward']==expected and (category is None or r['category']==category)
        checks.append(dict(task_id=task,control=name,phase=phase,expected_reward=expected,accepted=accepted,result=r))
        (out/'progress.json').write_text(json.dumps(checks,indent=2)+'\n')
        print(task,name,phase,r['category'],accepted,flush=True)
        if r['category'].startswith('infrastructure') or r['category']=='unclassified_verifier_result':
            raise RuntimeError('Stop incomplete campaign; retain raw records')
    for mode in MODES:
        task=f'i2c_sink_{mode}_v1'
        for alt in (False,True):
            for phase in ('public','terminal','evaluation'):
                record(task,'indexed' if alt else 'shift',rtl(mode,alt),1.,phase)
        for name,src in controls(mode).items():record(task,name,src,0.)
        record(task,'empty-function',(ROOT/'tasks'/task/'workspace/i2c_sink.sv').read_text(),0.)
    task='i2c_sink_byte_v1'
    record(task,'empty','',None,category='invalid_submission')
    record(task,'spoof',rtl('byte').replace('endmodule','initial $display("PB_I2C_COMPLETE"); endmodule'),None,category='invalid_submission')
    record(task,'width',rtl('byte').replace('[15:0] item_data','[7:0] item_data'),None,category='invalid_submission')
    record(task,'syntax',rtl('byte').replace('item_data<=0;','item_data<=;'),0.,category='compile_error')
    paths=[ROOT/p for p in ['verifier/i2c_sink/campaign.py','verifier/i2c_sink/corpus.py','verifier/i2c_sink/tb.sv','verifier/i2c_sink/quality.py','task_families/i2c_sink_v1/generate.py','task_families/i2c_sink_v1/reference_template.sv','verifier/independent_formal/campaign.py','verifier/uart_tx/campaign_v5.py','environment/remote_backend.py']]
    for mode in MODES:paths.extend(p for p in (ROOT/'tasks'/f'i2c_sink_{mode}_v1').rglob('*') if p.is_file())
    result=dict(schema='i2c-sink-quality-v1',accepted=len(checks)==32 and all(c['accepted'] for c in checks),checks=checks,source_files={str(p.relative_to(ROOT)):sha(p) for p in paths},scope='Finite addressed writes only; VIP protocol checks and independent pin/output accounting; no complete I2C-controller claim')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();r=run(a.out);print('accepted',r['accepted']);raise SystemExit(0 if r['accepted'] else 1)
