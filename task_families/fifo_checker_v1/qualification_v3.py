"""Admission for depth-one/five packages; does not inherit depth-two/three evidence."""
import json
import tempfile
from pathlib import Path
from .generate_v3 import produce
from .qualification import files
from environment.artifact_task.session_v2 import sha
ROOT = Path(__file__).resolve().parents[2]
GATE = 'experiments/task-production-v3/checker-quality-v3.json'


def check(package):
    package=Path(package)
    depth=json.loads((package/'task.json').read_text()).get('depth')
    if type(depth) is not int or depth not in (1,5):
        raise ValueError('Depth has no revision3 industrial admission')
    gate=json.loads((ROOT/GATE).read_text())
    if not gate['accepted'] or len(gate['checks'])!=39 or not all(r['accepted'] for r in gate['checks']):
        raise ValueError('Quality gate rejected or incomplete')
    for name,digest in gate['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Qualified source differs')
    with tempfile.TemporaryDirectory() as t:
        expected=Path(t)/'task';produce(depth,expected)
        if files(expected)!=files(package):raise ValueError('Generated task content differs')
    return {'accepted':True,'task_id':'fifo_checker_d%d_v1'%depth,'quality_sha256':sha(ROOT/GATE)}
