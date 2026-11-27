"""Finite reviewed task adapters; independent-reference register repair added."""
import json
from .dispatch_v6 import ROOT,TASKS as PREVIOUS,graders as previous_graders
TASKS=PREVIOUS+('status_set_dominant_repair_v1','status_clear_dominant_repair_v1')
def graders(task):
 if task not in TASKS:raise ValueError('Unknown artifact task')
 if task.startswith('status_'):
  from verifier.status_register.campaign import grade
  from task_families.status_register_v1.qualification import check
  check(ROOT/'tasks'/task)
  return (lambda p,o,phase:grade(task,p,o,phase)),(lambda p,o:grade(task,p,o,'evaluation',True))
 return previous_graders(task)
def catalog():return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
