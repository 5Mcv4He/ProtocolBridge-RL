"""Explicit source-matched admission; generated candidates are not automatically tasks."""
import json,tempfile
from pathlib import Path
from .generate_v2 import generate,MODES
from task_families.fifo_checker_v1.qualification import files,ROOT
from environment.artifact_task.session_v2 import sha
GATE='experiments/i2c-sink-v1/quality.json'

def check(package):
    package=Path(package);meta=json.loads((package/'task.json').read_text());mode=meta.get('mode')
    if mode not in MODES:raise ValueError('Unqualified mode')
    gate=json.loads((ROOT/GATE).read_text())
    if not gate['accepted'] or len(gate['checks'])!=32 or not all(r['accepted'] for r in gate['checks']):
        raise ValueError('Incomplete quality gate')
    for path,digest in gate['source_files'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Qualified source differs')
    with tempfile.TemporaryDirectory() as tmp:
        expected=Path(tmp)/'task';generate(mode,expected)
        if files(package)!=files(expected):raise ValueError('Task differs from qualified generator')
    return dict(task_id=meta['task_id'],admitted=True,gate_sha256=sha(ROOT/GATE),files=files(package))
