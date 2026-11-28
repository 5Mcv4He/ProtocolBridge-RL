"""Exact-source function-first structural admission."""
import json
from pathlib import Path
from verifier.bitfold_optimization.campaign import ROOT,TASK,sha,LIBRARY_SHA256
from verifier.bitfold_optimization.quality import dependencies
GATE='experiments/bitfold-optimization-v1/quality.json'
def check(package):
    package=Path(package)
    if package.resolve()!=ROOT/'tasks'/TASK:raise ValueError('Use canonical reviewed task')
    g=json.loads((ROOT/GATE).read_text())
    if g.get('schema')!='bitfold-cell-budget-quality-v1' or not g.get('accepted') or len(g['checks'])!=15 or not all(x['accepted'] for x in g['checks']):raise ValueError('Incomplete structural gate')
    if g['source_files']!=dependencies() or g['library_sha256']!=LIBRARY_SHA256:raise ValueError('Source or library mismatch')
    expected=[('reference',22),('alternate',19)]
    for name,count in expected:
      for phase in ('public','terminal','evaluation'):
        rows=[x for x in g['checks'] if x['control']==name and x['phase']==phase]
        if len(rows)!=1:raise ValueError('Missing positive')
        r=rows[0]['result']
        if r['source_sha256']!=sha(package/(name+'.sv')) or r['reward']!=1 or not r['verification_complete'] or r['resource_measurement']['mapped_cell_count']!=count:raise ValueError('Invalid positive')
    for name in ('constant','drop_bit','overflow','serial_over_budget','baseline'):
        rows=[x for x in g['checks'] if x['control']==name]
        if len(rows)!=1:raise ValueError('Missing negative')
        r=rows[0]['result'];f=package/'workspace/bitfold.sv' if name=='baseline' else package/'controls'/(name+'.sv')
        category='synthesis_error' if name in ('baseline','serial_over_budget') else 'transaction_mismatch'
        if r['source_sha256']!=sha(f) or r['reward']!=0 or r['category']!=category:raise ValueError('Negative was not semantically rejected')
        if category=='synthesis_error' and not r['resource_measurement']['functional_checks_passed']:raise ValueError('Budget control must be functionally legal')
    return {'task_id':TASK,'accepted':True,'gate_sha256':sha(ROOT/GATE)}
