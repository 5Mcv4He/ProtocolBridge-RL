"""Bounded trusted register grading job. This module never contacts a model."""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from task_families.apb_register_v1.campaign import grade
from environment.register_inputs_v1 import derive


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def execute():
    request = json.loads(Path('request.json').read_text())
    if any(sha(p) != h for p, h in request['files'].items()):
        raise ValueError('Deployment identity differs')
    contract = json.loads(Path('contract.json').read_text())
    role_input = json.loads(Path('input.json').read_text())
    if role_input != derive(contract, request['seeds'])[request['role']]:
        raise ValueError('Input role differs')
    result = grade(contract, 'candidate.sv', 'grade', 'config.json',
                   role_input['seed'], role_input['random_count'])
    if any(sha(p) != h for p, h in request['files'].items()):
        raise ValueError('Deployment changed during grading')
    if result['source_sha256'] != request['files']['candidate.sv']:
        raise ValueError('Graded candidate differs')


def supervise():
    start = time.monotonic()
    minimum = shutil.disk_usage('.').free
    child = subprocess.Popen([sys.executable, '-m', 'environment.register_remote_v1', 'execute'],
                             start_new_session=True)
    reason = None
    while child.poll() is None:
        minimum = min(minimum, shutil.disk_usage('.').free)
        if minimum < 1024**3 or time.monotonic() - start > 780:
            reason = 'disk_reserve' if minimum < 1024**3 else 'wall_budget'
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            break
        time.sleep(1)
    Path('resource.json').write_text(json.dumps(dict(
        exit_code=child.returncode, stopped_reason=reason,
        minimum_free_bytes=minimum, wall_seconds=time.monotonic()-start)))
    return child.returncode or (1 if reason else 0)


if __name__ == '__main__':
    if sys.argv[1:] == ['execute']:
        execute()
    elif not sys.argv[1:]:
        raise SystemExit(supervise())
    else:
        raise ValueError('Unexpected trusted job arguments')
