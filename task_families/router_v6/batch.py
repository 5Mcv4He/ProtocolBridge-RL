"""Bounded novel-aperture production with a shared qualified checker component.

Generates candidates only. Source-matched runtime evidence and actual per-instance
industrial controls are separate gates. Interrupted directories are preserved.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from task_families.production_lock import exclusive
from task_families.router_v2.generate import sha, verify
from task_families.router_core import generate, BASE_COMMIT
from task_families.router_v4 import contract
from task_families.router_v4.execution import materialize
from .upgrade import upgrade

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = (
    'task_families/router_v6/batch.py', 'task_families/router_v6/upgrade.py',
    'task_families/router_v5/response_ownership.sv.in',
    'task_families/router_core.py', 'task_families/router_v4/contract.py',
    'task_families/router_v4/execution.py', 'task_families/router_v3/materialize.py',
    'task_families/router_v3/qualification_v2.py', 'task_families/router_v2/generate.py',
    'task_families/router_v1/scenarios.py.in', 'task_families/production_lock.py',
)


def save(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def validate(plan):
    if set(plan) != {'schema', 'base_commit', 'producer_files', 'contracts', 'limits'}:
        raise ValueError('Exact plan fields required')
    if plan['schema'] != 'word-owner-production-v1' or plan['base_commit'] != BASE_COMMIT:
        raise ValueError('Unsupported source platform')
    if (set(plan['producer_files']) != set(DEPENDENCIES)
            or any(sha(ROOT / f) != h for f, h in plan['producer_files'].items())):
        raise ValueError('Incomplete or changed producer dependencies')
    if (set(plan['limits']) != {'max_candidates', 'minimum_free_bytes'}
            or type(plan['limits']['max_candidates']) is not int
            or not 1 <= len(plan['contracts']) <= plan['limits']['max_candidates'] <= 30
            or type(plan['limits']['minimum_free_bytes']) is not int
            or plan['limits']['minimum_free_bytes'] < 1024**3):
        raise ValueError('Finite candidate/storage bounds required')
    ids, semantics = set(), set()
    for row in plan['contracts']:
        contract.validate(row)
        key = tuple(tuple(w) for w in row['windows'])
        if row['task_id'] in ids or key in semantics:
            raise ValueError('Duplicate identity or engineering contract')
        ids.add(row['task_id']); semantics.add(key)


def run(planfile, out):
    planfile, out = Path(planfile).resolve(), Path(out).resolve()
    plan = json.loads(planfile.read_text())
    validate(plan)
    with exclusive(out):
        freeze = out / 'plan.json'
        if freeze.exists():
            if sha(freeze) != sha(planfile):
                raise ValueError('A different plan cannot resume this batch')
        else:
            freeze.write_bytes(planfile.read_bytes())
        records = []
        for row in plan['contracts']:
            tid = row['task_id']; folder = out / tid; receipt = out / (tid + '.json')
            if receipt.exists():
                record = json.loads(receipt.read_text())
                if record['status'] == 'generated':
                    verify(folder / 'package')
                    if sha(folder / 'package/family-manifest.json') != record['manifest_sha256']:
                        raise ValueError('Completed candidate changed')
                records.append(record)
                if record['status'] != 'generated':
                    break
                continue
            if folder.exists():
                raise ValueError('Interrupted candidate preserved; review before recovery')
            if shutil.disk_usage(out).free < plan['limits']['minimum_free_bytes']:
                save(out / 'resource-stop.json', {'before_task': tid, 'reason': 'storage_reserve'})
                break
            folder.mkdir(); start = time.monotonic()
            try:
                generate(row, folder / 'source', contract)
                materialize(folder / 'source', folder / 'execution')
                upgrade(folder / 'execution', folder / 'package')
                test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                                      cwd=str(folder / 'package'), stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, timeout=120)
                (folder / 'static-tests.log').write_bytes(test.stdout)
                if test.returncode:
                    raise ValueError('Final static checks failed')
                manifest = verify(folder / 'package')
                record = dict(task_id=tid, status='generated',
                              manifest_sha256=sha(folder / 'package/family-manifest.json'),
                              source_files=len(manifest['files']),
                              package_bytes=sum((folder / 'package' / f).stat().st_size for f in manifest['files']))
            except Exception as error:
                record = dict(task_id=tid, status='generation_failed', error_type=type(error).__name__)
            record.update(wall_seconds=time.monotonic() - start, industrial_admission='not_run', model_trials=0)
            save(receipt, record); records.append(record)
            save(out / 'progress.json', records)
            print(json.dumps(record), flush=True)
            if record['status'] != 'generated':
                break
        result = dict(schema='word-owner-production-result-v1', plan_sha256=sha(freeze),
                      planned=len(plan['contracts']), recorded=len(records),
                      generated=sum(r['status'] == 'generated' for r in records),
                      industrially_admitted=0, rows=records)
        save(out / 'result.json', result)
        return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('plan'); p.add_argument('out')
    a = p.parse_args(); r = run(a.plan, a.out)
    print(json.dumps({k: v for k, v in r.items() if k != 'rows'}))
