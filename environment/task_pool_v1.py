"""Query source-matched runnable environments across qualified task domains.

The private index holds explicit admission/configuration pairs. No Task ID
dispatch, fallback to historical evidence, or arbitrary backend import occurs.
This index counts environments; it does not infer model difficulty or quality
from the number of previously exported trajectories.
"""
import argparse
import json
from pathlib import Path
from environment.package_admission_v3 import validate as router_validate
from environment.register_admission_v1 import validate as register_validate
from environment.register_backend_v1 import read, sha


def query(index):
    plan = read(index)
    if set(plan) != {'schema', 'entries'} or plan['schema'] != 'qualified-task-pool-index-v1':
        raise ValueError('Unsupported pool index')
    rows, seen = [], set()
    for entry in plan['entries']:
        if set(entry) != {'admission', 'config'}:
            raise ValueError('Explicit admission/configuration pair required')
        path, config = Path(entry['admission']), Path(entry['config'])
        schema = read(path).get('schema')
        if schema == 'router-layered-admission-v3':
            a = router_validate(path, config)
            root = Path(a['package']); task = root/'tasks'/a['task_id']
            meta = read(task/'task.json')
            family = read(root/'family-manifest.json')['family']
            capabilities = meta['capabilities']
            runner = 'environment.native_tools.run_package_v2'
        elif schema == 'register-layered-admission-v1':
            a = register_validate(path, config)
            root = task = Path(a['package'])
            family = read(root/'task.json')['family']
            c = read(root/'contract.json')
            capabilities = ['apb4_slave', 'exact_address_decode', 'byte_strobes',
                            'idle_reset', 'exact_access_waits'] + sorted({r['access'] for r in c['registers']})
            runner = 'environment.native_tools.run_register_v1'
        else:
            raise ValueError('Historical, unsupported or unadmitted record')
        if a['task_id'] in seen:
            raise ValueError('Duplicate task identity; do not count environments as new contracts')
        seen.add(a['task_id'])
        rows.append(dict(task_id=a['task_id'], family=family, capabilities=capabilities,
                         admission=str(path.resolve()), admission_sha256=sha(path),
                         config_sha256=sha(config), package_manifest_sha256=a['package_manifest_sha256'],
                         initial_sha256=sha(task/'workspace/bridge.sv'), deliverable='bridge.sv',
                         task_form='rtl_implementation', runner=runner,
                         status='source_matched_admitted', difficulty='not_inferred_from_admission'))
    return dict(schema='qualified-task-pool-v1', count=len(rows), tasks=rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('index'); a = p.parse_args()
    print(json.dumps(query(a.index), indent=2))
