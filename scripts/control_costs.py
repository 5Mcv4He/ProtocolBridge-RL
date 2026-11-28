"""Account actual control-bank work without counting reused compilation twice.

This is an offline resource measurement, not a quality gate. No EDA invocation,
old verdict inheritance, admission, model outcome selection or private vector
export is performed.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from scripts.package_costs import grade_cost


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def summarize(evidence):
    root=Path(evidence);controls=root/'controls';report=json.loads((controls/'result.json').read_text())
    if report.get('schema') not in ('router-instance-controls-v2','component-instance-controls-v1'):
        raise ValueError('Unsupported control report')
    if report['freeze_sha256']!=sha(controls/'freeze.json'):raise ValueError('Control freeze changed')
    rows=[];labels=set();compiled=set()
    for row in report['rows']:
        name=row['label']
        if not isinstance(name,str) or not re.fullmatch('[a-zA-Z0-9_-]+',name) or name in labels:
            raise ValueError('Duplicate or unsafe control label')
        labels.add(name);p=controls/name;r=json.loads((p/'result.json').read_text())
        if sha(p/'result.json')!=row['result_sha256']:raise ValueError('Grading result changed')
        if any(row[k]!=r[k] for k in ('reward','category','verification_complete')) or row['cases_executed']!=len(r['cases']):
            raise ValueError('Control summary differs from actual result')
        reused=r.get('compile_reused',False)
        if reused!=row['compile_reused']:raise ValueError('Reuse record mismatch')
        if (p/'backend.json').exists():
            identity=json.dumps(json.loads((p/'backend.json').read_text())['inputs'],sort_keys=True)
            if reused and identity not in compiled:raise ValueError('Reused build lacks matching earlier successful compilation')
            if not reused and r.get('compile_exit')==0:compiled.add(identity)
        elif reused:raise ValueError('Reused build has no identity')
        cost=grade_cost(p)
        if reused and cost['compile_attempts']:raise ValueError('Reused build claims a new compile')
        rows.append(dict(label=name,kind='positive' if name.startswith('reference-') else 'negative',
                         compile_reused=reused,grade_wall_seconds=row['wall_seconds'],**cost))
    compile_values=[r['compile_cpu_seconds_reported'] for r in rows if r['compile_attempts']]
    simulation_values=[r['simulation_cpu_seconds_reported'] for r in rows if r['simulation_attempts']]
    resource=root/'resource-result.json';job=json.loads(resource.read_text()) if resource.exists() else {}
    return dict(schema='control-cost-summary-v1',task_id=report['task_id'],
        control_report_sha256=sha(controls/'result.json'),analyzer_sha256=sha(__file__),
        controls_reported_passed=report['controls_passed'],admission_inferred=False,
        grading_runs=len(rows),actual_compile_attempts=sum(r['compile_attempts'] for r in rows),
        reused_compile_runs=sum(r['compile_reused'] for r in rows),
        simulation_attempts=sum(r['simulation_attempts'] for r in rows),
        compile_cpu_seconds_reported=sum(compile_values) if all(v is not None for v in compile_values) else None,
        simulation_cpu_seconds_reported=sum(simulation_values) if all(v is not None for v in simulation_values) else None,
        compile_cpu_reports_complete=all(v is not None for v in compile_values),
        simulation_cpu_reports_complete=all(v is not None for v in simulation_values),
        grade_wall_seconds=sum(r['grade_wall_seconds'] for r in rows),
        job_wall_seconds=job.get('wall_seconds'),rows=rows,
        scope='Actual recorded compilation and simulation work; CPU is not wall time. Whole-job wall may include setup or separately declared probes. Quality and current admission require their own audits.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('evidence');p.add_argument('out');a=p.parse_args()
    result=summarize(a.evidence)
    with Path(a.out).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','scope')}))
