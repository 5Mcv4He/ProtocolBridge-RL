"""Bind declared obligations to completed control evidence; never grant admission.

Coverage is observed across each full reference suite, not proof that a named
stimulus alone caused a bin. Semantic adequacy still requires engineering review.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from task_families.package import verify


def link(obligations, references, controls):
    rows=[];seen=set()
    for item in obligations:
        if item['id'] in seen:raise ValueError('Duplicate obligation')
        seen.add(item['id']);evidence={}
        if not item['stimulus'] or not item['coverage']:raise ValueError('Empty verification obligation')
        for name,result in references.items():
            if result.get('reward')!=1 or not result.get('verification_complete'):
                raise ValueError('Incomplete positive control: '+name)
            cases=result['cases'];observed={b for c in cases for b in c.get('coverage_bins',[])}
            executed={c['name'] for c in cases if c.get('reward')==1}
            if not set(item['coverage'])<=observed:raise ValueError('Unobserved obligation coverage: '+item['id'])
            if not set(item['stimulus'])<=executed:raise ValueError('Unexecuted obligation stimulus: '+item['id'])
            evidence[name]={'observed_bins':sorted(set(item['coverage'])&observed),
                            'completed_stimuli':sorted(set(item['stimulus'])&executed)}
        rejected={}
        for name in item['controls']:
            r=controls.get(name,{})
            if r.get('reward')!=0 or r.get('category') not in ('transaction_functional_error','protocol_timing_error'):
                raise ValueError('Missing functional negative control: '+name)
            rejected[name]={'reward':r['reward'],'category':r['category'],'failed_case':r.get('failed_case')}
        if not references or not rejected:raise ValueError('Obligation needs positive and negative evidence')
        rows.append({'id':item['id'],'kind':item.get('kind'),'reference_evidence':evidence,'negative_evidence':rejected})
    if not rows:raise ValueError('No declared obligations')
    return rows


def report(package,gate):
    package=Path(package).resolve();gate=Path(gate).resolve();m=verify(package)
    freeze=json.loads((gate/'freeze.json').read_text());summary=json.loads((gate/'result.json').read_text())
    digest=hashlib.sha256((gate/'freeze.json').read_bytes()).hexdigest()
    if not summary.get('accepted') or summary.get('freeze_sha256')!=digest or freeze['task_id']!=m['task_id'] or summary.get('task_id')!=m['task_id']:
        raise ValueError('Missing source-bound accepted gate')
    for name,value in freeze['files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not (package/p).is_file():raise ValueError('Invalid dependency')
        if hashlib.sha256((package/p).read_bytes()).hexdigest()!=value:raise ValueError('Gate dependency changed: '+name)
    task=package/'tasks'/m['task_id'];metadata=json.loads((task/'task.json').read_text())
    refs={Path(n).stem:json.loads((gate/Path(n).stem/'result.json').read_text()) for n in metadata['quality']['references']}
    return {'schema':'obligation-evidence-v1','task_id':m['task_id'],'freeze_sha256':digest,
            'evidence_sha256':{str(p.relative_to(gate)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [gate/'result.json']+[gate/n/'result.json' for n in refs]},
            'obligations_sha256':hashlib.sha256((task/'obligations.json').read_bytes()).hexdigest(),
            'reporter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'obligations':link(json.loads((task/'obligations.json').read_text()),refs,summary['results']),
            'scope':'Source-matched executed stimuli, observed bins and rejected functional controls. This does not grant admission or establish completeness or causal coverage attribution.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('gate');p.add_argument('out');a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise ValueError('Preserve prior evidence')
    result=report(a.package,a.gate);out.write_text(json.dumps(result,indent=2)+'\n')
