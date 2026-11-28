"""Append event-level register checker tasks without changing old admission."""
import json
from .dispatch_v9 import ROOT,TASKS as PREVIOUS,graders as previous_graders
NEW_TASKS=('register_checker_rw_v1','register_checker_w1c_v1')
TASKS=PREVIOUS+NEW_TASKS

def graders(task):
    if task not in TASKS:raise ValueError('Unknown finite task')
    if task not in NEW_TASKS:return previous_graders(task)
    from task_families.register_checker_v1.qualification import check
    from verifier.register_checker.campaign import grade
    check(ROOT/'tasks'/task)
    return (lambda p,o,phase:grade(task,p,o,phase)),(lambda p,o:grade(task,p,o,'evaluation'))

def catalog():return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
