"""Bind canonical generated artifacts to independently executed controls."""
import json
import tempfile
from pathlib import Path
from .generate_v2 import produce
from environment.artifact_task.session_v2 import sha

ROOT = Path(__file__).resolve().parents[2]
GATE = 'experiments/task-production-v2/checker-quality-v2.json'


def files(path):
    entries = list(Path(path).rglob('*'))
    if any(p.is_symlink() for p in entries):
        raise ValueError('Symlink in task package')
    return {str(p.relative_to(path)): sha(p) for p in entries if p.is_file()}


def check(package):
    package = Path(package)
    meta = json.loads((package / 'task.json').read_text())
    depth = meta.get('depth')
    if type(depth) is not int or depth not in (2, 3):
        raise ValueError('Depth has no executed quality gate')
    gate = json.loads((ROOT / GATE).read_text())
    if not gate['accepted'] or len(gate['checks']) != 36 or not all(r['accepted'] for r in gate['checks']):
        raise ValueError('Quality gate rejected or incomplete')
    for name, digest in gate['source_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Qualified verifier dependency differs')
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / 'task'
        produce(depth, expected)
        if files(package) != files(expected):
            raise ValueError('Task differs from qualified generator')
    task = 'fifo_checker_d%d_v1' % depth
    positive = [r for r in gate['checks'] if r['task_id'] == task and r['expected_reward'] == 1]
    if {(r['control'], r['phase']) for r in positive} != {
            (c, p) for c in ('ring', 'shift') for p in ('public', 'terminal', 'evaluation')}:
        raise ValueError('Missing positive controls')
    for row in positive:
        source = package / ('reference.sv' if row['control'] == 'ring' else 'alternate.sv')
        if sha(source) != row['result']['source_sha256']:
            raise ValueError('Positive source not executed')
    for p in (package / 'controls').glob('*.sv'):
        rows = [r for r in gate['checks'] if r['task_id'] == task and r['control'] == p.stem]
        if len(rows) != 1 or rows[0]['expected_reward'] != 0 or rows[0]['result']['source_sha256'] != sha(p):
            raise ValueError('Negative source not executed')
    return dict(task_id=task, admitted=True, gate_sha256=sha(ROOT / GATE), files=files(package))
