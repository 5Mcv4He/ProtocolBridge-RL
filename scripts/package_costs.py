"""Read reported VCS CPU time; never mislabel it as isolated wall time."""
import json,re
from pathlib import Path

def grade_cost(path):
    path=Path(path);result=json.loads((path/'result.json').read_text())
    cpath=path/'compile.log';compile_cpu=None
    if cpath.exists():
        matches=re.findall(r'CPU time:\s*([\d.]+) seconds to compile \+\s*([\d.]+) seconds to elab \+\s*([\d.]+) seconds to link',cpath.read_text())
        if len(matches)==1:compile_cpu=sum(float(x) for x in matches[0])
    sim=[]
    for c in result.get('cases',[]):
        p=path/c['name']/'simulation.log'
        matches=re.findall(r'CPU Time:\s*([\d.]+) seconds;',p.read_text()) if p.exists() else []
        sim.append(float(matches[0]) if len(matches)==1 else None)
    prov=path/'adapter-provenance.json'
    return {'compile_attempts':int('compile_exit' in result),'compile_cpu_seconds_reported':compile_cpu,
            'simulation_attempts':len(sim),'simulation_cpu_seconds_reported':sum(sim) if sim and all(x is not None for x in sim) else None,
            'simulation_cpu_reports':sum(x is not None for x in sim),'adapter_wall_seconds':json.loads(prov.read_text()).get('adapter_wall_seconds') if prov.exists() else None,
            'compile_wall_seconds':None,'simulation_wall_seconds':None,
            'scope':'Reported CPU and enclosing adapter wall time; compile/simulation transport wall time was not independently instrumented.'}
