"""Positive/negative campaign controls, including two reset-specific mutations."""
import argparse,json,os
from pathlib import Path
from .validate import bundle
from .reset import ROOT
from verifier.campaign import grade,sha
from verifier.scenarios import suite
NAMES=('reference','bad_address','bad_strobe','bad_error','bad_wait','bad_read_data','bad_backpressure','bad_reset_half','bad_reset_response','bad_early_read','bad_accept_latency')
# Test prioritization for known injected faults, never a verdict rule. Every
# candidate still uses the same UVM checks; surviving the focused case continues
# through the remaining complete suite.
FIRST_CASE={'bad_address':'address_data','bad_strobe':'write_accumulate',
 'bad_error':'wait_error','bad_wait':'wait_error','bad_read_data':'address_data',
 'bad_backpressure':'response_backpressure','bad_reset_half':'reset_aw_only',
 'bad_reset_response':'reset_b_stall','bad_early_read':'address_data',
 'bad_accept_latency':'address_data'}
def validate(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    source=out/'control_bundle.sv';source.write_text(bundle(NAMES))
    original=os.environ.get('PB_CONFIG');base=Path(original) if original else ROOT/'.local/config.json'
    config=json.loads(base.read_text());results={};compiled=None
    try:
        for i,name in enumerate(NAMES):
            path=out/('config-%s.json'%name);path.write_text(json.dumps(dict(config,variant=i)));os.environ['PB_CONFIG']=str(path)
            cases=suite()
            if name in FIRST_CASE:cases.sort(key=lambda c:c['name']!=FIRST_CASE[name])
            results[name]=grade(source,out/name,reuse_build=compiled,trusted_controls=True,cases=cases)
            results[name]['fixture_sha256']=sha(ROOT/'fixtures'/(name+'.sv'))
            results[name]['compiled_bank_selection']=i
            if (out/name/'backend.json').exists():compiled=out/name
            (out/name/'result.json').write_text(json.dumps(results[name],indent=2))
            if not compiled or (name=='reference' and results[name]['reward']!=1):break
    finally:
        if original is None:os.environ.pop('PB_CONFIG',None)
        else:os.environ['PB_CONFIG']=original
    accepted=len(results)==len(NAMES) and results['reference']['reward']==1 and all(results[n]['reward']==0 for n in NAMES[1:])
    (out/'summary.json').write_text(json.dumps({'accepted':accepted,'results':results},indent=2));return accepted
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();raise SystemExit(0 if validate(a.out) else 1)
