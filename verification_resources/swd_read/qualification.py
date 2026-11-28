"""Require exact dependency closure and real semantic rejection evidence."""
import json
from pathlib import Path
from verifier.swd_read.campaign import ROOT,TASK,sha
from verifier.swd_read.quality import dependencies
GATE='experiments/swd-read-v1/quality.json'
def check(package):
    package=Path(package)
    if package.resolve()!=ROOT/'tasks'/TASK:raise ValueError('Use the canonical reviewed task')
    gate=json.loads((ROOT/GATE).read_text())
    if gate.get('schema')!='swd-read-quality-v2' or not gate.get('accepted') or len(gate['checks'])!=19 or not all(r['accepted'] for r in gate['checks']):raise ValueError('Incomplete SWD gate')
    if gate['source_files']!=dependencies():raise ValueError('Source dependency mismatch')
    for name in ('reference','alternate'):
        for phase in ('public','terminal','evaluation'):
            records=[r for r in gate['checks'] if r['control']==name and r['phase']==phase]
            if len(records)!=1:raise ValueError('Missing positive control')
            r=records[0]['result']
            if r['reward']!=1 or not r['verification_complete'] or r['source_sha256']!=sha(package/(name+'.sv')) or r['activity']['reads']!=48:raise ValueError('Positive result not bound to full execution')
    for f in sorted((package/'controls').glob('*.sv')):
        records=[r for r in gate['checks'] if r['control']==f.stem]
        if len(records)!=1:raise ValueError('Missing negative control')
        r=records[0]['result']
        if r['reward']!=0 or r['category'] not in ('transaction_mismatch','protocol_timing_error') or r['source_sha256']!=sha(f):raise ValueError('Negative control not functionally rejected')
    return {'task_id':TASK,'accepted':True,'gate_sha256':sha(ROOT/GATE)}
