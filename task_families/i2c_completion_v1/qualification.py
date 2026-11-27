"""New initial materials require their own gate and the unchanged protocol backend."""
import json,tempfile
from pathlib import Path
from .generate import generate,MODES
from task_families.fifo_checker_v1.qualification import files,ROOT
from task_families.i2c_sink_v1.qualification import check as check_backend
from environment.artifact_task.session_v2 import sha
GATE='experiments/task-production-v3/i2c-completion-quality-v1.json'
def check(package):
    package=Path(package);meta=json.loads((package/'task.json').read_text());mode=meta.get('mode')
    if mode not in MODES:raise ValueError('Unknown completion contract')
    check_backend(ROOT/'tasks'/('i2c_sink_'+mode+'_v1'))
    gate=json.loads((ROOT/GATE).read_text())
    if not gate['accepted'] or len(gate['checks'])!=18 or not all(r['accepted'] for r in gate['checks']):raise ValueError('Incomplete completion gate')
    for name,digest in gate['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Qualified source differs')
    with tempfile.TemporaryDirectory() as t:
        expected=Path(t)/'task';generate(mode,expected)
        if files(package)!=files(expected):raise ValueError('Task differs from qualified generation')
    return dict(task_id=meta['task_id'],accepted=True,gate_sha256=sha(ROOT/GATE))
