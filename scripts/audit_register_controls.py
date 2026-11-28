"""Replay recorded APB control evidence; never run EDA or infer runtime admission."""
import argparse
import hashlib
import json
from pathlib import Path
from environment.register_instance_controls import inputs,accepted
from task_families.apb_register_v1.verification import scenarios,config_sv,anchors_sv
from task_families.apb_register_v1.results import simulation_result

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())


def audit(package,evidence):
    package=Path(package);evidence=Path(evidence);c,meta=inputs(package)
    controls=evidence/'controls';report=read(controls/'result.json');freeze=read(controls/'freeze.json')
    if report.get('schema')!='apb-register-control-results-v1' or report.get('controls_passed') is not True:
        raise ValueError('Functional control execution incomplete')
    if report['task_id']!=c['task_id'] or report['freeze_sha256']!=sha(controls/'freeze.json'):
        raise ValueError('Control identity changed')
    if freeze['manifest_sha256']!=sha(package/'manifest.json') or freeze['config_sha256']!=sha(evidence/'.local/config.json'):
        raise ValueError('Frozen materials or configuration changed')
    required={'environment/register_instance_controls.py'}|{str(p.relative_to(ROOT)) for p in (ROOT/'task_families/apb_register_v1').iterdir() if p.suffix in ('.py','.in')}
    bound={}
    for raw,h in freeze['sources'].items():
        matches=[n for n in required if raw==n or raw.endswith('/'+n)]
        if len(matches)!=1 or matches[0] in bound:raise ValueError('Ambiguous execution source')
        name=matches[0]
        if sha(ROOT/name)!=h or sha(evidence/name)!=h:raise ValueError('Executed source differs')
        bound[name]=h
    if set(bound)!=required:raise ValueError('Missing execution dependency')
    names=meta['references']+meta['negative_controls']
    if len(report['rows'])!=len(names) or freeze['controls']!={n:sha(package/n) for n in names}:
        raise ValueError('Incomplete or different control bank')
    rows=scenarios(c,freeze['seed'],freeze['random_count'])
    vectors=''.join('%d %08x %08x %x\n'%tuple(x) for x in rows)
    transfers=sum(x[0]!=2 for x in rows);resets=1+sum(x[0]==2 for x in rows)
    environment_entries=set()
    for i,(name,row) in enumerate(zip(names,report['rows'])):
        label='control-%02d'%i;d=controls/label;r=read(d/'result.json');positive=i<len(meta['references'])
        if row['label']!=label or row['source']!=name or row['positive']!=positive or row['result_sha256']!=sha(d/'result.json'):
            raise ValueError('Actual control result differs')
        if r['source_sha256']!=sha(package/name) or sha(d/'candidate.sv')!=r['source_sha256'] or row['source_sha256']!=r['source_sha256']:
            raise ValueError('Wrong candidate graded')
        if sha(d/'tb.sv')!=sha(package/'verification/tb.sv') or (d/'register_config.svh').read_text()!=config_sv(c) or (d/'oracle_anchors.svh').read_text()!=anchors_sv(c):
            raise ValueError('Checker inputs differ from contract')
        if (d/'vectors.txt').read_text()!=vectors or r['input_sha256']!=sha(d/'vectors.txt'):
            raise ValueError('Actual stimulus differs')
        if r['compile_exit']!=0 or r['grader_sha256']!=bound['task_families/apb_register_v1/campaign.py']:
            raise ValueError('Functional control did not compile under frozen grader')
        backend=read(d/'backend.json')
        if backend.get('compiled') is not True or any(backend['inputs'][n]!=sha(d/n) for n in ('candidate.sv','tb.sv','register_config.svh','oracle_anchors.svh')):
            raise ValueError('Compiled source binding differs')
        if backend['inputs']['configuration']!=freeze['config_sha256'] or backend['inputs']['grader']!=bound['task_families/apb_register_v1/campaign.py']:
            raise ValueError('Compiled configuration or grader differs')
        environment_entries.add(backend['inputs']['environment_entry'])
        projected=simulation_result((d/'simulation.log').read_text(),r['simulation_exit'],transfers,resets,transfers*c['wait_cycles'],len(c['registers']))
        if any(r[k]!=projected[k] or row[k]!=r[k] for k in ('reward','category','verification_complete')) or not accepted(projected,positive) or row['accepted'] is not True:
            raise ValueError('Actual log or functional attribution differs')
    if len(environment_entries)!=1:raise ValueError('Execution environment changed within the bank')
    return dict(schema='apb-register-control-audit-v1',task_id=c['task_id'],functional_layer_qualified=True,
                runtime_admitted=False,manifest_sha256=sha(package/'manifest.json'),control_report_sha256=sha(controls/'result.json'),
                auditor_sha256=sha(__file__),positive_controls=len(meta['references']),negative_controls=len(meta['negative_controls']),
                environment_entry_sha256=environment_entries.pop(),
                independently_compiled_controls=len(names),positive_transfers_each=transfers,positive_resets_each=resets,
                positive_wait_edges_each=transfers*c['wait_cycles'],required_bins=17*len(c['registers']),
                scope='Recorded source, input, compilation and verdict consistency; not a proof of oracle completeness or Agent runtime isolation.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('evidence');p.add_argument('out');a=p.parse_args()
    r=audit(a.package,a.evidence)
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(r))
