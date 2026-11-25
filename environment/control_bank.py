"""Compile trusted positive/mutation controls together; never used for Agent grading.
All variants see the same inputs. Only the selected variant drives the VIP bus.
Selection changes DUT logic, not verifier rules. Standalone RTL is also retained.
"""
import re
from pathlib import Path

def bundle(paths):
    sources=[Path(p).read_text() for p in paths]
    header=sources[0].split(');',1)[0]+');\n'
    ports=[]
    for direction,width,raw in re.findall(r'\b(input|output)\s+logic\s*(\[[^\]]+\])?\s*(.*?)(?=\b(?:input|output)\s+logic|\)\s*;)',header,re.S):
        ports.extend((direction,width,n.strip()) for n in raw.strip().strip(',').split(','))
    if not ports or any(not re.match(r'^\w+$',n) for d,w,n in ports):raise ValueError('Unsupported control ports')
    text=header+'integer selection; initial if(!$value$plusargs("variant=%d",selection)) selection=0;\n'
    for i in range(len(sources)):
        for d,w,n in ports:
            if d=='output':text+='wire %s v%d_%s;\n'%(w,i,n)
        connections=','.join('.%s(%s)'%(n,n if d=='input' else 'v%d_%s'%(i,n)) for d,w,n in ports)
        text+='bridge_variant_%d variant_%d(%s);\n'%(i,i,connections)
    for d,w,n in ports:
        if d=='output':text+='assign '+n+'='+''.join('(selection==%d)?v%d_%s:'%(i,i,n) for i in range(len(sources)))+"'x;\n"
    text+='endmodule\n'
    for i,source in enumerate(sources):
        if source.split(');',1)[0] != sources[0].split(');',1)[0]:raise ValueError('Control port mismatch')
        text+=source.replace('module bridge(', 'module bridge_variant_%d('%i,1)
    return text
