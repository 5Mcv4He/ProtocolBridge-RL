"""Query three qualified engineering domains without inheriting task verdicts.

V1 entries retain their existing validators. The new composed domain requires
its own runtime qualification and concrete industrial control bank.
"""
import argparse
import json
from pathlib import Path
from environment.task_pool_v1 import query as query_v1
from environment.composed_admission_v1 import validate, read, sha


def query(index):
    plan=read(index)
    if set(plan)!={'schema','entries'} or plan['schema']!='qualified-task-pool-index-v2':
        raise ValueError('Unsupported pool index')
    rows=[];seen=set()
    for entry in plan['entries']:
        if set(entry)!={'admission','config'}:
            raise ValueError('Explicit admission/configuration pair required')
        path,config=Path(entry['admission']),Path(entry['config'])
        if read(path).get('schema')=='composed-layered-admission-v1':
            a=validate(path,config);root=Path(a['package']);task=root/'tasks'/a['task_id']
            row=dict(task_id=a['task_id'],family=read(root/'family-manifest.json')['family'],
                capabilities=read(task/'task.json')['capabilities'],admission=str(path.resolve()),
                admission_sha256=sha(path),config_sha256=sha(config),
                package_manifest_sha256=a['package_manifest_sha256'],
                initial_sha256=sha(task/'workspace/bridge.sv'),deliverable='bridge.sv',
                task_form='rtl_implementation',runner='environment.native_tools.run_composed_v1',
                status='source_matched_admitted',difficulty='not_inferred_from_admission')
        else:
            # The legacy API accepts a JSON file. An ephemeral index contains
            # only already explicit local paths and does not copy task evidence.
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'index.json'
                p.write_text(json.dumps(dict(schema='qualified-task-pool-index-v1',entries=[entry])))
                row=query_v1(p)['tasks'][0]
        if row['task_id'] in seen:
            raise ValueError('Duplicate task identity')
        seen.add(row['task_id']);rows.append(row)
    return dict(schema='qualified-task-pool-v2',count=len(rows),tasks=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('index');a=p.parse_args()
    print(json.dumps(query(a.index),indent=2))
