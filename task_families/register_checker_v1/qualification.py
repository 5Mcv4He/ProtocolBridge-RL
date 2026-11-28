"""Admit exact packages only after both legal structures and semantic controls."""
import json,tempfile
from pathlib import Path
from .generate import generate,MODES,controls
from verifier.independent_formal.campaign import ROOT,sha
from task_families.fifo_checker_v1.qualification import files
from verification_resources.dependencies import local_import_closure
GATE='experiments/register-checker-v1/quality.json'
def check(package):
    package=Path(package);meta=json.loads((package/'task.json').read_text());mode=meta.get('mode')
    if mode not in MODES:raise ValueError('Unknown register checker contract')
    gate=json.loads((ROOT/GATE).read_text())
    if gate.get('schema')!='register-checker-quality-v1' or not gate['accepted'] or len(gate['checks'])!=38 or not all(r['accepted'] for r in gate['checks']):raise ValueError('Incomplete gate')
    required=set(local_import_closure(ROOT,['verifier/register_checker/quality.py']))
    required.update(str(p.relative_to(ROOT)) for m in MODES for p in (ROOT/'tasks'/('register_checker_'+m+'_v1')).rglob('*') if p.is_file())
    if set(gate['source_files'])!=required:raise ValueError('Incomplete dependency set')
    if any(sha(ROOT/f)!=h for f,h in gate['source_files'].items()):raise ValueError('Executed dependency differs')
    with tempfile.TemporaryDirectory() as t:
        expected=Path(t)/'task';generate(mode,expected)
        if files(package)!=files(expected):raise ValueError('Task package differs')
    task='register_checker_'+mode+'_v1';records=[r for r in gate['checks'] if r['task_id']==task]
    for name,filename in [('array','reference.sv'),('per_address','alternate.sv')]:
        for phase in ('public','terminal','evaluation'):
            matches=[r for r in records if r['control']==name and r['phase']==phase]
            if len(matches)!=1 or matches[0]['result']['reward']!=1 or not matches[0]['result']['verification_complete'] or matches[0]['result']['source_sha256']!=sha(package/filename):raise ValueError('Legal execution missing')
    for name in controls(mode):
        matches=[r for r in records if r['control']==name]
        if len(matches)!=1 or matches[0]['result']['reward']!=0 or matches[0]['result']['category']!='transition_mismatch' or matches[0]['result']['source_sha256']!=sha(package/'controls'/(name+'.sv')):raise ValueError('Semantic control not actually detected')
    return {'task_id':task,'accepted':True,'gate_sha256':sha(ROOT/GATE)}
