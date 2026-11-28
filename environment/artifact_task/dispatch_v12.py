"""Append fixed-flow bit-count optimization without changing prior task admission."""
import json
from .dispatch_v11 import ROOT,TASKS as PREVIOUS,graders as previous_graders
TASKS=PREVIOUS+('bitfold_cell_budget_v1',)
def graders(task):
    if task not in TASKS:raise ValueError('Unknown finite task')
    if task!='bitfold_cell_budget_v1':return previous_graders(task)
    from verification_resources.bitfold_optimization.qualification import check
    from verifier.bitfold_optimization.campaign import grade
    check(ROOT/'tasks'/task)
    return (lambda p,o,phase:grade(task,p,o,phase)),(lambda p,o:grade(task,p,o,'evaluation'))
def catalog():return [json.loads((ROOT/'tasks'/t/'task.json').read_text()) for t in TASKS]
