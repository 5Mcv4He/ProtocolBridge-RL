"""Finite RFFE admission requires the complete revision-two industrial gate."""
import json,tempfile
from pathlib import Path
from .generate import generate,MODES
from task_families.fifo_checker_v1.qualification import files,ROOT
from environment.artifact_task.session_v2 import sha
GATE='experiments/task-production-v3/rffe-quality-v2.json'
def check(package):
    package=Path(package);meta=json.loads((package/'task.json').read_text());mode=meta.get('mode')
    if mode not in MODES:raise ValueError('Unknown register contract')
    gate=json.loads((ROOT/GATE).read_text())
    if gate['schema']!='rffe-register-quality-v2' or not gate['accepted'] or len(gate['checks'])!=33 or not all(r['accepted'] for r in gate['checks']):raise ValueError('Incomplete RFFE gate')
    for name,digest in gate['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Qualified source differs')
    with tempfile.TemporaryDirectory() as t:
        expected=Path(t)/'task';generate(mode,expected)
        if files(package)!=files(expected):raise ValueError('Task differs from qualified generation')
    return dict(task_id=meta['task_id'],accepted=True,gate_sha256=sha(ROOT/GATE))
