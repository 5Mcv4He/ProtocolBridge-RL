"""Reviewed artifact adapters including checker-design contracts."""
import json
from .dispatch_v5 import ROOT, TASKS as PREVIOUS, graders as previous_graders
TASKS = PREVIOUS + ('fifo_checker_d2_v1', 'fifo_checker_d3_v1')
def graders(task):
    if task not in TASKS:
        raise ValueError('Unknown artifact task')
    if task.startswith('fifo_checker_'):
        from task_families.fifo_checker_v1.qualification import check
        from verifier.fifo_checker.campaign_v2 import grade
        check(ROOT / 'tasks' / task)
        return (lambda p,o,phase:grade(task,p,o,phase)), (lambda p,o:grade(task,p,o,'evaluation'))
    return previous_graders(task)
def catalog():
    return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
