"""Strict materialization v5: require the complete reviewed runtime dependency set.

Historical production.py and its v4 manifests remain reproducible. This version
does not grant rollout permission merely because package hashes match; the task
gate, actual runtime isolation and per-study frozen inputs remain necessary.
"""
import argparse
import json
import shutil
from pathlib import Path
from .production import FAMILIES, ROOT

GATES = {
    "reference-repair": "experiments/verification-resources-v1/independent-reference-quality.json",
    "uart-transmit": "experiments/task-production-v2/uart-quality-v5.json",
    "stimulus-design": "experiments/verification-resources-v1/stimulus-quality.json",
}
from .dependencies import local_import_closure
from environment.artifact_task.session_v2 import sha, save

SCHEMA = 'finite-engineering-materialization-v5'
RUNTIME = 'environment.artifact_task.runner_v6'
COMMON = (
    'environment/artifact_task/runner_v6.py',
    'environment/artifact_task/__main__.py',
    'environment/utm_worker.py',
    'environment/utm_sandbox.sh',
    'verification_resources/production_v2.py',
)


def qualified(family, variant):
    if family not in FAMILIES or variant not in FAMILIES[family]:
        raise ValueError('Unsupported engineering contract')
    task = FAMILIES[family][variant]
    gatepath = GATES[family]
    gate = json.loads((ROOT / gatepath).read_text())
    if not gate['accepted']:
        raise ValueError('Task gate rejected')
    for name, digest in gate['source_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Qualified source differs')
    required = set(gate['source_files']) | set(local_import_closure(ROOT, COMMON)) | {gatepath}
    dependencies = {name: sha(ROOT / name) for name in sorted(required)}
    taskroot = ROOT / 'tasks' / task
    files = {'task/' + str(p.relative_to(taskroot)): sha(p)
             for p in sorted(taskroot.rglob('*')) if p.is_file()}
    return task, dependencies, files


def materialize(family, variant, out):
    task, deps, files = qualified(family, variant)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / 'tasks' / task, out / 'task')
    manifest = dict(schema=SCHEMA, family=family, variant=variant, task_id=task,
                    producer_sha256=sha(__file__), runtime=RUNTIME,
                    source_dependencies=deps, files=files)
    save(out / 'manifest.json', manifest)
    return check(out)


def check(package):
    package = Path(package).resolve()
    manifest = json.loads((package / 'manifest.json').read_text())
    fields = {'schema', 'family', 'variant', 'task_id', 'producer_sha256',
              'runtime', 'source_dependencies', 'files'}
    if set(manifest) != fields or manifest['schema'] != SCHEMA:
        raise ValueError('Wrong manifest schema or fields')
    task, deps, files = qualified(manifest['family'], manifest['variant'])
    if (manifest['task_id'] != task or manifest['runtime'] != RUNTIME or
            manifest['producer_sha256'] != sha(__file__)):
        raise ValueError('Producer or runtime identity differs')
    if manifest['source_dependencies'] != deps:
        raise ValueError('Required dependency set or hashes differ')
    if manifest['files'] != files:
        raise ValueError('Canonical task differs')
    entries = list(package.rglob('*'))
    if any(p.is_symlink() for p in entries):
        raise ValueError('Symlinks not allowed')
    actual = {str(p.relative_to(package)): sha(p) for p in entries
              if p.is_file() and p != package / 'manifest.json'}
    if actual != files:
        raise ValueError('Missing, extra or changed package files')
    return manifest


def reset(package, work):
    manifest = check(package)
    package, work = Path(package), Path(work)
    task = json.loads((package / 'task/task.json').read_text())
    work.mkdir(parents=True, exist_ok=False)
    for p in (package / 'task/spec.md', package / 'task/workspace' / task['deliverable']):
        shutil.copyfile(p, work / p.name)
    save(work / 'task-identity.json', dict(task_id=task['task_id'],
         task_sha256=sha(package / 'task/task.json'),
         initial_sha256=sha(work / task['deliverable']),
         materialization_sha256=sha(package / 'manifest.json')))
    return {'task_id': manifest['task_id'], 'initialized': True}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('produce')
    a.add_argument('family', choices=FAMILIES)
    a.add_argument('variant')
    a.add_argument('out')
    a = sub.add_parser('check')
    a.add_argument('package')
    a = sub.add_parser('reset')
    a.add_argument('package')
    a.add_argument('work')
    a = p.parse_args()
    result = (materialize(a.family, a.variant, a.out) if a.command == 'produce' else
              check(a.package) if a.command == 'check' else reset(a.package, a.work))
    print(json.dumps(result, indent=2))
