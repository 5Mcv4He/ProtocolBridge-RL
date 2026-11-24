"""Export only allowlisted, user-owned evidence; never vendor logs or API headers."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('controls');p.add_argument('agent');p.add_argument('destination');a=p.parse_args()
out=Path(a.destination);out.mkdir(parents=True,exist_ok=False)

def export_run(src,dst):
    dst.mkdir(parents=True)
    result=json.loads((src/'result.json').read_text())
    if (src/'simulation.log').exists():
        error_lines=[l for l in (src/'simulation.log').read_text().splitlines() if l.startswith('UVM_ERROR ') and not l.startswith('UVM_ERROR :')]
        result['verification_error_counts']={
            'uvm_scoreboard':sum('[PB_FUNCTION]' in l for l in error_lines),
            'task_timing_assertions':sum('[PB_TIMING]' in l for l in error_lines),
            'axi_vip_protocol':sum('[register_fail:AMBA:AXI' in l for l in error_lines),
            'apb_vip_protocol':sum('[register_fail:AMBA:APB' in l for l in error_lines),
        }
    # Error strings can contain machine paths; completed evaluations need no such paths.
    if 'reason' in result and ('/home/' in result['reason'] or '/Users/' in result['reason']):
        result['reason']='See private raw evidence'
    (dst/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    evidence={}
    for name in ('compile.log','simulation.log','bridge.sv','vectors.json'):
        f=src/name
        if f.exists(): evidence[name]=hashlib.sha256(f.read_bytes()).hexdigest()
    (dst/'evidence-sha256.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if (src/'simulation.log').exists():
        lines=(src/'simulation.log').read_text().splitlines()
        safe=[l for l in lines if l.startswith(('PB2_','UVM_ERROR :','UVM_FATAL :'))]
        (dst/'events.txt').write_text('\n'.join(safe)+'\n')

controls=Path(a.controls);agent=Path(a.agent)
shutil.copyfile(controls/'summary.json',out/'controls-summary.json')
for name in json.loads((controls/'summary.json').read_text())['results']:
    export_run(controls/name,out/'controls'/name)
(out/'agent').mkdir()
for name in ('result.json','freeze.json'):
    shutil.copyfile(agent/name,out/'agent'/name)
raw_trace=(agent/'trace.json').read_bytes()
trace=json.loads(raw_trace)
for entry in trace:
    action=entry['action']
    if action['tool']=='edit' and 'content' in action:
        body=action.pop('content').encode()
        action.update(content_sha256=hashlib.sha256(body).hexdigest(),content_bytes=len(body))
    if action['tool']=='read' and isinstance(entry.get('feedback'),str):
        body=entry['feedback'].encode()
        entry['feedback']={'file':action['file'],'content_sha256':hashlib.sha256(body).hexdigest(),'content_bytes':len(body)}
(out/'agent/trace.json').write_text(json.dumps(trace,indent=2)+'\n')
provenance={
    'format':'compact-tool-trace-v1',
    'full_trace_sha256':hashlib.sha256(raw_trace).hexdigest(),
    'omitted':'Read file bodies and edit bodies are represented by SHA-256 and byte count. Full trace and candidate snapshots are retained locally; final submitted RTL is published.',
}
(out/'agent/trace-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
shutil.copyfile(agent/'submission/bridge.sv',out/'agent/final.sv')
shutil.copyfile(agent/'submission/submission.json',out/'agent/submission.json')
export_run(agent/'submission/grade',out/'agent/final-grade')
for f in agent.glob('public-*'): export_run(f,out/'agent'/f.name)
# Check selected export for accidental machine paths or credential-shaped content.
for f in out.rglob('*'):
    if f.is_file():
        text=f.read_text()
        if re.search(r'/Users/|/home/eda|Bearer |sk-[A-Za-z0-9]{16,}',text):
            raise RuntimeError('Export requires manual review: '+str(f))
print(out)
