"""Extend control evidence audit with serialized stimulus/build-source binding.

The original audit and records remain intact. No new simulation or functional
verdict is inferred: this checks that archived execution material is consistent
with the already executed candidate, configuration and declared input rows.
"""
import argparse,json,hashlib
from pathlib import Path
from .audit_controls import audit as previous,sha

def audit(package,evidence):
    package=Path(package).resolve();evidence=Path(evidence).resolve()
    report=previous(package,evidence);control=evidence/'controls'
    rows=json.loads((control/'result.json').read_text())['rows'];count=0;entries=set()
    for row in rows:
        d=control/row['label'];cfg=json.loads((control/(row['label']+'-config.json')).read_text())
        runtime=json.loads((d/'runtime.json').read_text());backend=json.loads((d/'backend.json').read_text())
        expected={p.name:sha(p) for p in (package/'verifier/task002').glob('*.sv')}
        expected.update(candidate=sha(control/'control_bank.sv'),campaign=sha(package/'verifier/task002/campaign.py'),
                        build_configuration=hashlib.sha256(json.dumps({k:v for k,v in cfg.items() if k not in ('variant','remote_root')},sort_keys=True).encode()).hexdigest())
        inputs=runtime['inputs']
        if set(inputs)!=set(expected)|{'environment_entry'} or any(inputs[k]!=v for k,v in expected.items()):raise ValueError('Build input dependency mismatch')
        if backend['inputs']!=inputs or backend['remote']!=runtime['remote']:raise ValueError('Runtime/build record differs')
        if len(inputs['environment_entry'])!=64:raise ValueError('Missing environment source identity')
        entries.add(inputs['environment_entry'])
        cases={c['name']:c for c in json.loads((d/'cases.json').read_text())}
        for c in json.loads((d/'result.json').read_text())['cases']:
            vectors=''.join('%d %08x %08x %x %d %d %d %d %d %d %d\n'%tuple(r) for r in cases[c['name']]['rows'])
            if (d/c['name']/'vectors.txt').read_text()!=vectors:raise ValueError('Archived stimuli differ from declared inputs')
            count+=1
    if len(entries)!=1:raise ValueError('Environment changed within control execution')
    report.update(schema='router-control-audit-v2',stimulus_records_bound=count,
                  environment_entry_sha256=entries.pop(),parent_auditor_sha256=report['auditor_sha256'],auditor_sha256=sha(Path(__file__)))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('evidence');p.add_argument('out');a=p.parse_args()
    with Path(a.out).open('x') as f:json.dump(audit(a.package,a.evidence),f,indent=2);f.write('\n')
