"""Synthesis repair admission requires independent semantics and both proof roles."""
import json,tempfile
from pathlib import Path
from .generate import generate,MODES
from task_families.fifo_checker_v1.qualification import files,ROOT
from environment.artifact_task.session_v2 import sha
GATE='experiments/task-production-v3/bitfold-quality-v1.json'
def check(package):
    package=Path(package);meta=json.loads((package/'task.json').read_text());mode=meta.get('mode')
    if mode not in MODES:raise ValueError('Unknown bit operation')
    gate=json.loads((ROOT/GATE).read_text())
    if not gate['accepted'] or len(gate['checks'])!=31 or not all(r['accepted'] for r in gate['checks']):raise ValueError('Incomplete bitfold gate')
    for name,digest in gate['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Qualified source differs')
    with tempfile.TemporaryDirectory() as t:
        expected=Path(t)/'task';generate(mode,expected)
        if files(package)!=files(expected):raise ValueError('Task differs from qualified generation')
    libraries={r['result']['library_sha256'] for r in gate['checks'] if 'library_sha256' in r['result']}
    if len(libraries)!=1:raise ValueError('Quality gate library differs across controls')
    return dict(task_id=meta['task_id'],accepted=True,gate_sha256=sha(ROOT/GATE),library_sha256=next(iter(libraries)))
