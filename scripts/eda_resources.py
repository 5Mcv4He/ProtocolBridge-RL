"""Extract numeric VCS resource footers without publishing vendor logs or paths."""
import argparse,json,re
from pathlib import Path


def analyze(root):
    root=Path(root);rows=[]
    for entry in json.loads((root/'experiment.json').read_text())['schedule']:
        d=root/entry['id']
        if not (d/'metrics.json').exists():continue
        sim=[];compile_cpu=[];compiles=0;simulations=0
        for timing in d.rglob('timing.json'):
            events=json.loads(timing.read_text());compiles+=sum(x['kind']=='compile' for x in events);simulations+=sum(x['kind']=='simulate' for x in events)
            if any(x['kind']=='compile' for x in events):
                log=timing.parent/'compile.log'
                text=log.read_text(errors='replace') if log.exists() else ''
                matches=re.findall(r'CPU time:\s*([\d.]+) seconds to compile \+\s*([\d.]+) seconds to elab \+\s*([\d.]+) seconds to link',text)
                if matches:compile_cpu.append(sum(float(x) for x in matches[-1]))
        for log in d.rglob('simulation.log'):
            matches=re.findall(r'CPU Time:\s*([\d.]+) seconds;\s*Data structure size:\s*([\d.]+)Mb',log.read_text(errors='replace'))
            if matches:sim.append(tuple(float(x) for x in matches[-1]))
        rows.append({'trial':entry['id'],'compile_invocations':compiles,'compile_footers':len(compile_cpu),'compiler_cpu_seconds_measured':round(sum(compile_cpu),3),
                     'simulation_invocations':simulations,'simulation_footers':len(sim),'simulator_cpu_seconds_measured':round(sum(x[0] for x in sim),3),
                     'maximum_reported_data_structure_Mb':max(x[1] for x in sim) if sim else None})
    result={'kind':'numeric_vendor_resource_footers','rows':rows,'note':'CPU totals include only available numeric footers. Missing footers are not zero-cost processes. VCS data-structure Mb is its reported unit, not host peak RSS. No commercial log text is published.'}
    (root/'eda-resource-analysis.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();r=analyze(a.root);print(json.dumps({'trials':len(r['rows']),'compiler_cpu_seconds_measured':sum(x['compiler_cpu_seconds_measured'] for x in r['rows']),'simulator_cpu_seconds_measured':sum(x['simulator_cpu_seconds_measured'] for x in r['rows'])},indent=2))
