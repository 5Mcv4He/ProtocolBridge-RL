"""Allowlisted public evidence only; private cases/seeds and vendor logs stay local."""
import argparse,difflib,hashlib,json,re
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compact(result):
    result=json.loads(json.dumps(result))
    if 'reason' in result:
        result['reason']=re.sub(r'/[^\s\'\";,]+','[local-path]',result['reason'])
    for case in result.get('cases',[]):
        samples=case.pop('latency_samples',[]);bins=case.pop('cross_bins',[])
        case['latency_sample_count']=len(samples);case['observed_cross_bin_count']=len(bins)
    return result

def write(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2)+'\n')

def export_grade(src,dst):
    write(dst/'result.json',compact(json.loads((src/'result.json').read_text())))
    hashes={str(p.relative_to(src)):digest(p) for p in src.rglob('*') if p.is_file() and p.name in ('compile.log','simulation.log','vectors.txt','cases.json','bridge.sv')}
    write(dst/'evidence-sha256.json',hashes)

def main():
    p=argparse.ArgumentParser();p.add_argument('controls');p.add_argument('destination');p.add_argument('--agent');a=p.parse_args()
    src=Path(a.controls);dst=Path(a.destination);dst.mkdir(parents=True,exist_ok=False)
    controls=json.loads((src/'summary.json').read_text())
    write(dst/'controls-summary.json',{'accepted':controls['accepted'],'results':{n:compact(r) for n,r in controls['results'].items()}})
    for name in controls['results']:export_grade(src/name,dst/'controls'/name)
    if a.agent:
        agent=Path(a.agent)
        write(dst/'agent/result.json',compact(json.loads((agent/'result.json').read_text())))
        write(dst/'agent/freeze.json',json.loads((agent/'freeze.json').read_text()))
        trace=json.loads((agent/'trace.json').read_text())
        for entry in trace:
            action=entry['action']
            if action.get('tool')=='edit' and 'content' in action:
                body=action.pop('content').encode();action.update(content_sha256=hashlib.sha256(body).hexdigest(),content_bytes=len(body))
            if action.get('tool')=='invalid' and 'response' in action:
                body=action.pop('response').encode();action.update(response_sha256=hashlib.sha256(body).hexdigest(),response_bytes=len(body))
                try:
                    requested=json.loads(body.decode()).get('tool')
                    if requested in ('read','edit','test','submit'):action['requested_tool']=requested
                except (ValueError,AttributeError):pass
            if action.get('tool')=='read':
                body=entry['feedback'].encode();entry['feedback']={'content_sha256':hashlib.sha256(body).hexdigest(),'content_bytes':len(body)}
            if action.get('tool')=='test' and isinstance(entry['feedback'],dict):entry['feedback']=compact(entry['feedback'])
        write(dst/'agent/trace.json',trace)
        write(dst/'agent/trace-provenance.json',{'full_trace_sha256':digest(agent/'trace.json'),'format':'compact-tool-trace-v2'})
        write(dst/'agent/harness-provenance.json',[
            {'event_file':p.name,'sha256':digest(p),
             'worker_uid':json.loads(p.read_text()).get('worker_uid'),
             'worker_pid':json.loads(p.read_text()).get('worker_pid')}
            for p in sorted(agent.glob('harness-*.json'))])
        if (agent/'submission/bridge.sv').exists():
            (dst/'agent/final.sv').write_bytes((agent/'submission/bridge.sv').read_bytes())
            export_grade(agent/'submission/grade',dst/'agent/final-grade')
            failed_hashes={e['feedback'].get('source_sha256') for e in trace
                           if e['action'].get('tool')=='test' and isinstance(e['feedback'],dict)
                           and e['feedback'].get('reward')==0}
            failed=next((p for p in sorted(agent.glob('candidate-*.sv')) if digest(p) in failed_hashes),None)
            if failed:
                (dst/'agent/failed-tested.sv').write_bytes(failed.read_bytes())
                (dst/'agent/repair.diff').write_text(''.join(difflib.unified_diff(
                    failed.read_text().splitlines(keepends=True),
                    (agent/'submission/bridge.sv').read_text().splitlines(keepends=True),
                    fromfile='failed-tested.sv',tofile='final.sv',n=0)))
        for public in agent.glob('public-*'):export_grade(public,dst/'agent'/public.name)
        if (agent/'reserved-evaluation/result.json').exists():
            export_grade(agent/'reserved-evaluation',dst/'agent/reserved-evaluation')
    print(dst)
if __name__=='__main__':main()
