"""Mutation regression: one compiled bank, fresh simulation per selected RTL.
Only the selected implementation is connected to VIP pins. The scoreboard is
identical for every selection; selection is not available to its verdict logic.
"""
import argparse,json,re
from pathlib import Path
from verifier.grade import grade,digest
from .reset import ROOT
NAMES=('reference','bad_address','bad_strobe','bad_error','bad_wait','bad_read_data','bad_backpressure')

def bundle(names):
    ref=(ROOT/'fixtures/reference.sv').read_text();header=ref[:ref.index(' typedef')]
    ports=[]
    for direction,width,raw in re.findall(r'\b(input|output)\s+logic\s*(\[[^\]]+\])?\s*(.*?)(?=\b(?:input|output)\s+logic|\)\s*;)',header,re.S):
        ports.extend((direction,width,n.strip()) for n in raw.strip().strip(',').split(','))
    text=header+'integer selection; initial if(!$value$plusargs("variant=%d",selection)) selection=0;\n'
    for i,name in enumerate(names):
        for direction,width,n in ports:
            if direction=='output':text+=f'wire {width} v{i}_{n};\n'
        connections=','.join(f'.{n}({n if d=="input" else f"v{i}_{n}"})' for d,w,n in ports)
        text+=f'bridge_variant_{i} variant_{i}({connections});\n'
    for d,w,n in ports:
        if d=='output':text+=f'assign {n}='+''.join(f'(selection=={i})?v{i}_{n}:' for i in range(len(names)))+"'x;\n"
    text+='endmodule\n'
    for i,name in enumerate(names):text+=(ROOT/'fixtures'/f'{name}.sv').read_text().replace('module bridge(',f'module bridge_variant_{i}(',1)
    return text

def validate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    source=out/'control_bundle.sv';source.write_text(bundle(NAMES))
    results={};compiled=None
    for i,name in enumerate(NAMES):
        results[name]=grade(source,out/name,reuse_build=compiled,runtime_args=(f'+variant={i}',))
        if (out/name/'backend.json').exists():compiled=out/name
        results[name]['fixture_sha256']=digest(ROOT/'fixtures'/f'{name}.sv')
        results[name]['compiled_bank_selection']=i
        (out/name/'result.json').write_text(json.dumps(results[name],indent=2))
        print(name,json.dumps(results[name]),flush=True)
        if not compiled or (name=='reference' and results[name]['reward']!=1.0):break
    ok=len(results)==len(NAMES) and results['reference']['reward']==1 and all(results[n]['reward']==0 for n in results if n!='reference')
    (out/'summary.json').write_text(json.dumps({'accepted':ok,'results':results},indent=2));return ok
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();raise SystemExit(0 if validate(a.out) else 1)
