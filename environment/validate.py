"""Control-bank assembly and current v3 regression entry point."""
import argparse,re
from .reset import ROOT

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
    from .validate_v3 import validate as current
    return current(out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args()
    raise SystemExit(0 if validate(a.out) else 1)
