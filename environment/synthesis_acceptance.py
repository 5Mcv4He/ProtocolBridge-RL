"""Sequential real DC/Formality/PT controls; no API calls or functional reward changes."""
import argparse,json
from pathlib import Path
from environment.synthesis_tools import run as tool_run,ROOT,sha
from environment.synthesis_session import session_class
from environment.policy import load
from verifier.task003.scenarios import suite

def capacity_control_rejected(result):
    return (result.get('reward')==0 and
            result.get('category') in ('transaction_functional_error','protocol_timing_error') and
            any('Request capacity exceeded' in c.get('failures',[]) for c in result.get('cases',[])))

def _acceptance(out,trusted=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);checks={};results={}
    def run(source,dest,**options):
        result=tool_run(source,dest,**options)
        print(json.dumps({'control':Path(dest).name,'status':result['observation']['status']}),flush=True)
        if any(isinstance(result.get(k),dict) and result[k].get('status')=='ENV_ERROR' for k in ('observation','formal','measurement')):
            raise RuntimeError('Infrastructure failure: '+Path(dest).name)
        return result
    counter='module bridge(input logic clk, rst_n, output logic [3:0] q); always_ff @(posedge clk) if (!rst_n) q<=0; else q<=q+1; endmodule\n'
    controls={
        'counter':counter,
        'syntax':'module bridge(input logic clk, output logic q); assign q=; endmodule\n',
        'latch':'module bridge(input logic clk, en, d, output logic q); always_latch if(en) q=d; endmodule\n',
        'forbidden':'module bridge; initial $display("private"); endmodule\n'}
    for name,text in controls.items():
        source=out/(name+'.sv');source.write_text(text)
        r=run(source,out/name,equivalence=trusted and name=='counter',measure=trusted and name=='counter');results[name]=r
        expected={'counter':'PASS','syntax':'FAIL','latch':'PASS','forbidden':'INVALID'}[name]
        checks[name+'_status']=r['observation']['status']==expected
    if trusted:checks['counter_equivalence']=results['counter']['formal']=={'status':'PASS','equivalent':True}
    if trusted:checks['teaching_measurement']=results['counter']['measurement'] is not None and results['counter']['measurement']['status']=='TEACHING_MEASUREMENT'
    checks['latch_advisory']=any(d['code']=='LATCH_INFERRED' for d in results['latch']['observation']['diagnostics'])
    checks['forbidden_no_execution']='execution' not in results['forbidden']
    if trusted:
        source=out/'different.sv';source.write_text(counter.replace('q+1','q+2'))
        results['nonequivalent']=run(source,out/'nonequivalent',equivalence=True,equivalence_netlist=out/'counter/mapped.v')
        checks['nonequivalent_rejected']=results['nonequivalent']['formal']=={'status':'FAIL','equivalent':False}
    for task in ('task003','task004'):
        results[task]=run(ROOT/'fixtures'/task/'reference.sv',out/task,equivalence=trusted,measure=trusted)
        checks[task+'_synthesis']=results[task]['observation']['status']=='PASS'
        if trusted:checks[task+'_equivalence']=results[task]['formal']=={'status':'PASS','equivalent':True}
        if trusted:checks[task+'_measurement']=results[task]['measurement'] is not None and results[task]['measurement']['status']=='TEACHING_MEASUREMENT'
    # Actual session dispatcher and actual DC executions, with no model involved.
    work=out/'work';work.mkdir()
    (work/'bridge.sv').write_bytes((ROOT/'fixtures/task003/bad_early_credit.sv').read_bytes())
    (work/'spec.md').write_bytes((ROOT/'tasks/axil_to_apb4_queue_003/spec.md').read_bytes())
    calls=[]
    def backend(source,dest):
        calls.append(str(dest));return run(source,dest)['observation']
    s=session_class('axil_to_apb4_queue_003')(load('test_diagnostic'),work,out/'session',suite(False,20261126),synthesizer=backend)
    checks['read_required']=s.handle({'tool':'synth_check'})['status']=='REJECTED' and not calls
    for file in ('spec.md','bridge.sv'):s.handle({'tool':'read','file':file})
    for i in range(2):checks['session_real_synthesis_%d'%i]=s.handle({'tool':'synth_check'})['status']=='PASS'
    checks['third_denied']=s.handle({'tool':'synth_check'})['status']=='REJECTED' and len(calls)==2
    checks['private_read_denied']=s.handle({'tool':'read','file':'private/reward.json'})['status']=='REJECTED'
    checks['script_denied']=s.handle({'tool':'synth_check','script':'exit'})['status']=='REJECTED' and len(calls)==2
    checks['synth_pass_does_not_imply_public_pass']=s.handle({'tool':'test'})['status']=='FAIL'
    checks['submission']=s.handle({'tool':'submit'})['status']=='SUBMITTED'
    checks['closed']=s.handle({'tool':'synth_check'})['status']=='REJECTED' and len(calls)==2
    terminal=s.finalize()
    checks['functional_reward_independent']=capacity_control_rejected(terminal)
    checks['no_tool_reward']=all(r['reward'] is None for r in results.values())
    checks['source_identity']=all(r['source_sha256']==sha(out/name/'bridge.sv') for name,r in results.items())
    summary={'version':'synthesis-tools-v1','accepted':all(checks.values()),'checks':checks,
             'controls':{k:{field:r.get(field) for field in ('source_sha256','observation','formal','measurement','reward','wall_seconds','evidence_sha256')} for k,r in results.items()},
             'real_tools':['Design Compiler','VCS VIP/UVM']+(['Formality','PrimeTime PX'] if trusted else []),'model_used':False,'trusted_extensions_requested':trusted,
             'terminal_control':{k:terminal.get(k) for k in ('reward','category','source_sha256','suite_sha256','failed_case')},
             'limits':['Synthesis acceptance includes one real functional negative control; positive task qualification remains a separate Quality Gate.','No PPA reward; teaching measurements only.','No FPV proof of queue capacity or arbitration.']}
    (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

def acceptance(out,trusted=False):
    try:return _acceptance(out,trusted)
    except RuntimeError as error:
        result={'version':'synthesis-tools-v1','accepted':False,'category':'infrastructure_error','reason':str(error),'checks':{},'model_used':False}
        (Path(out)/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--trusted',action='store_true');a=p.parse_args();r=acceptance(a.out,a.trusted)
    print(json.dumps({'accepted':r['accepted'],'checks':r['checks']},indent=2));raise SystemExit(0 if r['accepted'] else 1)
